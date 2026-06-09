import json
import os
import secrets
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "content.json"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def load_content() -> dict:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_content(content: dict) -> None:
    temp_file = DATA_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(content, file, indent=2, ensure_ascii=False)
    temp_file.replace(DATA_FILE)


def parse_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def strip_bullet_marker(line: str) -> str:
    return line.strip().lstrip("-*•").strip()


def split_text_blocks(text: str) -> list[list[str]]:
    blocks = []
    current = []

    for line in text.splitlines():
        clean_line = line.strip()
        if clean_line:
            current.append(clean_line)
            continue

        if current:
            blocks.append(current)
            current = []

    if current:
        blocks.append(current)

    return blocks


def parse_experience_text(text: str) -> list[dict]:
    parsed = []

    for block in split_text_blocks(text):
        if len(block) < 3:
            raise ValueError(
                "Each experience block needs role, organization, and period on the first three lines."
            )

        role, organization, period = block[:3]
        bullets = [strip_bullet_marker(line) for line in block[3:]]
        parsed.append(
            {
                "role": role,
                "organization": organization,
                "period": period,
                "bullets": [bullet for bullet in bullets if bullet],
            }
        )

    return parsed


def parse_education_text(text: str) -> list[dict]:
    parsed = []

    for line in parse_lines(text):
        if "|" in line:
            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 3:
                raise ValueError("Education lines using | must be qualification | institution | year.")
            qualification, institution, year = parts
        else:
            separator = " – " if " – " in line else " - "
            if separator not in line or "," not in line:
                raise ValueError("Education lines should look like: Institution – Qualification, Year.")

            institution, rest = [part.strip() for part in line.split(separator, 1)]
            qualification, year = [part.strip() for part in rest.rsplit(",", 1)]

        if not qualification or not institution or not year:
            raise ValueError("Each education line needs institution, qualification, and year.")

        parsed.append(
            {
                "qualification": qualification,
                "institution": institution,
                "year": year,
            }
        )

    return parsed


def format_experience_text(experience: list[dict]) -> str:
    blocks = []
    for item in experience:
        lines = [
            str(item.get("role", "")).strip(),
            str(item.get("organization", "")).strip(),
            str(item.get("period", "")).strip(),
        ]
        lines.extend(f"- {bullet}" for bullet in item.get("bullets", []) if str(bullet).strip())
        blocks.append("\n".join(line for line in lines if line))

    return "\n\n".join(blocks)


def format_education_text(education: list[dict]) -> str:
    lines = []
    for item in education:
        institution = str(item.get("institution", "")).strip()
        qualification = str(item.get("qualification", "")).strip()
        year = str(item.get("year", "")).strip()
        lines.append(f"{institution} – {qualification}, {year}")

    return "\n".join(lines)


def is_admin() -> bool:
    return bool(session.get("is_admin"))


@app.get("/")
def portfolio():
    return render_template("index.html", content=load_content())


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if secrets.compare_digest(password, ADMIN_PASSWORD):
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        flash("Invalid password.", "error")

    return render_template("admin_login.html")


@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("portfolio"))


@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if not is_admin():
        return redirect(url_for("admin_login"))

    content = load_content()

    if request.method == "POST":
        csrf_token = request.form.get("csrf_token", "")
        if csrf_token != session.get("csrf_token"):
            flash("Session expired. Please try again.", "error")
            return redirect(url_for("admin_panel"))

        try:
            content["profile"] = {
                "name": request.form.get("name", "").strip(),
                "headline": request.form.get("headline", "").strip(),
                "about": request.form.get("about", "").strip(),
                "location": request.form.get("location", "").strip(),
                "email": request.form.get("email", "").strip(),
                "phone": request.form.get("phone", "").strip(),
            }
            content["skills"] = parse_lines(request.form.get("skills", ""))
            content["experience"] = parse_experience_text(request.form.get("experience_text", ""))
            content["education"] = parse_education_text(request.form.get("education_text", ""))
            content["certifications"] = parse_lines(request.form.get("certifications", ""))
            content["responsibilities"] = parse_lines(request.form.get("responsibilities", ""))
            content["referees"] = parse_lines(request.form.get("referees", ""))

            save_content(content)
            flash("Portfolio content updated successfully.", "success")
            return redirect(url_for("admin_panel"))
        except (ValueError, json.JSONDecodeError) as error:
            flash(f"Could not save changes: {error}", "error")

    session["csrf_token"] = secrets.token_hex(16)

    return render_template(
        "admin_panel.html",
        content=content,
        skills_text="\n".join(content.get("skills", [])),
        certifications_text="\n".join(content.get("certifications", [])),
        responsibilities_text="\n".join(content.get("responsibilities", [])),
        referees_text="\n".join(content.get("referees", [])),
        experience_text=format_experience_text(content.get("experience", [])),
        education_text=format_education_text(content.get("education", [])),
        csrf_token=session["csrf_token"],
    )


if __name__ == "__main__":
    app.run(debug=True)

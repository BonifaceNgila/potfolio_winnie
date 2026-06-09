import json
import os
import secrets
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from jinja2 import Environment, FileSystemLoader, select_autoescape

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


def is_streamlit_runtime() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ModuleNotFoundError:
        return False

    return get_script_run_ctx(suppress_warning=True) is not None


def _get_streamlit_view_mode(st) -> str:
    try:
        value = st.query_params.get("view", "portfolio")
        if isinstance(value, list):
            return value[0] if value else "portfolio"
        return value or "portfolio"
    except AttributeError:
        params = st.experimental_get_query_params()
        values = params.get("view", ["portfolio"])
        return values[0] if values else "portfolio"


def _set_streamlit_view_mode(st, mode: str) -> None:
    try:
        st.query_params["view"] = mode
    except AttributeError:
        st.experimental_set_query_params(view=mode)


def render_streamlit_admin_panel(st) -> None:
    st.markdown("# Portfolio Admin")
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        if st.button("Back to Portfolio"):
            _set_streamlit_view_mode(st, "portfolio")
            st.rerun()
    with top_col2:
        if st.button("Refresh Data"):
            st.rerun()

    if "streamlit_is_admin" not in st.session_state:
        st.session_state["streamlit_is_admin"] = False

    if not st.session_state.get("streamlit_is_admin", False):
        with st.form("streamlit_admin_login"):
            password = st.text_input("Admin password", type="password")
            login_submitted = st.form_submit_button("Login")

        if login_submitted:
            if secrets.compare_digest(password, ADMIN_PASSWORD):
                st.session_state["streamlit_is_admin"] = True
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Invalid password.")

        return

    if st.button("Logout"):
        st.session_state["streamlit_is_admin"] = False
        st.success("Logged out.")
        st.rerun()

    content = load_content()
    profile = content.get("profile", {})

    st.caption("Edit content below and click Save Changes.")

    with st.form("streamlit_admin_editor"):
        name = st.text_input("Name", value=profile.get("name", "")).strip()
        headline = st.text_area("Headline", value=profile.get("headline", ""), height=80).strip()
        about = st.text_area("About", value=profile.get("about", ""), height=180).strip()

        col1, col2, col3 = st.columns(3)
        with col1:
            location = st.text_input("Location", value=profile.get("location", "")).strip()
        with col2:
            email = st.text_input("Email", value=profile.get("email", "")).strip()
        with col3:
            phone = st.text_input("Phone", value=profile.get("phone", "")).strip()

        skills_text = st.text_area(
            "Skills (one per line)",
            value="\n".join(content.get("skills", [])),
            height=140,
        )
        experience_text = st.text_area(
            "Experience (one blank line between roles; first 3 lines role, organization, period)",
            value=format_experience_text(content.get("experience", [])),
            height=340,
        )
        education_text = st.text_area(
            "Education (one per line: Institution – Qualification, Year)",
            value=format_education_text(content.get("education", [])),
            height=120,
        )
        certifications_text = st.text_area(
            "Certifications & Training (one per line)",
            value="\n".join(content.get("certifications", [])),
            height=140,
        )
        responsibilities_text = st.text_area(
            "Other Responsibilities (one per line)",
            value="\n".join(content.get("responsibilities", [])),
            height=120,
        )
        referees_text = st.text_area(
            "Referees (one per line)",
            value="\n".join(content.get("referees", [])),
            height=100,
        )

        save_submitted = st.form_submit_button("Save Changes")

    if not save_submitted:
        return

    try:
        updated = {
            "profile": {
                "name": name,
                "headline": headline,
                "about": about,
                "location": location,
                "email": email,
                "phone": phone,
            },
            "skills": parse_lines(skills_text),
            "experience": parse_experience_text(experience_text),
            "education": parse_education_text(education_text),
            "certifications": parse_lines(certifications_text),
            "responsibilities": parse_lines(responsibilities_text),
            "referees": parse_lines(referees_text),
        }
        save_content(updated)
        st.success("Portfolio content updated successfully.")
    except (ValueError, json.JSONDecodeError) as error:
        st.error(f"Could not save changes: {error}")


def render_streamlit_portfolio() -> None:
    import streamlit as st
    import streamlit.components.v1 as components

    content = load_content()
    profile = content.get("profile", {})

    st.set_page_config(
        page_title=profile.get("name", "Portfolio"),
        page_icon="💼",
        layout="wide",
    )

    st.markdown(
        """
        <style>
          [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
            display: none;
          }
          [data-testid="stAppViewContainer"] > .main {
            padding-top: 0;
          }
          [data-testid="stSidebar"] {
            display: none;
          }
          .block-container {
            padding: 0 !important;
            max-width: 100% !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    current_view = _get_streamlit_view_mode(st)

    if current_view == "admin":
        render_streamlit_admin_panel(st)
        return

    nav_col1, nav_col2 = st.columns([1, 4])
    with nav_col1:
        if st.button("Manage Details"):
            _set_streamlit_view_mode(st, "admin")
            st.rerun()
    with nav_col2:
        st.caption("Use Manage Details to open the admin editor.")

    template_env = Environment(
        loader=FileSystemLoader(str(BASE_DIR / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = template_env.get_template("index.html")

    def streamlit_url_for(endpoint: str, filename: str | None = None) -> str:
        if endpoint == "static" and filename == "styles.css":
            return "__STATIC_STYLES__"
        if endpoint == "static" and filename == "script.js":
            return "__STATIC_SCRIPT__"
        if endpoint == "admin_login":
            return "?view=admin"
        if endpoint == "portfolio":
            return "?view=portfolio"
        return "#"

    rendered = template.render(content=content, url_for=streamlit_url_for)
    css_text = (BASE_DIR / "static" / "styles.css").read_text(encoding="utf-8")
    js_text = (BASE_DIR / "static" / "script.js").read_text(encoding="utf-8")

    rendered = rendered.replace(
        '<link rel="stylesheet" href="__STATIC_STYLES__" />',
        f"<style>{css_text}</style>",
    )
    rendered = rendered.replace(
        '<script src="__STATIC_SCRIPT__"></script>',
        f"<script>{js_text}</script>",
    )

    estimated_height = 1500
    estimated_height += len(content.get("experience", [])) * 220
    estimated_height += len(content.get("skills", [])) * 16
    estimated_height += len(content.get("education", [])) * 120
    estimated_height += len(content.get("certifications", [])) * 40
    estimated_height += len(content.get("responsibilities", [])) * 40
    estimated_height += len(content.get("referees", [])) * 40

    components.html(rendered, height=max(1800, estimated_height), scrolling=True)


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


if is_streamlit_runtime():
    render_streamlit_portfolio()
elif __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", use_reloader=False)

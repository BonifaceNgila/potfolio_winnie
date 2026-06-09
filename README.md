# Portfolio App (Python + Flask)

This portfolio is now dynamic and editable through an admin panel.

## Run

1. Open terminal in this folder.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional: set secure environment variables.

Windows PowerShell:

```powershell
$env:FLASK_SECRET_KEY="replace-with-a-strong-secret"
$env:ADMIN_PASSWORD="replace-with-a-strong-password"
```

4. Start the app:

```bash
python app.py
```

5. Open:
- Portfolio: http://127.0.0.1:5000/
- Admin login: http://127.0.0.1:5000/admin/login

Default admin password if not overridden is `admin123`.

## Data storage

All editable content is stored in:
- `data/content.json`

The app preserves your current experience entries as defaults and lets you update them when needed.

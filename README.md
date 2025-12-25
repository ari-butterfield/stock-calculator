# Simple Flask Task Template

This is a minimal Flask project template that provides a simple text form to add, edit, and delete tasks backed by SQLite.

Quick start

1. Create a virtual environment and activate it:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the app:

```powershell
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Files of interest

- `app.py` — application factory and DB init
- `models.py` — `Task` model
- `routes.py` — CRUD routes (index, add, edit, delete)
- `forms.py` — WTForms definitions
- `templates/` — Jinja2 templates

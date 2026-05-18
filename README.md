# Shepherd

A church attendance management system built with Flask.

---

## Features

- **Member management** — maintain a list of church members
- **Groups** — organise members into ministry groups (e.g. Worship Service, Youth)
- **Events** — schedule services and gatherings linked to a group
- **Attendance** — record and query who attended each event
- **Admin accounts** — login-protected web UI with two access levels (Admin / Superuser)
- **REST API** — JSON API for all data operations (members, groups, events, attendance)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3 (application factory, blueprints) |
| ORM | Flask-SQLAlchemy 3 / SQLAlchemy 2 |
| Authentication | Flask-Login 0.6 (session-based) |
| Database (dev) | SQLite (zero-config, file-based) |
| Database (prod) | PostgreSQL (via `DATABASE_URL`) |
| Runtime | Python 3.11+ |

---

## Quick Start

**Prerequisites:** Python 3.11+

```powershell
# 1. Activate the virtual environment (create with: python -m venv venv)
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create and configure the environment file
Copy-Item .env.example .env
# Edit .env and set SECRET_KEY to a strong random value:
python -c "import secrets; print(secrets.token_hex(32))"

# 4. Start the development server
python run.py
```

The app is available at **http://127.0.0.1:5000**

Tables are created automatically on first launch — no migration step required.

---

## Creating the First Admin Account

The first account must be created from the command line:

```powershell
$env:FLASK_APP = "run.py"
flask create-admin
```

You will be prompted for a username, email, and password. This account is automatically a **superuser** with full access.

---

## Project Structure

```
shepherd/
├── app/
│   ├── __init__.py          # Application factory (create_app)
│   ├── extensions.py        # db, login_manager
│   ├── models/              # User, Member, Group, Event, Attendance
│   ├── routes/              # auth, members, groups, events, attendance
│   ├── services/            # Business logic layer
│   └── templates/           # Jinja2 HTML templates
├── tests/
│   ├── run_all_smoke.py     # Smoke test runner
│   └── smoke_*.py           # Smoke test files (112 tests)
├── config.py                # Development / Testing / Production config
├── run.py                   # App entry point
├── requirements.txt
└── .env.example
```

---

## API Reference

All API endpoints require an active login session. Unauthenticated requests return `401`.

| Endpoint | Methods | Description |
|---|---|---|
| `/api/members/` | GET, POST | List / create members |
| `/api/members/<id>` | GET, PUT, DELETE | Get / update / delete a member |
| `/api/groups/` | GET, POST | List / create groups |
| `/api/groups/<id>` | GET, PUT, DELETE | Get / update / delete a group |
| `/api/events/` | GET, POST | List / create events |
| `/api/events/<id>` | GET, DELETE | Get / delete an event |
| `/api/attendance/` | GET, POST | List / record attendance |
| `/api/attendance/<id>` | PUT, DELETE | Update / delete an attendance record |

Query parameters:
- `GET /api/events/?group_id=<id>` — filter events by group
- `GET /api/attendance/?event_id=<id>&member_id=<id>` — filter attendance records

---

## Running the Tests

```powershell
.\venv\Scripts\python.exe tests/run_all_smoke.py
```

Expected output: `112 passed, 0 failed` across 9 smoke test files.

---

## Documentation

- [ADMIN_GUIDE.md](ADMIN_GUIDE.md) — full setup, user management, database, PostgreSQL migration, and URL reference

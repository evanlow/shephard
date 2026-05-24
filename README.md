# Shepherd

Shepherd is a church attendance management system designed to help church administrators record attendance for worship services, Sunday School classes, ministry groups, and other church events.

The system allows authorised admin users to manage members, groups, events, and attendance records through a web-based interface. It is designed for multi-user administrative use, with local SQLite support for development and PostgreSQL support for production deployment on AWS.

---

## What Shepherd Solves

Church attendance is often recorded manually using paper forms, spreadsheets, or informal notes. Shepherd provides a centralised system where authorised users can:

- Maintain a structured list of church members
- Organise members into groups or classes
- Create worship service, Sunday School, or ministry events
- Mark attendance in real time
- Review attendance records when follow-up is needed
- Manage administrative access securely

---

## Key Features

- **Admin login and role-based access** — supports Admin and Superuser access levels
- **Member management** — create, update, archive, restore, and manage church members
- **Group management** — organise members into worship service groups, Sunday School classes, or ministry groups
- **Event management** — schedule services, gatherings, classes, and other attendance-taking events
- **Attendance marking** — record present/absent status for members by event
- **Attendance reports and exports** — retrieve attendance data for review and reporting
- **System purge functions** — administrative maintenance tools for clearing selected datasets
- **REST API** — JSON API for members, groups, events, and attendance operations
- **SQLite for local development** — simple local setup for testing and development
- **PostgreSQL for production** — suitable for deployment using Amazon RDS
- **AWS-ready deployment guide** — supports deployment using EC2, RDS, systemd, Gunicorn, Nginx, and HTTPS

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3, application factory, blueprints |
| ORM | Flask-SQLAlchemy 3 / SQLAlchemy 2 |
| Authentication | Flask-Login 0.6, session-based login |
| Database, local development | SQLite |
| Database, production | PostgreSQL via `DATABASE_URL` |
| Frontend | Jinja2 templates, Bootstrap |
| Runtime | Python 3.11+ |
| Production hosting | AWS EC2, Amazon RDS PostgreSQL |
| Production service management | Gunicorn, systemd, Nginx |

---

## Quick Start

**Prerequisites:** Python 3.11+

```powershell
# 1. Create and activate the virtual environment
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create and configure the environment file
Copy-Item .env.example .env
# Edit .env and set SECRET_KEY to a strong random value:
python -c "import secrets; print(secrets.token_hex(32))"

# 4. Initialize database tables
$env:FLASK_APP = "run.py"
flask init-db

# 5. Start the development server
python run.py
```

The app is available at **http://127.0.0.1:5000**.

Run `flask init-db` when setting up a new database. Schema upgrades should be handled explicitly.

---

## Creating the First Admin Account

The first account must be created from the command line:

```powershell
$env:FLASK_APP = "run.py"
flask create-admin
```

You will be prompted for a username, email, and password. This account is automatically a **superuser** with full access.

---

## Environment Variables

Create a `.env` file from `.env.example` for local development.

Common variables include:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session/security secret key |
| `DATABASE_URL` | Optional database connection string. If omitted locally, SQLite is used. |
| `FLASK_ENV` | Environment indicator, depending on deployment setup |

For production deployment, environment variables should be configured outside the repository, for example in `/etc/shepherd.env` or a similar server-side environment file. Do not commit real secrets, database passwords, or production credentials into GitHub.

---

## Project Structure

```text
shepherd/
├── app/
│   ├── __init__.py          # Application factory (create_app)
│   ├── extensions.py        # db, login_manager
│   ├── models/              # User, Member, Group, Event, Attendance
│   ├── routes/              # auth, members, groups, events, attendance
│   ├── services/            # Business logic layer
│   └── templates/           # Jinja2 HTML templates
├── docs/
│   └── screenshots/         # Screenshots can be added here later
├── tests/
│   ├── run_all_smoke.py     # Smoke test runner
│   └── smoke_*.py           # Smoke test files
├── .env.example             # Example environment variables
├── ADMIN_ROLE_GUIDE.md      # Admin-role user guide
├── AWS_deployment_guide.md  # AWS-specific deployment guide
├── DEPLOYMENT_GUIDE.md      # General deployment guide
├── SUPERUSERS_GUIDE.md      # Superuser feature guide
├── config.py                # Development / Testing / Production config
├── run.py                   # App entry point
├── requirements.txt         # Python dependencies
└── LICENSE                  # MIT License
```

---

## API Reference

All API endpoints require an active login session. Unauthenticated requests return `401`.

| Endpoint | Methods | Description |
|---|---|---|
| `/api/members/` | GET, POST | List / create members, supports `group_id` |
| `/api/members/<id>` | GET, PUT, DELETE | Get / update / delete a member, supports `group_id` assignment |
| `/api/groups/` | GET, POST | List / create groups |
| `/api/groups/<id>` | GET, PUT, DELETE | Get / update / delete a group |
| `/api/events/` | GET, POST | List / create events |
| `/api/events/<id>` | GET, DELETE | Get / delete an event |
| `/api/attendance/` | GET, POST | List / record attendance |
| `/api/attendance/<id>` | PUT, DELETE | Update / delete an attendance record |
| `/api/attendance/event/<id>/status` | GET | Event attendance summary: `expected`, `present`, `absent` |

Query parameters:

- `GET /api/events/?group_id=<id>` — filter events by group
- `GET /api/attendance/?event_id=<id>&member_id=<id>` — filter attendance records

---

## Running the Tests

```powershell
.\venv\Scripts\python.exe tests/run_all_smoke.py
```

Expected output: all smoke tests should pass.

---

## Documentation

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) — general deployment setup, database configuration, environment variables, and URL reference
- [AWS_deployment_guide.md](AWS_deployment_guide.md) — AWS deployment guide covering EC2, PostgreSQL RDS, server setup, and production hosting
- [ADMIN_ROLE_GUIDE.md](ADMIN_ROLE_GUIDE.md) — day-to-day usage guide for Admin-role users
- [SUPERUSERS_GUIDE.md](SUPERUSERS_GUIDE.md) — full feature reference for Superusers, including admin capabilities, delete/archive functions, and user management

---

## Screenshots

Screenshots can be added later under `docs/screenshots/`.

Suggested future screenshots:

- Dashboard
- Attendance marking screen
- Member management
- Group management
- Event management
- Admin / Superuser functions

---

## Suggested Repository About Section

For GitHub's repository **About** panel, use the following description:

```text
Church attendance management system for worship service, Sunday School, members, groups, events, and admin attendance tracking.
```

Suggested topics:

```text
flask, church-management, attendance-system, postgresql, aws, python, sqlalchemy, bootstrap
```

---

## License

Shepherd is released under the [MIT License](LICENSE). It is free to use, modify, and deploy by anyone, including churches and organisations.

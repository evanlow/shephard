# Shepherd Project Plan

## Status: MVP Implementation In Progress

---

## 1. Requirements Traceability

The following table maps specification sections to implementation status.

| Spec Section | Requirement | Status |
|---|---|---|
| §8.1 Authentication | Login with username/password | ✅ Implemented |
| §8.1 Authentication | Passwords stored as hashes | ✅ Implemented |
| §8.1 Authentication | Unauthenticated web users redirected to login | ✅ Implemented |
| §8.1 Authentication | Unauthenticated API requests return 401 | ✅ Implemented |
| §8.1 Authentication | Admin and Superuser roles | ✅ Implemented (`is_admin`, `is_superuser`) |
| §8.1 Authentication | First superuser via CLI command | ✅ `flask create-admin` |
| §8.2 Member Management | Create, view, update, delete member | ✅ Implemented |
| §8.2 Member Management | Assign/unassign member to group | ✅ Implemented |
| §8.2 Member Management | Minimal personal data (name only) | ✅ Implemented |
| §8.3 Group Management | Create, view, update, delete group | ✅ Implemented |
| §8.3 Group Management | Unassign members on group delete | ✅ Implemented |
| §8.4 Event Management | Create event linked to group | ✅ Implemented |
| §8.4 Event Management | View event list; filter by group | ✅ Implemented |
| §8.4 Event Management | View event details, delete event | ✅ Implemented |
| §8.5 Attendance Taking | Mark member present for event | ✅ Implemented |
| §8.5 Attendance Taking | Expected attendees from group membership | ✅ Implemented |
| §8.5 Attendance Taking | Reject attendance for non-group members | ✅ Implemented |
| §8.5 Attendance Taking | Prevent duplicate attendance records | ✅ Implemented |
| §8.5 Attendance Taking | Update attendance for correction | ✅ Implemented |
| §8.5 Attendance Taking | Delete attendance (subject to permission) | ✅ Admin-level |
| §8.6 Event Attendance Status | Expected/present/absent counts and lists | ✅ Implemented |
| §8.7 Reporting | Attendance summary by event | ✅ `/api/attendance/event/<id>/status` |
| §8.7 Reporting | Attendance filtered by event | ✅ `/api/attendance/?event_id=<id>` |
| §8.7 Reporting | Attendance filtered by member | ✅ `/api/attendance/?member_id=<id>` |
| §9 API | REST API for all core entities | ✅ Implemented |
| §9 API | All API endpoints require authentication | ✅ Implemented |
| §10 Data Storage | SQLite for development | ✅ Implemented |
| §10 Data Storage | PostgreSQL for production via DATABASE_URL | ✅ Implemented |
| §11 Data Model | User, Member, Group, Event, Attendance models | ✅ Implemented |
| §11.5 Attendance | `marked_by` audit field | ✅ Implemented (nullable) |
| §12 Security | Admin login required for all functionality | ✅ Implemented |
| §12 Security | Password hashing | ✅ Werkzeug PBKDF2 |
| §12 Security | Secrets in environment variables, not in code | ✅ `.env` excluded from git |
| §12 Security | SQLite files excluded from git | ✅ `.gitignore` configured |
| §12 Security | Production requires HTTPS | ⬜ Deployment concern (Nginx + Let's Encrypt) |
| §12 Security | Production DATABASE_URL validation at startup | ✅ Implemented |
| §12 Security | Production SECRET_KEY validation at startup | ✅ Implemented |
| §17 Acceptance | All MVP acceptance criteria | ✅ See section 4 below |

---

## 2. Architecture Overview

```
shepherd/
├── app/
│   ├── __init__.py          # Application factory (create_app); startup validation
│   ├── extensions.py        # db, login_manager
│   ├── models/
│   │   ├── user.py          # User (id, username, email, password_hash, is_admin, is_superuser, created_at)
│   │   ├── member.py        # Member (id, name, group_id, created_at)
│   │   ├── group.py         # Group (id, name, description, created_at)
│   │   ├── event.py         # Event (id, name, date, group_id, created_at)
│   │   └── attendance.py    # Attendance (id, event_id, member_id, present, marked_by, recorded_at)
│   ├── routes/
│   │   ├── auth.py          # login, logout, dashboard, user management; admin_required / superuser_required decorators
│   │   ├── members.py       # /api/members/ — admin_required; DELETE superuser_required
│   │   ├── groups.py        # /api/groups/ — admin_required; DELETE superuser_required
│   │   ├── events.py        # /api/events/ — admin_required; DELETE superuser_required
│   │   └── attendance.py    # /api/attendance/ — admin_required; records marked_by
│   ├── services/            # Business logic layer (no HTTP dependency)
│   └── templates/           # Jinja2 HTML (login, dashboard, user management)
├── tests/
│   ├── run_all_smoke.py
│   ├── smoke_auth.py
│   ├── smoke_members.py / smoke_member_service.py
│   ├── smoke_groups.py / smoke_group_service.py
│   ├── smoke_events.py / smoke_event_service.py
│   ├── smoke_attendance.py / smoke_attendance_service.py
│   └── smoke_rbac.py        # Role-based access control tests
├── config.py                # Dev / Testing / Production configs with startup validation
└── run.py
```

---

## 3. Role Model

| Role | `is_admin` | `is_superuser` | Capabilities |
|---|---|---|---|
| Superuser | `True` | `True` | Full access including user management and all deletes |
| Admin | `True` | `False` | View + create + update members/groups/events/attendance; delete attendance |
| No role | `False` | `False` | Login only — no API access (403) |

**Access rules per endpoint:**

| Operation | Required Role |
|---|---|
| GET/POST/PUT on members, groups, events, attendance | Admin or Superuser |
| DELETE members | Superuser only |
| DELETE groups | Superuser only |
| DELETE events | Superuser only |
| DELETE attendance | Admin or Superuser |
| User management (create/delete users) | Superuser only |

---

## 4. MVP Acceptance Criteria Validation

| # | Criterion | Status |
|---|---|---|
| 1 | Superuser can create an admin account | ✅ `flask create-admin` (superuser) + `/admin/users/new` (creates admins) |
| 2 | Admin can log in | ✅ `/login` |
| 3 | Admin can create groups | ✅ `POST /api/groups/` |
| 4 | Admin can create members | ✅ `POST /api/members/` |
| 5 | Admin can assign members to groups | ✅ `PUT /api/members/<id>` with `group_id` |
| 6 | Admin can create events linked to groups | ✅ `POST /api/events/` |
| 7 | Admin can mark members present | ✅ `POST /api/attendance/` |
| 8 | System prevents marking non-group members | ✅ Service-layer validation |
| 9 | System prevents duplicate attendance | ✅ DB unique constraint + service validation |
| 10 | System shows expected/present/absent per event | ✅ `GET /api/attendance/event/<id>/status` |
| 11 | Local development works with SQLite | ✅ Default config uses SQLite |
| 12 | Production uses PostgreSQL via DATABASE_URL | ✅ ProductionConfig + startup validation |
| 13 | Secrets and local DB files not in git | ✅ `.gitignore` covers `.env` and `*.db` |

---

## 5. Future Enhancements (Post-MVP)

These are deferred per spec section 16 and are not part of the current MVP scope.

- **§16.1** Many-to-many group membership (member_groups association table)
- **§16.2** Attendance UI optimisation (search-as-you-type, large present button, auto-save)
- **§16.3** Real-time updates (polling or WebSocket via Flask-SocketIO)
- **§16.4** Reports and exports (weekly/monthly summaries, CSV/Excel export)
- **§16.5** Follow-up workflow (flag consecutive absentees, assign follow-up)
- **§16.6** Newcomer workflow (newcomer status, first visit date, conversion to member)

Additional future items:
- Role-based access control by ministry or group (finer-grained than Admin/Superuser)
- Full audit log for attendance changes (who changed what, when)
- Data retention policy
- Admin activity log
- HTTPS configuration guide for AWS EC2 + Nginx + Let's Encrypt

---

## 6. Deployment Checklist (Production)

When deploying to production:

1. Set `DATABASE_URL` to PostgreSQL RDS endpoint (app validates this at startup).
2. Set `SECRET_KEY` to a strong random value — `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Set `FLASK_ENV=production`.
4. Run `flask init-db` to create schema on first deploy.
5. Run `flask create-admin` to create the first superuser.
6. Configure Nginx as reverse proxy with HTTPS (Let's Encrypt or AWS ACM).
7. Run the app with Gunicorn: `gunicorn -w 4 run:app`.
8. Restrict RDS security group to EC2 instance only.

---

## 7. Running Tests

```bash
python tests/run_all_smoke.py
```

Expected: all tests pass (0 failures).

Test files:
- `smoke_auth.py` — login, logout, user management
- `smoke_members.py` / `smoke_member_service.py` — member CRUD
- `smoke_groups.py` / `smoke_group_service.py` — group CRUD
- `smoke_events.py` / `smoke_event_service.py` — event CRUD
- `smoke_attendance.py` / `smoke_attendance_service.py` — attendance CRUD and status
- `smoke_rbac.py` — role-based access control

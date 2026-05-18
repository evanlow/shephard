# Shepherd — Admin Guide

**Shepherd** is a church attendance management system. This guide covers everything an administrator needs to set up, run, and manage the system.

---

## Table of Contents

1. [First-Time Setup](#1-first-time-setup)
2. [Running the App](#2-running-the-app)
3. [User Roles](#3-user-roles)
4. [Creating the First Superuser](#4-creating-the-first-superuser)
5. [Managing Admin Users](#5-managing-admin-users)
6. [The Database](#6-the-database)
7. [Environment Variables](#7-environment-variables)
8. [Switching to PostgreSQL](#8-switching-to-postgresql)
9. [URL Reference](#9-url-reference)

---

## 1. First-Time Setup

**Prerequisites:** Python 3.11+

```powershell
# 1. Create and activate the virtual environment
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the example env file and fill in your values
Copy-Item .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY`:

```powershell
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as the value of `SECRET_KEY` in `.env`.

---

## 2. Running the App

```powershell
# Activate the venv (if not already active)
.\venv\Scripts\activate

# Start the development server
python run.py
```

The app will be available at **http://127.0.0.1:5000**

> **Note:** `db.create_all()` runs automatically on startup, so all database tables are created on first launch — no migration step required for development.

---

## 3. User Roles

Shepherd has two types of admin accounts:

| Role | Can use the app | Can manage admin users |
|---|---|---|
| **Admin** | ✅ | ❌ |
| **Superuser** | ✅ | ✅ |

- **Admins** can log in and manage church data (members, groups, events, attendance) via the API.
- **Superusers** can additionally create and delete other admin accounts via the web UI.
- There is no limit on the number of superusers, but only superusers can grant access to others.

---

## 4. Creating the First Superuser

The first account must be created from the command line using the `flask create-admin` command. This account is automatically a **superuser**.

```powershell
$env:FLASK_APP = "run.py"
flask create-admin
```

You will be prompted for:
- **Username** — used to log in
- **Email** — must be unique
- **Password** — minimum 8 characters (prompted twice to confirm)

> **Existing account?** If you created an account before the superuser feature was added, update it directly in the database:
> ```sql
> UPDATE users SET is_superuser = 1 WHERE username = 'your_username';
> ```

---

## 5. Managing Admin Users

Once logged in as a superuser:

1. Go to **http://127.0.0.1:5000/dashboard**
2. Click **Manage Admin Users**
3. From here you can:
   - View all admin accounts
   - Create a new admin (via **+ New User**)
   - Delete an existing admin

### Creating a new admin via the UI

Fill in:
- **Username** — must be unique
- **Email** — must be unique
- **Password** / **Confirm Password** — minimum 8 characters

New accounts created via the UI are regular **admins** (not superusers). To promote someone to superuser, update the database directly:

```sql
UPDATE users SET is_superuser = 1 WHERE username = 'their_username';
```

### Deleting an admin

Click **Delete** next to the user. You cannot delete your own account.

---

## 6. The Database

### Development (SQLite)

By default, Shepherd uses SQLite. The database file is stored at:

```
shepherd_dev.db        ← in the project root folder
```

Full path example:
```
C:\Users\you\Documents\development workspace\shepherd\shepherd_dev.db
```

### Viewing the database

**Option A — VS Code extension (recommended)**
Install **SQLite Viewer** by Florian Klampfer from the Extensions panel, then click `shepherd_dev.db` in the file explorer.

**Option B — DB Browser for SQLite**
Download from [sqlitebrowser.org](https://sqlitebrowser.org), then open the `.db` file.

**Option C — Command line**
```powershell
sqlite3 shepherd_dev.db
.tables
SELECT * FROM users;
.quit
```

### Tables

| Table | Description |
|---|---|
| `users` | Admin accounts |
| `members` | Church members |
| `groups` | Ministry groups (e.g. Worship Service) |
| `events` | Scheduled services / gatherings |
| `attendance` | Attendance records per event per member |

---

## 7. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ in production | Flask session signing key — keep secret |
| `FLASK_ENV` | Optional | `development` (default) or `production` |
| `DATABASE_URL` | Optional | Defaults to SQLite; set for PostgreSQL |

Configure these in your `.env` file (copied from `.env.example`).

---

## 8. Switching to PostgreSQL

1. Set `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/shepherd
   ```

2. Ensure `psycopg2-binary` is installed (already in `requirements.txt`).

3. Create the database in PostgreSQL:
   ```sql
   CREATE DATABASE shepherd;
   ```

4. Start the app — tables will be created automatically on first launch.

> For production deployments, also set `FLASK_ENV=production` and ensure `SECRET_KEY` is a strong random value.

---

## 9. URL Reference

### Web UI

| URL | Access | Description |
|---|---|---|
| `GET /login` | Public | Login page |
| `POST /login` | Public | Submit login form |
| `POST /logout` | Admin | Log out |
| `GET /dashboard` | Admin | Home dashboard |
| `GET /admin/users` | Superuser | List all admin users |
| `GET /admin/users/new` | Superuser | Create user form |
| `POST /admin/users/new` | Superuser | Submit new user |
| `POST /admin/users/<id>/delete` | Superuser | Delete a user |

### REST API

All API endpoints require authentication. Unauthenticated requests return `401 {"error": "Authentication required"}`.

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

# Shepherd — Admin Guide

**Shepherd** is a church attendance management system. This guide covers everything an administrator needs to set up, run, and manage the system.

---

## Table of Contents

1. [First-Time Setup](#1-first-time-setup)
2. [Running the App](#2-running-the-app)
3. [User Roles](#3-user-roles)
4. [Creating the First Superuser](#4-creating-the-first-superuser)
5. [Managing Admin Users](#5-managing-admin-users)
6. [Managing Groups and Members](#6-managing-groups-and-members)
7. [Managing Events](#7-managing-events)
8. [The Database](#8-the-database)
9. [Environment Variables](#9-environment-variables)
10. [Switching to PostgreSQL](#10-switching-to-postgresql)
11. [URL Reference](#11-url-reference)

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

# Initialize database tables (new database setup)
$env:FLASK_APP = "run.py"
flask init-db

# Start the development server
python run.py
```

The app will be available at **http://127.0.0.1:5000**

> **Note:** Run `flask init-db` for new database setup. For schema changes, use an explicit migration/upgrade step.

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

## 6. Managing Groups and Members

### The ALL MEMBERS group

Every Shepherd installation has a built-in **ALL MEMBERS** group that is created automatically on first use. This group has special behaviour:

- Every new member is automatically enrolled in ALL MEMBERS at creation time.
- Members assigned to additional groups belong to those groups **and** ALL MEMBERS simultaneously.
- The ALL MEMBERS group **cannot be renamed or deleted** — attempts via the UI or API will be rejected.

### Multi-group membership

A member can belong to more than one group at a time (e.g. "Worship Service" and "Youth Group"). When creating or updating a member via the API you can supply multiple group IDs:

```json
POST /api/members/
{ "name": "Jane Doe", "group_ids": [2, 5] }
```

The response will include both a `group_ids` list and a `groups` list (name + id) reflecting all current memberships. ALL MEMBERS is always included automatically — you do not need to pass its ID.

### Deactivating a member

When a member leaves the church, deactivate them rather than deleting them. This preserves all their past attendance records while excluding them from future events.

1. On the **Members** page, click **Deactivate** next to the member.
2. Enter their **last active day** — events on and before this date still list them; events after will not.
3. Click **Confirm**.

Deactivated members appear in the list with an **Inactive** badge (hidden by default — tick **Show inactive** to see them).

### Reactivating a member

If a deactivated member returns:

1. On the **Members** page, tick **Show inactive** to reveal deactivated members.
2. Click **Reactivate** next to the member.
3. Enter their **rejoin date** — they will appear in attendance from this date onward.
4. Click **Confirm**.

Reactivation updates the member's group join date to the rejoin date so the gap period is correctly excluded from reports. Past attendance records are never altered.

Both actions are also available from the member's **Edit** page in a dedicated Membership Status card.

---

## 7. Managing Events

### Editing an event

Admins can edit an event's **name** and **date/time** after creation. The group an event belongs to cannot be changed.

**Via the UI:**
1. Go to the **Events** page.
2. Click the edit icon next to the event.
3. Update the name and/or date & time, then click **Save Changes**.

**Via the API:**
```
PUT /api/events/<id>
Content-Type: application/json

{ "name": "Sunday Service – May 25", "date": "2026-05-25T10:00:00" }
```

You can supply `name`, `date`, or both. At least one field is required. An invalid or blank `name`, or an unparseable `date`, returns `400`.

### Attendance reports and historical accuracy

The **Reports** page (`/reports`) shows which members were present or absent for a given event. The expected member list is calculated at the time you view the report and reflects who was in the group **on or before the event date**.

This means:
- A member added to a group **after** an event took place will **not** appear in that event's report — they were not yet in the group when the event occurred.
- A member who was in the group at the time of the event **will** appear, even if they have since been removed.
- Members whose group join date is **unknown** (i.e. they existed before this feature was introduced) are treated as having always been in the group and will appear on all historical reports.

This behaviour ensures that archived event reports remain an accurate record of who was expected to attend at the time.

- A **deactivated member** is excluded from all events that fall after their last active date. Events on or before their last active day still show them as expected. Their past attendance records are never removed.

---

## 8. The Database

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
| `member_groups` | Junction table linking members to groups (many-to-many) |
| `events` | Scheduled services / gatherings |
| `attendance` | Attendance records per event per member |

---

## 9. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ in production | Flask session signing key — keep secret |
| `FLASK_ENV` | Optional | `development` (default) or `production` |
| `DATABASE_URL` | Optional | Defaults to SQLite; set for PostgreSQL |

Configure these in your `.env` file (copied from `.env.example`).

---

## 10. Switching to PostgreSQL

1. Set `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/shepherd
   ```

2. Ensure `psycopg2-binary` is installed (already in `requirements.txt`).

3. Create the database in PostgreSQL:
   ```sql
   CREATE DATABASE shepherd;
   ```

4. Initialize tables:
   ```powershell
   $env:FLASK_APP = "run.py"
   flask init-db
   ```

5. Start the app.

> For production deployments, also set `FLASK_ENV=production` and ensure `SECRET_KEY` is a strong random value.

---

## 11. URL Reference

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
| `GET /members` | Admin | Members list + add form |
| `GET /members/<id>/edit` | Admin | Edit member form |
| `POST /members/<id>/edit` | Admin | Submit member edit |
| `POST /members/<id>/deactivate` | Admin | Deactivate a member |
| `POST /members/<id>/reactivate` | Admin | Reactivate a member |
| `GET /events/<id>/edit` | Admin | Edit event form |
| `POST /events/<id>/edit` | Admin | Submit event edit form |
| `GET /events/<id>/attendance` | Admin | Take attendance for event |
| `POST /events/<id>/attendance/quick_add` | Admin | Walk-in quick-add (JSON body: `{"name": "..."}`) |
| `GET /events/<id>/attendance/pdf` | Admin | Download attendance PDF |

### REST API

All API endpoints require authentication. Unauthenticated requests return `401 {"error": "Authentication required"}`.

| Endpoint | Methods | Description |
|---|---|---|
| `/api/members/` | GET, POST | List / create members (supports `group_id` or `group_ids`) |
| `/api/members/<id>` | GET, PUT, DELETE | Get / update / delete a member (supports `group_ids` for multi-group assignment) |
| `/api/groups/` | GET, POST | List / create groups |
| `/api/groups/<id>` | GET, PUT, DELETE | Get / update / delete a group (ALL MEMBERS group is protected) |
| `/api/events/` | GET, POST | List / create events |
| `/api/events/<id>` | GET, PUT, DELETE | Get / update / delete an event |
| `/api/attendance/` | GET, POST | List / record attendance |
| `/api/attendance/<id>` | PUT, DELETE | Update / delete an attendance record |
| `/api/attendance/event/<id>/status` | GET | Attendance summary (expected/present/absent by event group) |

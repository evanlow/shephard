# Shepherd — Superuser Guide

This guide is for **Superusers** — the highest-privilege account level in Shepherd. It covers everything you can do that a regular Admin cannot, as well as a complete reference for all features available to you.

---

## Table of Contents

1. [What Is a Superuser?](#1-what-is-a-superuser)
2. [Logging In](#2-logging-in)
3. [Managing Admin Users](#3-managing-admin-users)
4. [Managing Members](#4-managing-members)
5. [Managing Groups](#5-managing-groups)
6. [Managing Events](#6-managing-events)
7. [Archiving and Deleting Events](#7-archiving-and-deleting-events)
8. [Taking Attendance](#8-taking-attendance)
9. [Reports and PDF Export](#9-reports-and-pdf-export)
10. [URL and API Reference](#10-url-and-api-reference)

---

## 1. What Is a Superuser?

Shepherd has two types of admin accounts:

| Capability | Admin | Superuser |
|---|:---:|:---:|
| Log in to the app | ✅ | ✅ |
| Create and edit members, groups, events | ✅ | ✅ |
| Take attendance | ✅ | ✅ |
| Download attendance PDFs | ✅ | ✅ |
| View reports | ✅ | ✅ |
| Deactivate / reactivate members | ✅ | ✅ |
| **Delete** members, groups | ❌ | ✅ |
| **Archive / unarchive** events | ❌ | ✅ |
| **Delete** events (archived only) | ❌ | ✅ |
| **Create / delete / toggle** admin users | ❌ | ✅ |

In short: Superusers can do everything an Admin can do, plus all destructive and user-management operations.

---

## 2. Logging In

Navigate to:
```
http://<your-server>/login
```

Enter your username and password. After login you will be taken to the **Dashboard**, which gives you a summary of members, groups, and upcoming events.

> If you have forgotten your password, a Superuser account can only be reset directly in the database. See the [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for database access instructions.

---

## 3. Managing Admin Users

This section is exclusive to Superusers.

### Viewing all users

From the Dashboard, click **Manage Admin Users**, or go directly to:
```
http://<your-server>/admin/users
```

You will see a table of all admin accounts, their email addresses, and their current role (Admin or Superuser).

### Creating a new admin

1. On the Users page, click **+ New User**.
2. Fill in:
   - **Username** — must be unique
   - **Email** — must be unique
   - **Password** / **Confirm Password** — minimum 8 characters
3. Click **Create User**.

New accounts created via the UI are regular **Admins**. To promote someone to Superuser, update the database directly:
```sql
UPDATE users SET is_superuser = 1 WHERE username = 'their_username';
```

### Granting or revoking admin access

Click the **Toggle Admin** button next to a user to grant or revoke their admin access. This allows you to temporarily disable a user's access without deleting their account.

> **Note:** You cannot toggle your own account, and Superuser accounts cannot be toggled this way — they are protected.

### Deleting an admin

Click **Delete** next to the user to permanently remove their account.

> **Note:** You cannot delete your own account.

---

## 4. Managing Members

### Adding a member

1. Go to **Members** in the navigation bar.
2. Fill in the member name in the **Add Member** form and select a group if applicable.
3. Click **Add Member**.

Every new member is automatically enrolled in the **ALL MEMBERS** group. If you assign them to an additional group (e.g. "Worship Service"), they will belong to both.

### Editing a member

1. Click the **Edit** button next to the member.
2. Update the name and/or group assignments.
3. Click **Save**.

### Deactivating a member

When a member leaves the church, deactivate them instead of deleting them. Their past attendance records and reports are preserved; they simply stop appearing in future events.

1. Click **Deactivate** next to the member on the **Members** page.
2. Enter their **last active day** — events on and before this date still list them; events after will not.
3. Click **Confirm**.

Deactivated members are hidden by default. Tick **Show inactive** to reveal them — they display an **Inactive** badge with their deactivation date and are greyed out.

### Reactivating a member

If a deactivated member returns to the church:

1. Tick **Show inactive** on the **Members** page.
2. Click **Reactivate** next to the member.
3. Enter their **rejoin date**.
4. Click **Confirm**.

The member's group join date is updated to the rejoin date, correctly excluding the gap period from all future reports. All past attendance records remain untouched.

Both actions are also available from the member's **Edit** page in a Membership Status card at the bottom.

### Deleting a member *(Superuser only)*

Click the **Delete** button next to the member. This permanently removes the member and all their attendance records.

> Consider deactivating instead of deleting — deactivation preserves history while excluding the member from future events.

> Regular Admins cannot delete members — only Superusers can.

---

## 5. Managing Groups

### Creating a group

1. Go to **Groups** in the navigation bar.
2. Enter a group name (and optional description) in the **Create Group** form.
3. Click **Create Group**.

### Editing a group

1. Click the **Edit** button next to the group.
2. Update the name or description.
3. Click **Save**.

> **The ALL MEMBERS group cannot be renamed.** This is a system-managed group that all members belong to. Attempts to rename it will be blocked.

### Deleting a group *(Superuser only)*

Click the **Delete** button next to the group. Members in that group will be **unassigned** from it (they are not deleted), but will remain in ALL MEMBERS.

> **The ALL MEMBERS group cannot be deleted.** It is required by the system.

> Regular Admins cannot delete groups — only Superusers can.

---

## 6. Managing Events

### Creating an event

1. Go to **Events** in the navigation bar.
2. Fill in:
   - **Event Name** — e.g. "Sunday Service"
   - **Date & Time** — use the date/time picker
   - **Group** — the ministry group this event is for
3. Click **Create Event**.

### Editing an event

Both Admins and Superusers can edit an event's name and date/time.

1. Click the **Edit** button next to the event.
2. Update the name and/or date & time.
3. Click **Save Changes**.

> The event's **group cannot be changed** after creation.

> **Archived events cannot be edited.** You must unarchive the event first.

---

## 7. Archiving and Deleting Events *(Superuser only)*

Shepherd uses a two-step process to safely remove events: **archive first, then delete**.

### Why archive?

Archiving allows you to close off an event — preventing any further attendance changes — while keeping the data intact for historical reference. Deletion is permanent and cannot be undone.

### Archiving an event

**Via the UI:**
1. Go to the **Events** page.
2. Click the **Archive** button (yellow) next to the event.
3. Confirm the prompt.
4. The event disappears from the active events list and moves to the **Archived Events** section at the bottom of the page (visible to Superusers only).

**Via the API:**
```
POST /api/events/<id>/archive
```

**Effect of archiving:**
- The event is flagged as `is_archived = true`.
- It no longer appears in the default events list.
- Attendance **cannot be recorded, updated, or deleted** for an archived event. Any such attempt returns an error.
- The event can still be viewed individually by ID.

### Viewing archived events

Archived events are shown in an **Archived Events** section at the bottom of the Events page — visible only to Superusers. Each row shows the event name, group, date, and three actions: **Report**, **Unarchive**, and **Delete**.

**Via the API:**
```
GET /api/events/?archived=true
```

To retrieve all events regardless of archive status:
```
GET /api/events/?archived=false    ← active only (default)
GET /api/events/?archived=true     ← archived only
```
(Omitting the `archived` parameter returns active events only.)

### Unarchiving an event

If you archived an event by mistake, you can reverse it.

**Via the UI:**
1. Scroll to the **Archived Events** section at the bottom of the Events page.
2. Click **Unarchive** next to the event.
3. The event returns to the active events list immediately.

**Via the API:**
```
POST /api/events/<id>/unarchive
```

Once unarchived, the event is fully active again — attendance can be recorded and it appears in the active events list.

### Deleting an event *(requires archiving first)*

An event **must be archived before it can be deleted**. Attempting to delete an active (non-archived) event will return an error (`409 Conflict`).

**To delete an event:**
1. Archive the event first — click **Archive** on the active events list.
2. Scroll to the **Archived Events** section.
3. Click **Delete** next to the event and confirm the prompt.

> **This is permanent.** All attendance records linked to the event will also be removed. This action cannot be undone.

---

## 8. Taking Attendance

1. Go to **Events** and click **Take Attendance** next to an event.
2. You will see a list of all members in the event's group.
3. Click **Present** or **Absent** next to each member to record their status.

> **Attendance cannot be taken for archived events.** The attendance page and API will block any changes.

### Walk-in quick-add

If a visitor or new member attends who is not yet in the system:

1. On the attendance page, use the **Walk-in Quick-Add** card at the top.
2. Type the person's name and click **Add & Mark Present**.
3. Shepherd creates the member, enrolls them in ALL MEMBERS and the event's group (with a join date of the event date), and marks them present — all in one step.

Deactivated members do not appear in the expected list. Only members who were in the group on or before the event date (and not yet deactivated) are shown.

---

## 9. Reports and PDF Export

1. Go to **Reports** in the navigation bar.
2. Select an event from the dropdown.
3. The report shows expected count, present count, and absent count, with a per-member breakdown.
4. Click **Download PDF** to export a formatted attendance sheet.

The PDF includes:
- Event name, date, and group
- Summary table (expected / present / absent)
- Full member-by-member attendance list with colour-coded status

---

## 10. URL and API Reference

### Web UI (Superuser-exclusive pages)

| URL | Description |
|---|---|
| `GET /admin/users` | List all admin users |
| `GET /admin/users/new` | Create new admin form |
| `POST /admin/users/new` | Submit new admin |
| `POST /admin/users/<id>/toggle-admin` | Grant or revoke admin access |
| `POST /admin/users/<id>/delete` | Delete an admin user |

### Web UI (Admin + Superuser)

| URL | Description |
|---|---|
| `GET /dashboard` | Home dashboard |
| `GET /members` | Members list + add form |
| `GET /members/<id>/edit` | Edit member form |
| `POST /members/<id>/edit` | Submit member edit |
| `POST /members/<id>/deactivate` | Deactivate a member |
| `POST /members/<id>/reactivate` | Reactivate a member |
| `POST /members/<id>/delete` | **Superuser only** — delete member |
| `POST /events/<id>/attendance/quick_add` | Walk-in quick-add during attendance |
| `GET /groups` | Groups list + add form |
| `GET /groups/<id>/edit` | Edit group form |
| `POST /groups/<id>/edit` | Submit group edit |
| `POST /groups/<id>/delete` | **Superuser only** — delete group |
| `GET /events` | Events list + create form |
| `GET /events/<id>/edit` | Edit event form |
| `POST /events/<id>/edit` | Submit event edit |
| `POST /events/<id>/delete` | **Superuser only** — delete event (must be archived first) |
| `POST /events/<id>/archive` | **Superuser only** — archive an event |
| `POST /events/<id>/unarchive` | **Superuser only** — unarchive an event |
| `GET /events/<id>/attendance` | Take attendance for event |
| `GET /events/<id>/attendance/pdf` | Download attendance PDF |
| `GET /reports` | Reports page |

### REST API

All API endpoints require authentication. Unauthenticated requests return `401`.

| Endpoint | Method | Access | Description |
|---|---|---|---|
| `/api/members/` | GET, POST | Admin | List / create members |
| `/api/members/<id>` | GET, PUT | Admin | Get / update a member |
| `/api/members/<id>` | DELETE | **Superuser** | Delete a member |
| `/api/groups/` | GET, POST | Admin | List / create groups |
| `/api/groups/<id>` | GET, PUT | Admin | Get / update a group |
| `/api/groups/<id>` | DELETE | **Superuser** | Delete a group |
| `/api/events/` | GET, POST | Admin | List / create events |
| `/api/events/<id>` | GET, PUT | Admin | Get / update an event |
| `/api/events/<id>` | DELETE | **Superuser** | Delete an event (must be archived) |
| `/api/events/<id>/archive` | POST | **Superuser** | Archive an event |
| `/api/events/<id>/unarchive` | POST | **Superuser** | Unarchive an event |
| `/api/attendance/` | GET, POST | Admin | List / record attendance |
| `/api/attendance/<id>` | PUT, DELETE | Admin | Update / delete attendance record |
| `/api/attendance/event/<id>/status` | GET | Admin | Attendance summary for an event |

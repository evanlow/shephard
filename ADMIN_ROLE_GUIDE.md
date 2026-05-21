# Shepherd — Admin User Guide

**Shepherd** is a church attendance management system. This guide is for users with the **Admin** role — you can manage all church data and take attendance. Actions that are restricted to Superusers (deleting records, archiving events, managing other user accounts) are noted where relevant.

> Need to do something not listed here? Ask a **Superuser** — they can perform all Admin actions plus deletions, archiving, and user management. See [SUPERUSERS_GUIDE.md](SUPERUSERS_GUIDE.md).

---

## Table of Contents

1. [Logging In](#1-logging-in)
2. [Dashboard](#2-dashboard)
3. [Managing Members](#3-managing-members)
4. [Managing Groups](#4-managing-groups)
5. [Managing Events](#5-managing-events)
6. [Taking Attendance](#6-taking-attendance)
7. [Reports and PDF Export](#7-reports-and-pdf-export)
8. [URL Reference](#8-url-reference)

---

## 1. Logging In

Navigate to:
```
http://<your-server>/login
```

Enter your username and password. After login you will be taken to the **Dashboard**.

> If you have forgotten your password, contact a Superuser — passwords can only be reset directly in the database.

---

## 2. Dashboard

The Dashboard gives you an at-a-glance summary:
- Total number of members
- Total number of groups
- Upcoming events

Use the navigation bar at the top to access Members, Groups, Events, and Reports.

---

## 3. Managing Members

### Adding a member

1. Go to **Members** in the navigation bar.
2. Fill in the member name in the **Add Member** form and select a group if applicable.
3. Click **Add Member**.

Every new member is automatically enrolled in the **ALL MEMBERS** group. If you assign them to an additional group (e.g. "Worship Service"), they belong to both simultaneously.

### Editing a member

1. Click **Edit** next to the member.
2. Update the name, group assignments, or member-since date.
3. Click **Save Changes**.

The **Member since** date controls which historical events the member is expected to have attended — events before this date will not list them.

### Deactivating a member

When a member leaves the church, deactivate them instead of deleting them. Their past attendance records are preserved; they simply stop appearing in future events.

1. On the **Members** page, click **Deactivate** next to the member.
2. Enter their **last active day** — events on and before this date still list them; events after will not.
3. Click **Confirm**.

Deactivated members are hidden by default. Tick **Show inactive** to reveal them — they display an **Inactive** badge with the deactivation date and are greyed out with a strikethrough name.

### Reactivating a member

If a deactivated member returns to the church:

1. Tick **Show inactive** on the **Members** page.
2. Click **Reactivate** next to the member.
3. Enter their **rejoin date** — they will appear in attendance from this date onward.
4. Click **Confirm**.

Reactivation updates the member's group join date to the rejoin date, correctly excluding the gap period from all reports. All past attendance records remain untouched.

Both deactivate and reactivate are also available from the member's **Edit** page in a dedicated **Membership Status** card.

---

## 4. Managing Groups

### Creating a group

1. Go to **Groups** in the navigation bar.
2. Enter a group name (and optional description) in the **Create Group** form.
3. Click **Create Group**.

### Editing a group

1. Click **Edit** next to the group.
2. Update the name or description.
3. Click **Save**.

> **The ALL MEMBERS group cannot be renamed.** It is a system-managed group that all members belong to automatically.

> Deleting groups is restricted to Superusers.

---

## 5. Managing Events

### Creating an event

1. Go to **Events** in the navigation bar.
2. Fill in:
   - **Event Name** — e.g. "Sunday Service"
   - **Date & Time** — use the date/time picker
   - **Group** — the ministry group this event is for
3. Click **Create Event**.

### Editing an event

1. Click the **Edit** button next to the event.
2. Update the name and/or date & time.
3. Click **Save Changes**.

> The event's **group cannot be changed** after creation.

> **Archiving and deleting events** is restricted to Superusers.

---

## 6. Taking Attendance

1. Go to **Events** and click **Take Attendance** next to an event.
2. You will see a list of all members in the event's group who were active on the event date.
3. Click **Present** or **Absent** next to each member to record their status.

The expected member list only includes members who:
- Were assigned to the group **on or before** the event date, and
- Were **not deactivated** before the event date.

### Walk-in quick-add

If a visitor or new member attends who is not yet in the system:

1. Use the **Walk-in Quick-Add** card at the top of the attendance page.
2. Type the person's name and click **Add & Mark Present**.
3. Shepherd creates the member, enrolls them in ALL MEMBERS and the event's group (with a join date of the event date), and marks them present — all in one step.

> **Attendance cannot be taken for archived events.**

---

## 7. Reports and PDF Export

1. Go to **Reports** in the navigation bar.
2. Select an event from the dropdown.
3. The report shows expected count, present count, and absent count, with a per-member breakdown.
4. Click **Download PDF** to export a formatted attendance sheet.

The PDF includes:
- Event name, date, and group
- Summary table (expected / present / absent)
- Full member-by-member attendance list with colour-coded status

**Historical accuracy:** The expected member list for any event reflects who was in the group on or before the event date and was not yet deactivated. This means reports are an accurate snapshot of who was expected at the time, regardless of group or membership changes made since.

---

## 8. URL Reference

All pages require you to be logged in. Unauthenticated requests redirect to the login page.

| URL | Description |
|---|---|
| `GET /dashboard` | Home dashboard |
| `GET /members` | Members list + add form |
| `GET /members/<id>/edit` | Edit member form |
| `POST /members/<id>/edit` | Submit member edit |
| `POST /members/<id>/deactivate` | Deactivate a member |
| `POST /members/<id>/reactivate` | Reactivate a member |
| `GET /groups` | Groups list + add form |
| `GET /groups/<id>/edit` | Edit group form |
| `POST /groups/<id>/edit` | Submit group edit |
| `GET /events` | Events list + create form |
| `GET /events/<id>/edit` | Edit event form |
| `POST /events/<id>/edit` | Submit event edit |
| `GET /events/<id>/attendance` | Take attendance for event |
| `POST /events/<id>/attendance/quick_add` | Walk-in quick-add (JSON body: `{"name": "..."}`) |
| `GET /events/<id>/attendance/pdf` | Download attendance PDF |
| `GET /reports` | Reports page |

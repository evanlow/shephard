# Shepherd System Specification

## 1. Overview

**Shepherd** is a church attendance and member-care system designed to help authorised church administrators record attendance for worship services, Sunday School, and other church gatherings.

The system is intended for churches that need a simple but accountable way to:

- Maintain a list of members and newcomers.
- Organise people into groups or classes.
- Create attendance events such as worship services or Sunday School sessions.
- Mark attendance during the event.
- Retrieve attendance records for reporting, accountability, and follow-up.
- Identify absentees so pastoral or administrative follow-up can be carried out.

Shepherd is not designed as a self-check-in system. Members do not log in and do not mark their own attendance. Attendance is marked by authorised administrators only.

---

## 2. Background and Business Context

The initial requirement came from a church that needs an attendance system for worship services and Sunday School.

The current process is broadly:

1. Church members attend worship service or Sunday School.
2. Administrators mark their attendance.
3. Attendance data is kept for accountability and reporting.
4. Newcomers fill in a welcome form.
5. Newcomers are later added into a database or spreadsheet for future attendance tracking.
6. The church may use absentee information for follow-up.

The church has approximately:

- 500 active members.
- 700 names in the broader record.

Personal data should be kept minimal. The initial requirement is to store names only, avoiding mobile numbers or sensitive personal data unless the church later approves and documents the need for it.

---

## 3. Goals

Shepherd aims to provide a secure and practical web-based system that allows church administrators to track attendance accurately and efficiently.

Primary goals:

1. Provide a central member list.
2. Support group or class assignment.
3. Support event-based attendance taking.
4. Allow multiple administrators to access the system.
5. Protect access through administrator login.
6. Allow attendance data to be retrieved when needed.
7. Support future reporting for absentees, attendance trends, and follow-up.
8. Keep personal data collection minimal and PDPA-conscious.

---

## 4. Non-Goals for the Initial MVP

The initial MVP does not aim to provide:

1. Member self-login.
2. QR-code self-check-in by members.
3. Public registration pages.
4. Online payment or donation tracking.
5. Full church CRM functionality.
6. Mobile app installation.
7. SMS or WhatsApp follow-up automation.
8. Advanced analytics dashboards.
9. Biometric or facial-recognition attendance.

These may be considered in later phases only if the church confirms the need, legal basis, and operational readiness.

---

## 5. User Types

### 5.1 Superuser

A Superuser has the highest level of system access.

Typical responsibilities:

- Create administrator accounts.
- Manage groups.
- Manage members.
- Create events.
- View and export attendance data.
- Perform system-level administrative tasks.

### 5.2 Admin

An Admin is an authorised church user who can perform attendance-related tasks.

Typical responsibilities:

- View members and groups.
- Create or manage events, depending on permission level.
- Mark attendance.
- View attendance summaries.

### 5.3 Member

A Member is a person whose attendance is tracked in the system.

Important distinction:

- Members do not log in.
- Members do not self-mark attendance.
- Members are represented as records inside the system.

### 5.4 Newcomer

A Newcomer is a person attending for the first time or not yet part of the regular member list.

Initial handling may be manual:

- Newcomer fills in a welcome form.
- Admin later adds the newcomer into Shepherd.
- Newcomer may later be converted into a regular active member.

---

## 6. Core Concepts

### 6.1 Member

A Member represents a person whose attendance may be tracked.

Minimum information:

- Name.
- Group assignment, if applicable.
- Status, if implemented later, such as active, inactive, or newcomer.

Initial data collection should remain minimal.

### 6.2 Group or Class

A Group represents a collection of members who are expected to attend a certain type of event.

Examples:

- Adult Worship 8AM.
- Adult Worship 10AM.
- Sunday School Nursery.
- Sunday School Primary.
- Youth Group.

For the current MVP, the system may use a simple one-member-to-one-group model. In future, this may evolve into a many-to-many model where one person can belong to multiple groups, such as Worship Service, Cell Group, and Choir.

### 6.3 Event

An Event represents a specific attendance-taking occasion.

Examples:

- Worship Service - 3 May 2026 - 8:00 AM.
- Worship Service - 3 May 2026 - 10:00 AM.
- Sunday School - 3 May 2026 - Primary Class.

Each event should be linked to a group. The event's expected attendees are derived from the members assigned to that group.

### 6.4 Attendance Record

An Attendance Record stores whether a member was present for a specific event.

For the MVP logic:

- Expected members are the members assigned to the event's group.
- Present members are expected members marked as present.
- Absent members are expected members who were not marked present.

This means absence can be calculated rather than manually marked one by one.

---

## 7. Core Workflow

The main Shepherd workflow is:

1. Admin logs in.
2. Admin creates or selects a group.
3. Admin adds members to the group.
4. Admin creates an event linked to that group.
5. Admin opens the event attendance page.
6. System displays expected members for that event.
7. Admin marks attendees as present.
8. System calculates absentees as expected members not marked present.
9. Admin views attendance summary.
10. Admin retrieves data for reporting or follow-up.

Example:

- Group: Adult Worship 8AM.
- Members: Alice, Bob, Charlie.
- Event: Worship Service - 3 May 2026 - 8AM.
- Alice and Bob are marked present.
- Charlie is not marked present.
- System reports:
  - Expected count: 3.
  - Present count: 2.
  - Absent count: 1.
  - Absent member: Charlie.

---

## 8. Functional Requirements

### 8.1 Authentication and Access Control

The system shall require administrators to log in before accessing attendance functionality.

Requirements:

1. Admin users shall log in using username and password.
2. Passwords shall be stored as password hashes, not plain text.
3. Unauthenticated web users shall be redirected to login.
4. Unauthenticated API requests shall return an authentication error.
5. The system shall support at least two roles:
   - Admin.
   - Superuser.
6. The first Superuser account shall be created using a command-line setup command.

### 8.2 Member Management

The system shall allow authorised administrators to manage member records.

Requirements:

1. Create member.
2. View member list.
3. View member details.
4. Update member name.
5. Assign or unassign member to a group.
6. Delete member, if permitted.
7. Store minimal personal data for PDPA-conscious operation.

Initial member fields:

- `id`
- `name`
- `group_id`
- `created_at`

Possible future fields:

- `status`
- `notes`
- `created_by`
- `updated_at`

### 8.3 Group Management

The system shall allow authorised administrators to manage groups.

Requirements:

1. Create group.
2. View group list.
3. Update group name.
4. Delete group.
5. Preserve members when a group is deleted by unassigning them rather than deleting them.

Initial group fields:

- `id`
- `name`
- `created_at`

### 8.4 Event Management

The system shall allow authorised administrators to create and manage events.

Requirements:

1. Create event.
2. Link event to a group.
3. View event list.
4. Filter events by group.
5. View event details.
6. Delete event, if permitted.

Initial event fields:

- `id`
- `name`
- `date` or `start_datetime`
- `group_id`
- `created_at`

### 8.5 Attendance Taking

The system shall allow authorised administrators to mark attendance for an event.

Requirements:

1. Attendance shall be taken against an event.
2. Event shall be linked to a group.
3. Expected attendees shall be derived from the event's group membership.
4. Admin shall mark members as present.
5. Unmarked expected members shall be treated as absent for reporting.
6. The system shall prevent attendance from being recorded for a member who does not belong to the event's group.
7. The system shall prevent duplicate attendance records for the same member and event.
8. Attendance can be updated if correction is needed.
9. Attendance can be deleted if correction is needed, subject to permission.

### 8.6 Event Attendance Status

The system shall provide an attendance status view for each event.

The status shall include:

- Event ID.
- Event name.
- Group ID.
- Expected members.
- Present members.
- Absent members.
- Expected count.
- Present count.
- Absent count.

This is the key reporting contract for Shepherd.

### 8.7 Reporting and Data Retrieval

The system shall allow attendance data to be retrieved when needed.

Initial reporting requirements:

1. Attendance summary by event.
2. Present and absent member list by event.
3. Attendance records filtered by event.
4. Attendance records filtered by member.

Future reporting requirements:

1. Attendance trends by date range.
2. Consecutive absence report.
3. Member attendance history.
4. Group attendance history.
5. Export to CSV or Excel.
6. Dashboard charts.

---

## 9. API Requirements

The system may expose a REST API for internal use by the web interface or future integrations.

All API endpoints shall require authentication.

Core API areas:

### 9.1 Members

- `GET /api/members/`
- `POST /api/members/`
- `GET /api/members/<id>`
- `PUT /api/members/<id>`
- `DELETE /api/members/<id>`

Member creation and update should support `group_id` assignment.

### 9.2 Groups

- `GET /api/groups/`
- `POST /api/groups/`
- `GET /api/groups/<id>`
- `PUT /api/groups/<id>`
- `DELETE /api/groups/<id>`

### 9.3 Events

- `GET /api/events/`
- `POST /api/events/`
- `GET /api/events/<id>`
- `DELETE /api/events/<id>`

Events should support filtering by `group_id`.

### 9.4 Attendance

- `GET /api/attendance/`
- `POST /api/attendance/`
- `PUT /api/attendance/<id>`
- `DELETE /api/attendance/<id>`
- `GET /api/attendance/event/<event_id>/status`

Attendance queries should support filtering by `event_id` and `member_id`.

---

## 10. Data Storage Requirements

Shepherd shall store member, group, event, attendance, and admin-user records in a relational database.

### 10.1 Development Database

For local development, Shepherd uses SQLite.

Typical local setup:

- SQLite database file.
- Easy to create and reset.
- Suitable for localhost development and testing.

### 10.2 Production Database

For production deployment on AWS, Shepherd should use PostgreSQL on AWS RDS.

Reasons:

- Better support for concurrent users.
- More suitable for production reliability.
- Easier backup and restore options.
- More appropriate for reporting and future scaling.

### 10.3 Environment-Based Configuration

The application should select the database using environment configuration.

Typical approach:

- Local `.env`: SQLite database URL.
- Production environment file or AWS secret: PostgreSQL RDS `DATABASE_URL`.

Example concept:

```text
Development: sqlite:///shepherd_dev.db
Production: postgresql+psycopg2://user:password@rds-endpoint:5432/shepherd
```

Local SQLite database files should not be committed to GitHub.

---

## 11. Data Model

The initial logical data model is as follows.

### 11.1 User

Represents an administrator account.

Fields:

- `id`
- `username`
- `email`
- `password_hash`
- `is_admin`
- `is_superuser`
- `created_at`

### 11.2 Member

Represents a church member or person whose attendance is tracked.

Fields:

- `id`
- `name`
- `group_id`
- `created_at`

Relationships:

- Member belongs to one Group in the MVP.
- Member has many Attendance records.

### 11.3 Group

Represents a church group, service group, or class.

Fields:

- `id`
- `name`
- `created_at`

Relationships:

- Group has many Members.
- Group has many Events.

### 11.4 Event

Represents a specific attendance-taking occasion.

Fields:

- `id`
- `name`
- `date` or `start_datetime`
- `group_id`
- `created_at`

Relationships:

- Event belongs to one Group.
- Event has many Attendance records.

### 11.5 Attendance

Represents a member's attendance record for an event.

Fields:

- `id`
- `event_id`
- `member_id`
- `present`
- `marked_by`, if implemented.
- `marked_at`, if implemented.
- `created_at`

Rules:

- One attendance record per member per event.
- Member must belong to the same group as the event.
- Present members are recorded explicitly.
- Absent members can be derived from expected members not marked present.

---

## 12. Security Requirements

Security requirements:

1. Admin login required for all system functionality.
2. Passwords must be hashed securely.
3. Secret keys and database credentials must be stored in environment variables, not committed to GitHub.
4. Local `.env` files must be excluded from version control.
5. Local SQLite database files must be excluded from version control.
6. Production system should use HTTPS.
7. Production database should not be publicly exposed unless strictly necessary.
8. Access to production database should be restricted by AWS security groups.
9. Only authorised administrators should be able to access attendance data.

---

## 13. PDPA and Privacy Considerations

Shepherd should follow data-minimisation principles.

Initial privacy position:

- Store member names only unless additional fields are formally required.
- Avoid storing mobile numbers by default.
- Avoid storing NRIC, birth date, address, or sensitive personal data unless there is a documented purpose and approval.
- Restrict access to authorised administrators.
- Keep auditability in mind for future enhancements.

Potential future privacy enhancements:

1. Audit log of who marked or changed attendance.
2. Role-based access control by ministry or group.
3. Data retention policy.
4. Export log.
5. Admin activity log.

---

## 14. Deployment Requirements

The intended production deployment is a Flask application hosted on AWS.

Recommended AWS architecture:

- EC2 instance running the Flask app with Gunicorn.
- Nginx as reverse proxy.
- HTTPS using Let's Encrypt or AWS-managed certificate where appropriate.
- PostgreSQL database hosted on AWS RDS.
- Environment variables stored in server environment file or AWS Secrets Manager.
- Backups configured on RDS.

Local development should remain simple using SQLite.

---

## 15. Testing Requirements

The system should include smoke tests and service-layer tests for the main workflows.

Minimum test coverage should include:

1. Admin login required for protected routes.
2. Member creation, update, deletion.
3. Group creation, update, deletion.
4. Member assignment to group.
5. Event creation linked to group.
6. Attendance recording.
7. Duplicate attendance prevention.
8. Rejection of attendance for members outside event group.
9. Event attendance status calculation.
10. Absent members calculated correctly.

A practical MVP test case:

1. Create group `Worship 8AM`.
2. Create members Alice, Bob, and Charlie in the group.
3. Create event `Worship Service - 3 May 2026 - 8AM`.
4. Mark Alice and Bob present.
5. Retrieve event status.
6. Confirm expected count is 3.
7. Confirm present count is 2.
8. Confirm absent count is 1.
9. Confirm Charlie appears in absent members.

---

## 16. Future Enhancements

Possible future enhancements:

### 16.1 Many-to-Many Group Membership

Allow one member to belong to multiple groups.

Example:

- Adult Worship.
- Cell Group.
- Choir.
- Ushering Team.

This would require a `member_groups` association table.

### 16.2 Attendance UI Optimisation

Attendance taking during service should be fast.

Implemented:

- Search-as-you-type member list.
- Present / Undo buttons with AJAX (no page reload).
- Live counters (expected, present, absent) updated in real time.
- Filter by expected, present, absent.
- Mobile-friendly layout.
- Walk-in quick-add: create a new member and mark them present in one step directly
  from the attendance page. The member's `joined_at` is back-dated to the event date
  so the eligibility filter includes them for that event.

Not yet implemented:

- Recently marked list.

### 16.3 Real-Time Updates

Multiple admins may mark attendance concurrently.

Implemented:

- Short polling every 5 seconds against `GET /api/attendance/event/{id}/status`.
- Counters and row states updated without a page reload when another admin changes
  attendance.
- Full page reload triggered automatically if a walk-in (new member) is detected in
  the polling response.
- Last-checked timestamp shown in the page header.

Not yet implemented:

- WebSocket updates using Flask-SocketIO.

### 16.4 Reports and Exports

Future reports:

- Weekly attendance summary.
- Monthly attendance trends.
- Consecutive absence report.
- Group-level attendance percentage.
- Member attendance history.
- CSV or Excel export.

### 16.5 Follow-Up Workflow

Future follow-up features:

- Flag members absent for several consecutive events.
- Add follow-up notes.
- Assign follow-up to an admin or ministry leader.
- Track whether follow-up was completed.

### 16.6 Newcomer Workflow

Future newcomer features:

- Newcomer status.
- First visit date.
- Conversion from newcomer to regular member.
- Newcomer attendance history.
- Optional welcome-form import.

---

## 17. MVP Acceptance Criteria

The MVP can be considered successful when:

1. Superuser can create an admin account.
2. Admin can log in.
3. Admin can create groups.
4. Admin can create members.
5. Admin can assign members to groups.
6. Admin can create events linked to groups.
7. Admin can mark members present for an event.
8. System prevents marking members who are not in the event's group.
9. System prevents duplicate attendance for the same member and event.
10. System shows expected, present, and absent members for an event.
11. Local development works with SQLite.
12. Production can be configured to use PostgreSQL on AWS RDS.
13. Secrets and local database files are not committed to GitHub.

---

## 18. Summary

Shepherd is designed as a focused, admin-operated church attendance system.

The most important business rule is:

```text
Expected attendees = members assigned to the event's group
Present attendees = expected members marked present
Absent attendees = expected members not marked present
```

This rule allows Shepherd to support practical attendance taking, accountability reporting, and future member follow-up while keeping the initial system simple and privacy-conscious.

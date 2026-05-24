# Shepherd — User Acceptance Test Cases

This document contains User Acceptance Test (UAT) cases for the Shepherd church attendance management system. Each test case describes the preconditions, steps to perform, and the expected result.

Test cases are grouped by functional area. Role requirements (Admin or Superuser) are noted per case.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Dashboard](#2-dashboard)
3. [Member Management](#3-member-management)
4. [Group Management](#4-group-management)
5. [Event Management](#5-event-management)
6. [Attendance Taking](#6-attendance-taking)
7. [Attendance Reports and PDF Export](#7-attendance-reports-and-pdf-export)
8. [User Management (Superuser Only)](#8-user-management-superuser-only)
9. [Access Control and Role Restrictions](#9-access-control-and-role-restrictions)

---

## 1. Authentication

### UAT-AUTH-001: Successful login

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | A valid admin account exists |
| **Steps** | 1. Navigate to `/login`. <br>2. Enter a valid username and password. <br>3. Click **Login**. |
| **Expected Result** | User is redirected to the Dashboard. The navigation bar is visible with links to Members, Groups, Events, and Reports. |

---

### UAT-AUTH-002: Login with incorrect password

| Field | Detail |
|---|---|
| **Role** | Any |
| **Preconditions** | A valid admin account exists |
| **Steps** | 1. Navigate to `/login`. <br>2. Enter a valid username with an incorrect password. <br>3. Click **Login**. |
| **Expected Result** | Login fails. An error message is displayed. The user remains on the login page. |

---

### UAT-AUTH-003: Login with non-existent username

| Field | Detail |
|---|---|
| **Role** | Any |
| **Preconditions** | None |
| **Steps** | 1. Navigate to `/login`. <br>2. Enter a username that does not exist and any password. <br>3. Click **Login**. |
| **Expected Result** | Login fails. An error message is displayed. The user remains on the login page. |

---

### UAT-AUTH-004: Unauthenticated access is blocked

| Field | Detail |
|---|---|
| **Role** | Unauthenticated user |
| **Preconditions** | User is not logged in |
| **Steps** | 1. Without logging in, navigate directly to `/dashboard`. |
| **Expected Result** | User is redirected to the login page. The dashboard is not accessible. |

---

### UAT-AUTH-005: Successful logout

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in |
| **Steps** | 1. Click the **Logout** option in the navigation bar. |
| **Expected Result** | User is logged out and redirected to the login page. Navigating to `/dashboard` redirects back to login. |

---

## 2. Dashboard

### UAT-DASH-001: Dashboard displays summary counts

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; at least one member, one group, and one event exist |
| **Steps** | 1. Navigate to `/dashboard`. |
| **Expected Result** | Dashboard displays the total number of members, total number of groups, total events, and a recent events table. |

---

### UAT-DASH-002: Navigation links are accessible from Dashboard

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in |
| **Steps** | 1. Navigate to `/dashboard`. <br>2. Click each navigation link: Members, Groups, Events, Reports. |
| **Expected Result** | Each link navigates to the correct page without errors. |

---

## 3. Member Management

### UAT-MEM-001: Add a new member without a group

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in |
| **Steps** | 1. Navigate to `/members`. <br>2. In the **Add Member** form, enter a member name. <br>3. Leave **Additional Groups** unselected. <br>4. Click **Add Member**. |
| **Expected Result** | Member is created and appears in the members list. The member is automatically enrolled in the **ALL MEMBERS** group. No additional group is assigned. |

---

### UAT-MEM-002: Add a new member with additional group assignment

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; at least one group (other than ALL MEMBERS) exists |
| **Steps** | 1. Navigate to `/members`. <br>2. Enter a member name and select one or more options in **Additional Groups**. <br>3. Click **Add Member**. |
| **Expected Result** | Member is created, enrolled in **ALL MEMBERS**, and also enrolled in each selected additional group. The member appears in those groups' member lists. |

---

### UAT-MEM-003: Edit a member's name

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; at least one member exists |
| **Steps** | 1. Navigate to `/members`. <br>2. Click **Edit** next to a member. <br>3. Change the member's name. <br>4. Click **Save Changes**. |
| **Expected Result** | Member's name is updated. The updated name is reflected in the member list and in any group or event views that reference that member. |

---

### UAT-MEM-004: Edit a member's group assignment

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; at least two groups exist and one member is assigned to one group |
| **Steps** | 1. Navigate to `/members`. <br>2. Click **Edit** next to a member. <br>3. Change the group assignment to a different group. <br>4. Click **Save Changes**. |
| **Expected Result** | Member's group assignment is updated. The member no longer appears in the original group and now appears in the newly assigned group. |

---

### UAT-MEM-005: Deactivate a member

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; an active member exists |
| **Steps** | 1. Navigate to `/members`. <br>2. Click **Deactivate** next to a member. <br>3. Enter a last active day. <br>4. Click **Confirm**. |
| **Expected Result** | Member is deactivated. By default, the member is hidden from the members list. Ticking **Show inactive** reveals the member with an **Inactive** badge. The member does not appear in future event attendance lists. |

---

### UAT-MEM-006: Deactivated member excluded from future events

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | A member has been deactivated; an event exists with a date after the deactivation date |
| **Steps** | 1. Navigate to the attendance page for an event dated after the member's last active day. |
| **Expected Result** | The deactivated member does not appear in the expected attendee list for that event. |

---

### UAT-MEM-007: Reactivate a deactivated member

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; at least one deactivated member exists |
| **Steps** | 1. Navigate to `/members` and tick **Show inactive**. <br>2. Click **Reactivate** next to the deactivated member. <br>3. Enter a rejoin date. <br>4. Click **Confirm**. |
| **Expected Result** | Member is reactivated. The member appears in the active members list without the Inactive badge. The member appears in expected attendee lists for events dated on or after the rejoin date. Past attendance records remain unchanged. |

---

### UAT-MEM-008: Delete a member (Superuser only)

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; a member with attendance records exists |
| **Steps** | 1. Navigate to `/members`. <br>2. Click **Delete** next to a member. <br>3. Confirm the deletion prompt. |
| **Expected Result** | Member is permanently removed from the system. All attendance records for that member are also deleted. The member no longer appears in any list. |

---

### UAT-MEM-009: Admin cannot delete a member

| Field | Detail |
|---|---|
| **Role** | Admin (non-Superuser) |
| **Preconditions** | User is logged in as a regular Admin |
| **Steps** | 1. Navigate to `/members`. <br>2. Observe the list of members. |
| **Expected Result** | No **Delete** button is visible for any member. The Admin cannot delete members. |

---

## 4. Group Management

### UAT-GRP-001: Create a new group

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in |
| **Steps** | 1. Navigate to `/groups`. <br>2. Enter a group name in the **Create Group** form. <br>3. Optionally enter a description. <br>4. Click **Create Group**. |
| **Expected Result** | New group appears in the groups list. The group is available when creating events or assigning members. |

---

### UAT-GRP-002: Edit a group's name

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; at least one non-system group exists |
| **Steps** | 1. Navigate to `/groups`. <br>2. Click **Edit** next to a group. <br>3. Update the group name. <br>4. Click **Save**. |
| **Expected Result** | Group name is updated and the new name is reflected throughout the system. |

---

### UAT-GRP-003: ALL MEMBERS group cannot be renamed

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in |
| **Steps** | 1. Navigate to `/groups`. <br>2. Attempt to edit and rename the **ALL MEMBERS** group. <br>3. Click **Save**. |
| **Expected Result** | The rename is blocked. An error or informational message is shown indicating that ALL MEMBERS cannot be renamed. The group name remains unchanged. |

---

### UAT-GRP-004: Delete a group unassigns members but does not delete them (Superuser only)

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; a group with members exists |
| **Steps** | 1. Navigate to `/groups`. <br>2. Click **Delete** next to a group. <br>3. Confirm the deletion prompt. |
| **Expected Result** | The group is deleted. Members who were in that group are unassigned from it but remain in the system and in ALL MEMBERS. The members are not deleted. |

---

### UAT-GRP-005: ALL MEMBERS group cannot be deleted

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser |
| **Steps** | 1. Navigate to `/groups`. <br>2. Attempt to delete the **ALL MEMBERS** group. |
| **Expected Result** | The delete action is blocked. An error or informational message is shown. The ALL MEMBERS group remains. |

---

### UAT-GRP-006: Admin cannot delete a group

| Field | Detail |
|---|---|
| **Role** | Admin (non-Superuser) |
| **Preconditions** | User is logged in as a regular Admin |
| **Steps** | 1. Navigate to `/groups`. |
| **Expected Result** | No **Delete** button is visible for any group. The Admin cannot delete groups. |

---

## 5. Event Management

### UAT-EVT-001: Create a new event

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; at least one group exists |
| **Steps** | 1. Navigate to `/events`. <br>2. Fill in the **Event Name**, **Date & Time**, and select a **Group**. <br>3. Click **Create Event**. |
| **Expected Result** | Event is created and appears in the events list with the correct name, date/time, and group. The **Take Attendance** button is available for the event. |

---

### UAT-EVT-002: Edit an event's name and date

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; a non-archived event exists |
| **Steps** | 1. Navigate to `/events`. <br>2. Click **Edit** next to an event. <br>3. Change the event name and date/time. <br>4. Click **Save Changes**. |
| **Expected Result** | The event is updated with the new name and date/time. The events list reflects the changes. |

---

### UAT-EVT-003: Event group cannot be changed after creation

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; an event exists |
| **Steps** | 1. Navigate to `/events`. <br>2. Click **Edit** next to an event. <br>3. Observe the group field on the edit form. |
| **Expected Result** | The group field is not editable. The event's group is fixed at creation and cannot be changed. |

---

### UAT-EVT-004: Filter events by group

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; events exist for at least two different groups |
| **Steps** | 1. Use `GET /api/events/?group_id=<id>` with a specific group ID. |
| **Expected Result** | Only events belonging to the specified group are returned. Events from other groups are not included. |

---

### UAT-EVT-005: Archive an event (Superuser only)

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; a non-archived event exists |
| **Steps** | 1. Navigate to `/events`. <br>2. Click **Archive** (yellow button) next to an event. <br>3. Confirm the prompt. |
| **Expected Result** | The event disappears from the active events list. It appears in the **Archived Events** section at the bottom of the page. The event is flagged as archived. |

---

### UAT-EVT-006: Archived event cannot be edited

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; an archived event exists |
| **Steps** | 1. Open `/events/<id>/edit` for an archived event. <br>2. Attempt to submit a change. |
| **Expected Result** | The edit page renders, but submitting changes is blocked. An error is shown indicating that archived events cannot be edited. |

---

### UAT-EVT-007: Unarchive an event (Superuser only)

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; an archived event exists |
| **Steps** | 1. Scroll to the **Archived Events** section on the Events page. <br>2. Click **Unarchive** next to the event. |
| **Expected Result** | The event moves back to the active events list. It can be edited and attendance can be taken again. |

---

### UAT-EVT-008: Delete an archived event (Superuser only)

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; an archived event exists |
| **Steps** | 1. Scroll to the **Archived Events** section. <br>2. Click **Delete** next to the archived event. <br>3. Confirm the prompt. |
| **Expected Result** | The event is permanently deleted along with all its attendance records. The event no longer appears anywhere in the system. |

---

### UAT-EVT-009: Cannot delete a non-archived event (Superuser only)

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; a non-archived event exists |
| **Steps** | 1. Attempt to delete an active (non-archived) event via `POST /events/<id>/delete` or the API. |
| **Expected Result** | The deletion is rejected with a `409 Conflict` error. The event is not deleted. |

---

## 6. Attendance Taking

### UAT-ATT-001: Expected attendees are members in the event's group

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | A group exists with members; an event linked to that group exists |
| **Steps** | 1. Navigate to the attendance page for the event (`/events/<id>/attendance`). |
| **Expected Result** | The expected attendee list shows only members who belong to the event's group and were active on or before the event date. Members from other groups are not shown. |

---

### UAT-ATT-002: Mark a member as present

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is on the attendance page for an event; expected members are listed |
| **Steps** | 1. Click **Present** next to a member. |
| **Expected Result** | The member is recorded as present. The present count increments. The member's row updates to reflect the present status without a full page reload. |

---

### UAT-ATT-003: Mark a member as absent (undo present)

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | A member has been marked present for an event |
| **Steps** | 1. On the attendance page, click **Absent** next to a member who is currently marked present. |
| **Expected Result** | The present mark is removed. The present count decrements and the absent count increments. The member's row updates to reflect the absent status. |

---

### UAT-ATT-004: Attendance summary counts are correct

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | A group has 3 members (Alice, Bob, Charlie); an event exists for that group; Alice and Bob are marked present; Charlie is not marked |
| **Steps** | 1. On the attendance page or via `GET /api/attendance/event/<id>/status`, check the counts. |
| **Expected Result** | Expected count: 3. Present count: 2. Absent count: 1. Charlie appears in the absent members list. Alice and Bob appear in the present members list. |

---

### UAT-ATT-005: Duplicate attendance record is prevented

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | A member has already been marked present for an event |
| **Steps** | 1. Attempt to create a second attendance record for the same member and event via `POST /api/attendance/`. |
| **Expected Result** | The duplicate is rejected with an appropriate error (e.g. `409 Conflict`). Only one attendance record exists for that member and event. |

---

### UAT-ATT-006: Attendance cannot be recorded for a member outside the event's group

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | Member A belongs to Group X; an event exists for Group Y |
| **Steps** | 1. Attempt to record attendance for Member A against the Group Y event via `POST /api/attendance/`. |
| **Expected Result** | The request is rejected with an error. Member A does not appear in the attendance list for the Group Y event. |

---

### UAT-ATT-007: Deactivated member does not appear in attendance

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | A member has been deactivated with a last active day before the event date |
| **Steps** | 1. Navigate to the attendance page for the event. |
| **Expected Result** | The deactivated member is not listed in the expected attendees. They do not contribute to the expected count for that event. |

---

### UAT-ATT-008: Walk-in quick-add creates member and marks present

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is on the attendance page for an active event; the person is not yet in the system |
| **Steps** | 1. In the **Walk-in Quick-Add** card, type the person's name. <br>2. Click **Add & Mark Present**. |
| **Expected Result** | A new member is created, enrolled in ALL MEMBERS and the event's group (with a join date of the event date), and marked present — all in one step. The new member appears in the present list. The counters update accordingly. |

---

### UAT-ATT-009: Attendance cannot be taken for an archived event

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | An archived event exists |
| **Steps** | 1. Navigate to the attendance page for the archived event. <br>2. Attempt to mark a member present via the UI or API for the archived event. |
| **Expected Result** | The attendance page can be viewed, but attendance changes are blocked for archived events. The API returns an error for attendance write operations against an archived event. |

---

### UAT-ATT-010: Real-time polling updates counters without page reload

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser (two concurrent sessions) |
| **Preconditions** | Two admin users are on the attendance page for the same event simultaneously |
| **Steps** | 1. Admin A marks a member present. <br>2. Wait up to 5 seconds. |
| **Expected Result** | Admin B's attendance page automatically updates the counters and row states to reflect the change made by Admin A, without a full page reload. A last-checked timestamp is visible in the page header. |

---

### UAT-ATT-011: Walk-in detected by polling triggers full page reload

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser (two concurrent sessions) |
| **Preconditions** | Two admin users are on the attendance page for the same event simultaneously |
| **Steps** | 1. Admin A adds a walk-in member using the quick-add feature. <br>2. Wait up to 5 seconds for Admin B's page to poll. |
| **Expected Result** | Admin B's page automatically performs a full reload so the new walk-in member row appears correctly in their view. |

---

## 7. Attendance Reports and PDF Export

### UAT-RPT-001: Reports page displays event attendance summary

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; an event with attendance data exists |
| **Steps** | 1. Navigate to `/reports`. <br>2. Select an event from the dropdown. |
| **Expected Result** | The report displays the expected count, present count, and absent count for the selected event, along with a per-member breakdown showing each member's attendance status. |

---

### UAT-RPT-002: Historical report reflects membership at time of event

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | A member was added to a group after a past event occurred; the past event has attendance data |
| **Steps** | 1. Navigate to `/reports`. <br>2. Select the past event. |
| **Expected Result** | The member added after the event date is NOT included in the expected list for that event. The expected list reflects who was in the group on or before the event date, regardless of subsequent group changes. |

---

### UAT-RPT-003: Download attendance PDF

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | User is logged in; an event with attendance data exists |
| **Steps** | 1. Navigate to the attendance page for an event or the Reports page. <br>2. Click **Download PDF**. |
| **Expected Result** | A PDF file is downloaded. The PDF includes the event name, date, and group; a summary table with expected, present, and absent counts; and a full member-by-member attendance list with colour-coded status indicators. |

---

### UAT-RPT-004: API returns correct attendance status for an event

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | An event exists with members marked present and some absent |
| **Steps** | 1. Send `GET /api/attendance/event/<id>/status`. |
| **Expected Result** | The JSON response includes: `event_id`, `event_name`, `group_id`, `expected_members` (list of expected members), `present_members` (list of present members, including `attendance_id`), `absent_members` (list of absent members), `expected_count`, `present_count`, and `absent_count`. All counts are accurate. |

---

### UAT-RPT-005: Filter attendance records by event

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | Attendance records exist for at least two different events |
| **Steps** | 1. Send `GET /api/attendance/?event_id=<id>` with a specific event ID. |
| **Expected Result** | Only attendance records for the specified event are returned. |

---

### UAT-RPT-006: Filter attendance records by member

| Field | Detail |
|---|---|
| **Role** | Admin or Superuser |
| **Preconditions** | A member has attendance records across multiple events |
| **Steps** | 1. Send `GET /api/attendance/?member_id=<id>` with a specific member ID. |
| **Expected Result** | Only attendance records for the specified member are returned across all events. |

---

## 8. User Management (Superuser Only)

### UAT-USR-001: View all admin users

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; multiple admin accounts exist |
| **Steps** | 1. Navigate to `/admin/users`. |
| **Expected Result** | A table lists all admin accounts with their usernames, email addresses, and roles (Admin or Superuser). |

---

### UAT-USR-002: Create a new admin user

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser |
| **Steps** | 1. Navigate to `/admin/users`. <br>2. Click **+ New User**. <br>3. Fill in a unique username, unique email, and a password of at least 8 characters. <br>4. Confirm the password and click **Create User**. |
| **Expected Result** | A new Admin account is created and appears in the users list. The new account can log in with the provided credentials. The new account has the Admin role (not Superuser). |

---

### UAT-USR-003: Create admin with duplicate username is rejected

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; an admin with username "admin1" exists |
| **Steps** | 1. Navigate to `/admin/users/new`. <br>2. Enter "admin1" as the username and fill in all other fields. <br>3. Click **Create User**. |
| **Expected Result** | The creation is rejected. An error message indicates the username is already taken. No duplicate account is created. |

---

### UAT-USR-004: Toggle admin access (grant or revoke)

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; a non-Superuser admin account exists |
| **Steps** | 1. Navigate to `/admin/users`. <br>2. Click **Toggle Admin** next to a regular Admin user. |
| **Expected Result** | The admin's `is_admin` access flag is toggled. If revoked, the user can still log in with valid credentials but is blocked from admin-only routes. If granted, the user regains access to admin routes. |

---

### UAT-USR-005: Superuser cannot toggle their own account

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser |
| **Steps** | 1. Navigate to `/admin/users`. <br>2. Attempt to click **Toggle Admin** on the currently logged-in Superuser account. |
| **Expected Result** | The action is blocked. An error or informational message is shown. The Superuser's own account is not affected. |

---

### UAT-USR-006: Delete an admin user

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser; another admin account (not the current user) exists |
| **Steps** | 1. Navigate to `/admin/users`. <br>2. Click **Delete** next to a different admin user. <br>3. Confirm the prompt. |
| **Expected Result** | The admin account is permanently deleted and removed from the users list. That user can no longer log in. |

---

### UAT-USR-007: Superuser cannot delete their own account

| Field | Detail |
|---|---|
| **Role** | Superuser |
| **Preconditions** | User is logged in as Superuser |
| **Steps** | 1. Navigate to `/admin/users`. <br>2. Attempt to delete the currently logged-in Superuser's own account. |
| **Expected Result** | The action is blocked. An error or informational message is shown. The Superuser's account remains. |

---

### UAT-USR-008: Regular Admin cannot access user management

| Field | Detail |
|---|---|
| **Role** | Admin (non-Superuser) |
| **Preconditions** | User is logged in as a regular Admin |
| **Steps** | 1. Navigate directly to `/admin/users`. |
| **Expected Result** | Access is denied. The user sees a 403 Forbidden page or is redirected. The user management page is not accessible. |

---

## 9. Access Control and Role Restrictions

### UAT-ACL-001: Unauthenticated API requests return 401

| Field | Detail |
|---|---|
| **Role** | Unauthenticated |
| **Preconditions** | No active login session |
| **Steps** | 1. Send any API request (e.g. `GET /api/members/`) without an authenticated session. |
| **Expected Result** | The API returns `401 Unauthorized`. No data is exposed. |

---

### UAT-ACL-002: Superuser-only API actions rejected for Admin role

| Field | Detail |
|---|---|
| **Role** | Admin (non-Superuser) |
| **Preconditions** | User is logged in as a regular Admin |
| **Steps** | 1. Attempt to call `DELETE /api/members/<id>` as a regular Admin. <br>2. Attempt to call `DELETE /api/groups/<id>` as a regular Admin. <br>3. Attempt to call `POST /api/events/<id>/archive` as a regular Admin. |
| **Expected Result** | All three requests are rejected with a `403 Forbidden` response. The data is not modified. |

---

### UAT-ACL-003: Member self-login is not supported

| Field | Detail |
|---|---|
| **Role** | N/A |
| **Preconditions** | A member record exists in the system |
| **Steps** | 1. Attempt to log in using a member's name or any member-related credential. |
| **Expected Result** | There is no login mechanism for members. Members do not have login accounts. Only Admin users can log in. |

---

### UAT-ACL-004: Passwords are not stored in plain text

| Field | Detail |
|---|---|
| **Role** | Superuser (database verification) |
| **Preconditions** | At least one admin account exists |
| **Steps** | 1. Inspect the `users` table in the database directly. <br>2. Examine the `password_hash` column for any admin account. |
| **Expected Result** | The stored value is a cryptographic hash, not a readable plain-text password. The plain-text password cannot be recovered from the stored hash. |

---

*End of UAT document.*

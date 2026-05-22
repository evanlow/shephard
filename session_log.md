# Shepherd — Session Log

Chronological record of work sessions. Newest entries at the bottom.
Run command: `.\Scripts\python.exe tests/run_all_smoke.py`

---

## Entry Template

```
---
Date: YYYY-MM-DD
Session ID: <brief label>
Checkpoint type: start | test | implementation | risk | handoff
Trigger: <what caused this entry>

KPI: X/8 green
- Green: #1, #2, #3, ...
- Yellow: #N (<reason>)
- Red: none

KPI delta: <what changed since prior entry>

Actions completed:
- ...

Risks / blockers / corrective actions:
- none

Next steps:
- ...
---
```

---

## 2026-04-25 — Initial Build & Test Scaffold

---
Date: 2026-04-25
Session ID: initial-build
Checkpoint type: handoff
Trigger: Project scaffolded across multiple prior sessions; smoke suite created and verified today.

KPI: 8/8 green
- Green: #1 (compliance tracked), #2 (venv verified — existing venv used, not recreated),
         #3 (baseline confirmed: 112/112 passed, 0 warnings),
         #4 (post-change tests clean: 112/112 passed, 0 warnings),
         #5 (no UI changes this session — N/A, counted green),
         #6 (no form input changes this session — N/A, counted green),
         #7 (no anomalies detected),
         #8 (compliance recorded here)
- Yellow: none
- Red: none

KPI delta: First entry — no prior state.

Actions completed:
- Scaffolded full Flask project (factory pattern, blueprints, SQLAlchemy, Flask-Login)
- Models: User, Member, Group, Event, Attendance
- Services: MemberService, GroupService, EventService, AttendanceService
- Routes: auth (login/logout/dashboard/user management), members, groups, events, attendance
- flask create-admin CLI command (creates superuser)
- @superuser_required decorator; 403 handler + template
- Templates: login.html, dashboard.html, users.html, user_form.html, 403.html
- ADMIN_GUIDE.md created
- prime_directive.md reviewed — all principles upheld
- Smoke test suite created:
    tests/smoke_auth.py             (19 tests)
    tests/smoke_members.py          (10 tests)
    tests/smoke_groups.py           (11 tests)
    tests/smoke_events.py           (13 tests)
    tests/smoke_attendance.py       (14 tests)
    tests/smoke_member_service.py   (10 tests)
    tests/smoke_group_service.py    (13 tests)
    tests/smoke_event_service.py    (10 tests)
    tests/smoke_attendance_service.py (12 tests)
    tests/run_all_smoke.py          (runner)
- Suite result: 112/112 passed, 0 warnings [PASS]

Risks / blockers / corrective actions:
- user_form.html was missing (referenced in routes but never created);
  created and verified via test_new_user_form_loads [RESOLVED]

Next steps:
- Consider Flask-Migrate for schema migrations before first production deploy
- Manual UI smoke test before any HTML/CSS/JS changes (Principle 5)
- API testing with actual HTTP client (Postman / httpie) to validate JSON contracts
---

## 2026-05-22 — Attendance Page Enhancements Review & Test Gap Remediation

---
Date: 2026-05-22
Session ID: attendance-enhancements-review
Checkpoint type: implementation
Trigger: Pulled remote changes (d47afe2..cb44abb); reviewed new enhancements and
         remediated identified test and documentation gaps.

KPI: 8/8 green
- Green: #1 (compliance tracked live), #2 (venv verified — existing venv used,
         path confirmed as shepherd\venv\Scripts\python.exe),
         #3 (baseline confirmed: 316/316 passed, 0 warnings before changes),
         #4 (post-change tests clean: see next checkpoint entry),
         #5 (no direct HTML/CSS changes in this session — gaps remediated via
             server-side test assertions; N/A, counted green),
         #6 (no new form inputs added this session — N/A, counted green),
         #7 (no anomalies detected),
         #8 (compliance recorded here)
- Yellow: none
- Red: none

KPI delta: First entry for this session; baseline from prior session was 316/316.

Actions completed:
- Pulled 4 changed files from origin/main (d47afe2..cb44abb):
    app/services/attendance_service.py  — joined_at + deactivated_at eligibility
                                          filters; attendance_id in present_members
    app/templates/ui/attendance.html    — AJAX mark/undo, live counters, search/filter,
                                          walk-in quick-add, 5-second polling
    tests/smoke_attendance.py           — +12 lines (event_status tests)
    tests/smoke_ui.py                   — +28 lines (counter IDs, data-attrs, quick-add)
- Confirmed baseline: 316/316 passed, 0 warnings [PASS]
- Assessed test coverage and documentation — identified 3 gaps:
    (a) deactivated_at filter not covered at service level
    (b) quick-add invalid event (404) not tested
    (c) data-present attribute not asserted in data-attrs test
- Remediated all gaps:
    tests/smoke_attendance_service.py   — added test_get_event_status_excludes_
                                          member_deactivated_before_event,
                                          test_get_event_status_includes_member_
                                          deactivated_after_event
    tests/smoke_ui.py                   — added test_quick_add_invalid_event_returns_404;
                                          added data-present assertion to
                                          test_attendance_page_has_member_row_data_attributes
- Added docstrings to all 5 AttendanceService methods (get_all, record,
  get_event_status, update, delete)
- Updated shepherd_specification.md §16.2 and §16.3 to reflect implemented
  features (AJAX, counters, filter, walk-in quick-add, polling) and distinguish
  from not-yet-implemented items

Risks / blockers / corrective actions:
- Client-side JS features (search, filter, polling, auto-refresh status) are not
  smoke-testable at server level — expected and acceptable gap; noted in assessment.

Next steps:
- Manual UI smoke test of attendance page enhancements (Principle 5)
---

---
Date: 2026-05-22
Session ID: attendance-enhancements-review
Checkpoint type: test
Trigger: Post-change regression suite run after gap remediation.

KPI: 8/8 green
- Green: #1, #2, #3, #4 (post-change: 319/319 passed, 0 warnings), #5, #6, #7, #8
- Yellow: none
- Red: none

KPI delta: Test count 316 -> 319 (+3 new tests all passing).

Actions completed:
- Full regression suite passed: 319/319, 0 failures, 0 warnings [PASS]
- New tests confirmed passing:
    smoke_attendance_service: test_get_event_status_excludes_member_deactivated_before_event
    smoke_attendance_service: test_get_event_status_includes_member_deactivated_after_event
    smoke_ui: test_quick_add_invalid_event_returns_404

Risks / blockers / corrective actions:
- none

Next steps:
- Manual UI smoke test of attendance page enhancements (Principle 5)
- Commit remediation changes to feature branch before merging
---

## 2026-05-23 — Pull Latest Merged Code

---
Date: 2026-05-23
Session ID: pull-latest-merged
Checkpoint type: handoff
Trigger: New code (PR #16 — purge events feature) merged into main; user requested git pull.

KPI: 8/8 green
- Green: #1, #2, #3 (pre-pull: 319/319; post-pull: 323/323, 0 warnings),
         #4, #5, #6, #7, #8
- Yellow: none
- Red: none

KPI delta: Test count 319 -> 323 (+4 tests from pulled PR; all pass).

Actions completed:
- Pre-pull baseline confirmed: 319/319 passed, 0 warnings [PASS]
- git pull cb44abb..df53188 (fast-forward, 3 files changed, +64 lines net)
- Files pulled:
    app/routes/auth.py            (+14 lines) — new purge_events() route
    app/templates/auth/purge.html (+15 lines) — "Clear All Events" purge card
    tests/smoke_auth.py           (+35 lines) — 4 new tests for purge_events
- Post-pull regression: 323/323 passed, 0 warnings [PASS]
- New tests all passing:
    smoke_auth: test_purge_events_deletes_all_events
    smoke_auth: test_purge_events_also_deletes_attendance
    smoke_auth: test_purge_events_preserves_members_and_groups
    smoke_auth: test_purge_events_wrong_confirm_redirects_with_error

Risks / blockers / corrective actions:
- none

Next steps:
- Manual UI smoke test of new "Clear All Events" purge card (Principle 5)
- Manual UI smoke test of attendance page enhancements from prior session (Principle 5)
---

## 2026-05-23 — Bugfix: Restore Imports 0 Attendance after Google Sheets Round-Trip

---
Date: 2026-05-23
Session ID: fix-restore-attendance-float-row-index
Checkpoint type: implementation
Trigger: User reported "0 attendance records imported" during admin restore even though
         backup spreadsheet contained attendance data.

KPI: 8/8 green
- Green: #1, #2, #3 (pre-change: 323/323), #4 (post-change: 324/324, 0 warnings),
         #5, #6, #7, #8
- Yellow: none
- Red: none

KPI delta: Test count 323 -> 324 (+1 regression test; all pass).

Root cause:
- app/routes/auth.py restore loop used isinstance(num_val, int) at column A to detect
  attendance rows. When the backup xlsx is opened/re-saved by Google Sheets or Excel,
  integer cells come back as floats, so the guard failed on row 7 and the loop exited
  before importing any attendance.

Actions completed:
- Fixed: accept (int, float) excluding bool as a valid row index
- Added regression test: test_restore_imports_attendance_when_row_index_is_float
  (rewrites column A of every event sheet as float, then asserts restore still works)
- Post-change regression: 324/324 passed, 0 warnings [PASS]

Risks / blockers / corrective actions:
- none

Next steps:
- Commit on feature branch and push
- Manual UI smoke test by re-uploading a Google Sheets-roundtripped backup file
---

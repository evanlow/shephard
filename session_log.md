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

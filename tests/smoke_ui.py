"""Smoke tests for app/routes/ui.py

Covers: auth guards for all UI routes, basic page loads, and key form
submissions for members, groups, events, attendance, and reports.
"""

import sys
import os
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.event import Event
from app.models.group import Group
from app.models.member import Member
from app.models.user import User


def _make_app():
    return create_app("testing")


def _create_superuser(username="admin", email="admin@test.com", password="password123"):
    user = User(username=username, email=email, is_superuser=True, is_admin=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username="admin", password="password123"):
    client.post("/login", data={"username": username, "password": password})


# ---------------------------------------------------------------------------
# Auth guards — every UI route must redirect unauthenticated users to /login
# ---------------------------------------------------------------------------

class TestUIAuthGuards(unittest.TestCase):
    GUARDED_PATHS = [
        "/members",
        "/groups",
        "/events",
        "/reports",
    ]

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_unauthenticated_redirected_to_login(self):
        for path in self.GUARDED_PATHS:
            with self.subTest(path=path):
                resp = self.client.get(path)
                self.assertEqual(resp.status_code, 302, f"Expected redirect for {path}")
                self.assertIn("/login", resp.headers["Location"])


# ---------------------------------------------------------------------------
# Members UI
# ---------------------------------------------------------------------------

class TestMembersUI(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        _create_superuser()
        self.client = self.app.test_client()
        _login(self.client)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_members_page_loads(self):
        resp = self.client.get("/members")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Members", resp.data)

    def test_create_member_redirects(self):
        resp = self.client.post("/members", data={"name": "Alice Smith"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/members", resp.headers["Location"])
        member = db.session.execute(
            db.select(Member).where(Member.name == "Alice Smith")
        ).scalar_one_or_none()
        self.assertIsNotNone(member)

    def test_create_member_empty_name_redirects_with_flash(self):
        resp = self.client.post("/members", data={"name": ""}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"required", resp.data)

    def test_create_member_with_group(self):
        group = Group(name="Worship")
        db.session.add(group)
        db.session.commit()
        resp = self.client.post(
            "/members", data={"name": "Bob Jones", "group_id": str(group.id)}
        )
        self.assertEqual(resp.status_code, 302)
        member = db.session.execute(
            db.select(Member).where(Member.name == "Bob Jones")
        ).scalar_one_or_none()
        self.assertIsNotNone(member)
        self.assertEqual(member.group_id, group.id)

    def test_edit_member_form_loads(self):
        member = Member(name="Carol White")
        db.session.add(member)
        db.session.commit()
        resp = self.client.get(f"/members/{member.id}/edit")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Carol White", resp.data)

    def test_edit_member_form_not_found(self):
        resp = self.client.get("/members/9999/edit")
        self.assertEqual(resp.status_code, 302)

    def test_update_member_redirects(self):
        member = Member(name="Dave Green")
        db.session.add(member)
        db.session.commit()
        resp = self.client.post(
            f"/members/{member.id}/edit",
            data={"name": "Dave Black", "group_id": "0"},
        )
        self.assertEqual(resp.status_code, 302)
        db.session.refresh(member)
        self.assertEqual(member.name, "Dave Black")

    def test_create_member_invalid_group_id_string_falls_back(self):
        resp = self.client.post(
            "/members",
            data={"name": "Invalid Group Id", "group_id": "not-a-number"},
        )
        self.assertEqual(resp.status_code, 302)

    def test_create_member_error_flash_for_missing_group(self):
        resp = self.client.post(
            "/members",
            data={"name": "Bad Group", "group_id": "999999"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"not found", resp.data)

    def test_update_member_not_found_redirects(self):
        resp = self.client.post(
            "/members/999999/edit",
            data={"name": "Nobody", "group_id": "0"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Member not found", resp.data)

    def test_update_member_invalid_group_redirects_back_to_edit(self):
        member = Member(name="Needs Valid Group")
        db.session.add(member)
        db.session.commit()
        resp = self.client.post(
            f"/members/{member.id}/edit",
            data={"name": "Needs Valid Group", "group_ids": ["999999"]},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/members/{member.id}/edit", resp.headers["Location"])

    def test_delete_member_not_found_redirects(self):
        resp = self.client.post("/members/999999/delete", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Member not found", resp.data)

    def test_delete_member_redirects(self):
        member = Member(name="Eve Brown")
        db.session.add(member)
        db.session.commit()
        mid = member.id
        resp = self.client.post(f"/members/{mid}/delete")
        self.assertEqual(resp.status_code, 302)
        self.assertIsNone(db.session.get(Member, mid))


# ---------------------------------------------------------------------------
# Groups UI
# ---------------------------------------------------------------------------

class TestGroupsUI(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        _create_superuser()
        self.client = self.app.test_client()
        _login(self.client)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_groups_page_loads(self):
        resp = self.client.get("/groups")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Groups", resp.data)

    def test_create_group_redirects(self):
        resp = self.client.post("/groups", data={"name": "Sunday School"})
        self.assertEqual(resp.status_code, 302)
        group = db.session.execute(
            db.select(Group).where(Group.name == "Sunday School")
        ).scalar_one_or_none()
        self.assertIsNotNone(group)

    def test_create_group_empty_name_redirects_with_flash(self):
        resp = self.client.post("/groups", data={"name": ""}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"required", resp.data)

    def test_create_group_duplicate_name_redirects_with_flash(self):
        db.session.add(Group(name="Dupe Group"))
        db.session.commit()
        resp = self.client.post("/groups", data={"name": "Dupe Group"}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"already exists", resp.data)

    def test_edit_group_form_loads(self):
        group = Group(name="Youth")
        db.session.add(group)
        db.session.commit()
        resp = self.client.get(f"/groups/{group.id}/edit")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Youth", resp.data)

    def test_edit_group_form_not_found_redirects(self):
        resp = self.client.get("/groups/999999/edit", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Group not found", resp.data)

    def test_update_group_redirects(self):
        group = Group(name="Old Name")
        db.session.add(group)
        db.session.commit()
        resp = self.client.post(
            f"/groups/{group.id}/edit", data={"name": "New Name", "description": ""}
        )
        self.assertEqual(resp.status_code, 302)
        db.session.refresh(group)
        self.assertEqual(group.name, "New Name")

    def test_update_all_members_group_rename_blocked(self):
        default_group = db.session.execute(
            db.select(Group).where(Group.name == "ALL MEMBERS")
        ).scalar_one()
        resp = self.client.post(
            f"/groups/{default_group.id}/edit",
            data={"name": "Blocked Rename", "description": ""},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"cannot be renamed", resp.data)

    def test_update_group_missing_name_redirects_with_flash(self):
        group = Group(name="Needs Name")
        db.session.add(group)
        db.session.commit()
        resp = self.client.post(
            f"/groups/{group.id}/edit",
            data={"name": "", "description": "desc"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"required", resp.data)

    def test_update_group_not_found_redirects_with_flash(self):
        resp = self.client.post(
            "/groups/999999/edit",
            data={"name": "Ghost", "description": ""},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Group not found", resp.data)

    def test_delete_group_unassigns_members(self):
        group = Group(name="To Delete")
        db.session.add(group)
        db.session.commit()
        member = Member(name="Assigned", group_id=group.id)
        db.session.add(member)
        db.session.commit()
        gid = group.id
        mid = member.id
        default_group = db.session.execute(
            db.select(Group).where(Group.name == "ALL MEMBERS")
        ).scalar_one()

        resp = self.client.post(f"/groups/{gid}/delete")
        self.assertEqual(resp.status_code, 302)
        self.assertIsNone(db.session.get(Group, gid))
        remaining = db.session.get(Member, mid)
        self.assertIsNotNone(remaining)
        self.assertEqual(remaining.group_id, default_group.id)

    def test_delete_group_not_found_redirects_with_flash(self):
        resp = self.client.post("/groups/999999/delete", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Group not found", resp.data)


# ---------------------------------------------------------------------------
# Events UI
# ---------------------------------------------------------------------------

class TestEventsUI(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        _create_superuser()
        self.group = Group(name="Worship")
        db.session.add(self.group)
        db.session.commit()
        self.client = self.app.test_client()
        _login(self.client)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_events_page_loads(self):
        resp = self.client.get("/events")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Events", resp.data)

    def test_create_event_redirects(self):
        resp = self.client.post("/events", data={
            "name": "Worship Service",
            "date": "2026-05-03T08:00",
            "group_id": str(self.group.id),
        })
        self.assertEqual(resp.status_code, 302)
        event = db.session.execute(
            db.select(Event).where(Event.name == "Worship Service")
        ).scalar_one_or_none()
        self.assertIsNotNone(event)

    def test_create_event_missing_name_redirects_with_flash(self):
        resp = self.client.post("/events", data={
            "name": "",
            "date": "2026-05-03T08:00",
            "group_id": str(self.group.id),
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"required", resp.data)

    def test_create_event_missing_group_redirects_with_flash(self):
        resp = self.client.post("/events", data={
            "name": "No Group Event",
            "date": "2026-05-03T08:00",
            "group_id": "",
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"required", resp.data)

    def test_create_event_missing_date_redirects_with_flash(self):
        resp = self.client.post(
            "/events",
            data={"name": "No Date", "date": "", "group_id": str(self.group.id)},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Date and time are required", resp.data)

    def test_create_event_invalid_date_redirects_with_flash(self):
        resp = self.client.post(
            "/events",
            data={
                "name": "Bad Date",
                "date": "not-a-date",
                "group_id": str(self.group.id),
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Invalid date/time format", resp.data)

    def test_create_event_unknown_group_redirects_with_flash(self):
        resp = self.client.post(
            "/events",
            data={
                "name": "Unknown Group Event",
                "date": "2026-05-03T08:00",
                "group_id": "999999",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"not found", resp.data)

    def test_delete_event_redirects(self):
        event = Event(name="To Delete", date=datetime.now(timezone.utc), group_id=self.group.id)
        db.session.add(event)
        db.session.commit()
        eid = event.id
        resp = self.client.post(f"/events/{eid}/delete")
        self.assertEqual(resp.status_code, 302)
        self.assertIsNone(db.session.get(Event, eid))

    def test_delete_event_not_found_redirects_with_flash(self):
        resp = self.client.post("/events/999999/delete", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Event not found", resp.data)


# ---------------------------------------------------------------------------
# Attendance UI
# ---------------------------------------------------------------------------

class TestAttendanceUI(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        _create_superuser()
        self.group = Group(name="Worship")
        db.session.add(self.group)
        db.session.commit()
        self.member = Member(name="Alice", group_id=self.group.id)
        db.session.add(self.member)
        db.session.commit()
        self.event = Event(
            name="Sunday Service",
            date=datetime.now(timezone.utc),
            group_id=self.group.id,
        )
        db.session.add(self.event)
        db.session.commit()
        self.client = self.app.test_client()
        _login(self.client)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_attendance_page_loads(self):
        resp = self.client.get(f"/events/{self.event.id}/attendance")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sunday Service", resp.data)
        self.assertIn(b"Alice", resp.data)

    def test_attendance_page_not_found_redirects(self):
        resp = self.client.get("/events/9999/attendance")
        self.assertEqual(resp.status_code, 302)

    def test_mark_present_redirects(self):
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/mark",
            data={"member_id": str(self.member.id)},
        )
        self.assertEqual(resp.status_code, 302)

    def test_mark_absent_no_record_still_redirects(self):
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/unmark",
            data={"member_id": str(self.member.id)},
        )
        self.assertEqual(resp.status_code, 302)

    def test_mark_present_missing_member_id_redirects_with_flash(self):
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/mark",
            data={},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Member ID is required", resp.data)

    def test_mark_absent_missing_member_id_redirects_with_flash(self):
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/unmark",
            data={},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Member ID is required", resp.data)

    def test_mark_present_creates_record(self):
        from app.models.attendance import Attendance
        self.client.post(
            f"/events/{self.event.id}/attendance/mark",
            data={"member_id": str(self.member.id)},
        )
        rec = db.session.execute(
            db.select(Attendance).where(
                Attendance.event_id == self.event.id,
                Attendance.member_id == self.member.id,
            )
        ).scalar_one_or_none()
        self.assertIsNotNone(rec)
        self.assertTrue(rec.present)

    def test_mark_present_then_absent(self):
        from app.models.attendance import Attendance
        self.client.post(
            f"/events/{self.event.id}/attendance/mark",
            data={"member_id": str(self.member.id)},
        )
        self.client.post(
            f"/events/{self.event.id}/attendance/unmark",
            data={"member_id": str(self.member.id)},
        )
        rec = db.session.execute(
            db.select(Attendance).where(
                Attendance.event_id == self.event.id,
                Attendance.member_id == self.member.id,
            )
        ).scalar_one_or_none()
        self.assertIsNotNone(rec)
        self.assertFalse(rec.present)

    def test_mark_present_idempotent(self):
        """Marking present twice should not raise an error."""
        from app.models.attendance import Attendance
        self.client.post(
            f"/events/{self.event.id}/attendance/mark",
            data={"member_id": str(self.member.id)},
        )
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/mark",
            data={"member_id": str(self.member.id)},
        )
        self.assertEqual(resp.status_code, 302)

    def test_mark_present_error_is_flashed_for_ineligible_member(self):
        outsider_group = Group(name="Outsiders")
        db.session.add(outsider_group)
        db.session.commit()
        outsider = Member(name="Outsider", group_id=outsider_group.id)
        db.session.add(outsider)
        db.session.commit()

        resp = self.client.post(
            f"/events/{self.event.id}/attendance/mark",
            data={"member_id": str(outsider.id)},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"not assigned to this event", resp.data)

    def test_all_members_event_includes_cross_group_memberships(self):
        """ALL MEMBERS event should include members linked through memberships, not only primary group_id."""
        all_members_group = db.session.execute(
            db.select(Group).where(Group.name == "ALL MEMBERS")
        ).scalar_one()
        choir = Group(name="Choir")
        db.session.add(choir)
        db.session.commit()

        # Primary group is Choir, but this member is also in ALL MEMBERS.
        cross_group_member = Member(name="Cross Group", group_id=choir.id)
        cross_group_member.groups.append(all_members_group)
        db.session.add(cross_group_member)
        db.session.commit()

        all_members_event = Event(
            name="All Members Service",
            date=datetime.now(timezone.utc),
            group_id=all_members_group.id,
        )
        db.session.add(all_members_event)
        db.session.commit()

        resp = self.client.get(f"/events/{all_members_event.id}/attendance")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Cross Group", resp.data)


# ---------------------------------------------------------------------------
# Reports UI
# ---------------------------------------------------------------------------

class TestReportsUI(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        _create_superuser()
        self.group = Group(name="Worship")
        db.session.add(self.group)
        db.session.commit()
        self.event = Event(
            name="Sunday Service",
            date=datetime.now(timezone.utc),
            group_id=self.group.id,
        )
        db.session.add(self.event)
        db.session.commit()
        self.client = self.app.test_client()
        _login(self.client)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_reports_page_loads(self):
        resp = self.client.get("/reports")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Reports", resp.data)

    def test_reports_page_with_event_id(self):
        resp = self.client.get(f"/reports?event_id={self.event.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sunday Service", resp.data)

    def test_reports_page_invalid_event_id(self):
        resp = self.client.get("/reports?event_id=9999")
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Dashboard shows summary data
# ---------------------------------------------------------------------------

class TestDashboardSummary(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        _create_superuser()
        self.client = self.app.test_client()
        _login(self.client)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_dashboard_shows_nav_links(self):
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Members", resp.data)
        self.assertIn(b"Groups", resp.data)
        self.assertIn(b"Events", resp.data)
        self.assertIn(b"Reports", resp.data)

    def test_dashboard_shows_summary_counts(self):
        group = Group(name="Choir")
        db.session.add(group)
        db.session.commit()
        member = Member(name="Test User", group_id=group.id)
        db.session.add(member)
        db.session.commit()
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        # Should contain the count values somewhere
        self.assertIn(b"1", resp.data)


if __name__ == "__main__":
    unittest.main()

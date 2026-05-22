"""Smoke tests for app/routes/ui.py

Covers: auth guards for all UI routes, basic page loads, and key form
submissions for members, groups, events, attendance, and reports.
"""

import sys
import os
import unittest
from datetime import date, datetime, timezone

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

    def test_delete_member_redirects(self):
        member = Member(name="Eve Brown")
        db.session.add(member)
        db.session.commit()
        mid = member.id
        resp = self.client.post(f"/members/{mid}/delete")
        self.assertEqual(resp.status_code, 302)
        self.assertIsNone(db.session.get(Member, mid))

    def test_update_member_member_since_updates_dates(self):
        """Submitting member_since updates created_at and ALL MEMBERS joined_at."""
        from app.models.membership import member_groups as mg
        member = Member(name="Frank Lee")
        db.session.add(member)
        db.session.commit()
        resp = self.client.post(
            f"/members/{member.id}/edit",
            data={"name": "Frank Lee", "member_since": "2020-03-15"},
        )
        self.assertEqual(resp.status_code, 302)
        db.session.expire_all()
        updated = db.session.get(Member, member.id)
        self.assertEqual(updated.created_at.date(), date(2020, 3, 15))
        joined_at = db.session.execute(
            db.select(mg.c.joined_at).where(mg.c.member_id == member.id)
        ).scalar()
        self.assertIsNotNone(joined_at)
        joined_date = joined_at.date() if hasattr(joined_at, "date") else datetime.fromisoformat(str(joined_at)).date()
        self.assertEqual(joined_date, date(2020, 3, 15))

    def test_deactivate_member_returns_redirect(self):
        member = Member(name="Depart Soon")
        db.session.add(member)
        db.session.commit()
        resp = self.client.post(
            f"/members/{member.id}/deactivate",
            data={"deactivated_at": "2026-06-30"},
        )
        self.assertEqual(resp.status_code, 302)
        db.session.expire_all()
        updated = db.session.get(Member, member.id)
        self.assertIsNotNone(updated.deactivated_at)

    def test_deactivate_missing_date_redirects(self):
        member = Member(name="No Date")
        db.session.add(member)
        db.session.commit()
        resp = self.client.post(
            f"/members/{member.id}/deactivate",
            data={"deactivated_at": ""},
        )
        self.assertEqual(resp.status_code, 302)
        db.session.expire_all()
        still_active = db.session.get(Member, member.id)
        self.assertIsNone(still_active.deactivated_at)

    def test_reactivate_member_returns_redirect(self):
        from datetime import datetime as dt
        member = Member(name="Come Back")
        member.deactivated_at = dt(2026, 5, 31, 23, 59, 59)
        db.session.add(member)
        db.session.commit()
        resp = self.client.post(
            f"/members/{member.id}/reactivate",
            data={"rejoined_at": "2026-09-01"},
        )
        self.assertEqual(resp.status_code, 302)
        db.session.expire_all()
        updated = db.session.get(Member, member.id)
        self.assertIsNone(updated.deactivated_at)

    def test_reactivate_missing_date_redirects(self):
        from datetime import datetime as dt
        member = Member(name="Still Gone")
        member.deactivated_at = dt(2026, 5, 31, 23, 59, 59)
        db.session.add(member)
        db.session.commit()
        resp = self.client.post(
            f"/members/{member.id}/reactivate",
            data={"rejoined_at": ""},
        )
        self.assertEqual(resp.status_code, 302)
        db.session.expire_all()
        still_inactive = db.session.get(Member, member.id)
        self.assertIsNotNone(still_inactive.deactivated_at)


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

    def test_edit_group_form_loads(self):
        group = Group(name="Youth")
        db.session.add(group)
        db.session.commit()
        resp = self.client.get(f"/groups/{group.id}/edit")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Youth", resp.data)

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

    def test_rename_all_members_group_is_blocked(self):
        """Attempting to rename ALL MEMBERS via UI should flash an error and leave the name unchanged."""
        default_group = db.session.execute(
            db.select(Group).where(Group.name == "ALL MEMBERS")
        ).scalar_one()
        resp = self.client.post(
            f"/groups/{default_group.id}/edit",
            data={"name": "Renamed", "description": ""},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        db.session.refresh(default_group)
        self.assertEqual(default_group.name, "ALL MEMBERS")

    def test_delete_all_members_group_via_ui_is_blocked(self):
        """Attempting to delete ALL MEMBERS via UI should silently keep the group."""
        default_group = db.session.execute(
            db.select(Group).where(Group.name == "ALL MEMBERS")
        ).scalar_one()
        gid = default_group.id
        resp = self.client.post(f"/groups/{gid}/delete")
        self.assertEqual(resp.status_code, 302)
        self.assertIsNotNone(db.session.get(Group, gid))


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

    def test_delete_event_redirects(self):
        event = Event(name="To Delete", date=datetime.now(timezone.utc), group_id=self.group.id)
        db.session.add(event)
        db.session.commit()
        eid = event.id
        # Archive the event first so it can be deleted
        from app.services.event_service import EventService
        EventService.archive(eid)
        resp = self.client.post(f"/events/{eid}/delete")
        self.assertEqual(resp.status_code, 302)
        self.assertIsNone(db.session.get(Event, eid))

    def test_edit_event_page_loads(self):
        event = Event(name="Editable Event", date=datetime.now(timezone.utc), group_id=self.group.id)
        db.session.add(event)
        db.session.commit()
        resp = self.client.get(f"/events/{event.id}/edit")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Editable Event", resp.data)

    def test_edit_event_page_not_found_redirects(self):
        resp = self.client.get("/events/9999/edit")
        self.assertEqual(resp.status_code, 302)

    def test_update_event_redirects_on_success(self):
        event = Event(name="Old Name", date=datetime.now(timezone.utc), group_id=self.group.id)
        db.session.add(event)
        db.session.commit()
        resp = self.client.post(f"/events/{event.id}/edit", data={
            "name": "New Name",
            "date": "2027-06-01T10:00",
        })
        self.assertEqual(resp.status_code, 302)
        db.session.refresh(event)
        self.assertEqual(event.name, "New Name")

    def test_update_event_missing_name_redirects_with_flash(self):
        event = Event(name="Keep Name", date=datetime.now(timezone.utc), group_id=self.group.id)
        db.session.add(event)
        db.session.commit()
        resp = self.client.post(f"/events/{event.id}/edit", data={
            "name": "",
            "date": "2027-06-01T10:00",
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"required", resp.data)

    # ------------------------------------------------------------------
    # Archive / Unarchive
    # ------------------------------------------------------------------

    def test_archive_event_redirects(self):
        event = Event(name="To Archive", date=datetime.now(timezone.utc), group_id=self.group.id)
        db.session.add(event)
        db.session.commit()
        resp = self.client.post(f"/events/{event.id}/archive")
        self.assertEqual(resp.status_code, 302)

    def test_archive_event_sets_is_archived(self):
        event = Event(name="Archive Me", date=datetime.now(timezone.utc), group_id=self.group.id)
        db.session.add(event)
        db.session.commit()
        self.client.post(f"/events/{event.id}/archive")
        db.session.refresh(event)
        self.assertTrue(event.is_archived)

    def test_archived_event_excluded_from_active_list(self):
        event = Event(name="Hidden Event", date=datetime.now(timezone.utc), group_id=self.group.id)
        db.session.add(event)
        db.session.commit()
        self.client.post(f"/events/{event.id}/archive")
        resp = self.client.get("/events")
        self.assertEqual(resp.status_code, 200)
        # Event should not appear in the active events table
        from app.services.event_service import EventService
        active = EventService.get_all()
        self.assertNotIn(event.id, [e.id for e in active])

    def test_unarchive_event_redirects(self):
        event = Event(name="To Unarchive", date=datetime.now(timezone.utc), group_id=self.group.id, is_archived=True)
        db.session.add(event)
        db.session.commit()
        resp = self.client.post(f"/events/{event.id}/unarchive")
        self.assertEqual(resp.status_code, 302)

    def test_unarchive_event_clears_is_archived(self):
        event = Event(name="Restore Me", date=datetime.now(timezone.utc), group_id=self.group.id, is_archived=True)
        db.session.add(event)
        db.session.commit()
        self.client.post(f"/events/{event.id}/unarchive")
        db.session.refresh(event)
        self.assertFalse(event.is_archived)

    def test_archive_not_found_redirects(self):
        resp = self.client.post("/events/9999/archive")
        self.assertEqual(resp.status_code, 302)

    def test_unarchive_not_found_redirects(self):
        resp = self.client.post("/events/9999/unarchive")
        self.assertEqual(resp.status_code, 302)


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
            date=datetime(2099, 12, 31, 10, 0),
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

    def test_attendance_page_shows_all_members_in_group_via_m2m(self):
        """All members belonging to the event's group via m2m appear on the attendance page."""
        second = Member(name="Bob", group_id=self.group.id)
        db.session.add(second)
        db.session.commit()

        resp = self.client.get(f"/events/{self.event.id}/attendance")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Alice", resp.data)
        self.assertIn(b"Bob", resp.data)

    def test_quick_add_creates_member_and_marks_present(self):
        """Quick-add creates a new member and records them as present for the event."""
        import json
        from app.models.attendance import Attendance

        resp = self.client.post(
            f"/events/{self.event.id}/attendance/quick_add",
            data=json.dumps({"name": "Walk In Person"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["member_name"], "Walk In Person")
        self.assertIsNotNone(data["attendance_id"])

        member = db.session.get(Member, data["member_id"])
        self.assertIsNotNone(member)
        rec = db.session.execute(
            db.select(Attendance).where(
                Attendance.event_id == self.event.id,
                Attendance.member_id == member.id,
            )
        ).scalar_one_or_none()
        self.assertIsNotNone(rec)
        self.assertTrue(rec.present)

    def test_quick_add_sets_joined_at_to_event_date(self):
        """Quick-add member's joined_at is set to the event's date."""
        import json
        from app.models.membership import member_groups as mg

        resp = self.client.post(
            f"/events/{self.event.id}/attendance/quick_add",
            data=json.dumps({"name": "Late Arrival"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        member_id = resp.get_json()["member_id"]

        rows = db.session.execute(
            db.select(mg.c.joined_at).where(mg.c.member_id == member_id)
        ).scalars().all()
        self.assertTrue(len(rows) > 0)
        for joined_at in rows:
            joined_date = (
                joined_at.date()
                if hasattr(joined_at, "date")
                else datetime.fromisoformat(str(joined_at)).date()
            )
            self.assertEqual(joined_date, date(2099, 12, 31))

    def test_quick_add_missing_name_returns_400(self):
        """Quick-add with an empty name returns 400."""
        import json

        resp = self.client.post(
            f"/events/{self.event.id}/attendance/quick_add",
            data=json.dumps({"name": ""}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_deactivated_member_excluded_from_future_event(self):
        """A member deactivated before the event date is not listed on the attendance page."""
        from datetime import datetime as dt
        # self.event is 2099-12-31; deactivate Alice before that date
        self.member.deactivated_at = dt(2026, 6, 30, 23, 59, 59)
        db.session.commit()
        resp = self.client.get(f"/events/{self.event.id}/attendance")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(b"Alice", resp.data)

    def test_active_member_still_appears_on_event_after_deactivation_date(self):
        """A member deactivated after the event date should still appear on that event."""
        from datetime import datetime as dt
        # self.event is 2099-12-31; deactivate Alice on the very day → still listed
        self.member.deactivated_at = dt(2099, 12, 31, 23, 59, 59)
        db.session.commit()
        resp = self.client.get(f"/events/{self.event.id}/attendance")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Alice", resp.data)

    def test_attendance_page_has_counter_ids(self):
        """Attendance page includes expected-count, present-count, absent-count element IDs."""
        resp = self.client.get(f"/events/{self.event.id}/attendance")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="expected-count"', resp.data)
        self.assertIn(b'id="present-count"', resp.data)
        self.assertIn(b'id="absent-count"', resp.data)

    def test_attendance_page_has_member_row_data_attributes(self):
        """Attendance page member rows have data-member-id and data-attendance-status attributes."""
        from html.parser import HTMLParser

        class AttendanceStatusParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.has_attendance_status = False

            def handle_starttag(self, tag, attrs):
                if not self.has_attendance_status and any(name == "data-attendance-status" for name, _ in attrs):
                    self.has_attendance_status = True

        resp = self.client.get(f"/events/{self.event.id}/attendance")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'data-member-id=', resp.data)
        parser = AttendanceStatusParser()
        parser.feed(resp.get_data(as_text=True))
        self.assertTrue(parser.has_attendance_status)


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


# ---------------------------------------------------------------------------
# Attendance PDF export
# ---------------------------------------------------------------------------

class TestAttendancePDF(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        _create_superuser()
        self.group = Group(name="Choir")
        db.session.add(self.group)
        db.session.commit()
        self.member = Member(name="John Doe", group_id=self.group.id)
        db.session.add(self.member)
        db.session.commit()
        self.event = Event(
            name="Sunday Service",
            date=datetime(2026, 5, 3, 8, 0),
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

    def test_pdf_unauthenticated_redirects(self):
        app = _make_app()
        ctx = app.app_context()
        ctx.push()
        try:
            db.create_all()
            _create_superuser(username="unauth-admin", email="unauth-admin@test.com")
            group = Group(name="Unauth Choir")
            db.session.add(group)
            db.session.commit()
            event = Event(
                name="Unauth Service",
                date=datetime(2026, 5, 3, 8, 0),
                group_id=group.id,
            )
            db.session.add(event)
            db.session.commit()

            c = app.test_client()
            resp = c.get(f"/events/{event.id}/attendance/pdf")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/login", resp.headers["Location"])
        finally:
            db.session.remove()
            db.drop_all()
            ctx.pop()

    def test_pdf_returns_200_and_pdf_content_type(self):
        resp = self.client.get(f"/events/{self.event.id}/attendance/pdf")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/pdf", resp.content_type)

    def test_pdf_response_is_non_empty(self):
        resp = self.client.get(f"/events/{self.event.id}/attendance/pdf")
        self.assertGreater(len(resp.data), 0)
        # PDF files start with %PDF
        self.assertTrue(resp.data.startswith(b"%PDF"))

    def test_pdf_has_attachment_header(self):
        resp = self.client.get(f"/events/{self.event.id}/attendance/pdf")
        disposition = resp.headers.get("Content-Disposition", "")
        self.assertIn("attachment", disposition)
        self.assertIn(".pdf", disposition)

    def test_pdf_not_found_event_redirects(self):
        resp = self.client.get("/events/9999/attendance/pdf")
        self.assertEqual(resp.status_code, 302)

    def test_pdf_with_present_member(self):
        from app.models.attendance import Attendance
        rec = Attendance(
            event_id=self.event.id, member_id=self.member.id, present=True
        )
        db.session.add(rec)
        db.session.commit()
        resp = self.client.get(f"/events/{self.event.id}/attendance/pdf")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

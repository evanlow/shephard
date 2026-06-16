"""Smoke tests for event-level admin access control.

Covers:
- Superuser sees all events.
- Ordinary admin sees only assigned events (default-deny).
- Unassigned admin cannot access event-specific routes.
- Assigned admin can access event-specific routes.
- Ordinary admin cannot create events (superuser-only).
- Ordinary admin cannot access event edit routes.
- API list endpoint filters events by assignment.
- API get endpoint returns 403 for unassigned ordinary admin.
"""

import json
import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.event import Event
from app.models.event_admin import EventAdmin
from app.models.group import Group
from app.models.member import Member
from app.models.user import User

VALID_DATE = "2026-06-01T10:00:00"


def _make_app():
    return create_app("testing")


def _create_user(username, email, password, is_admin=False, is_superuser=False):
    user = User(username=username, email=email, is_admin=is_admin, is_superuser=is_superuser)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username, password):
    client.post("/login", data={"username": username, "password": password})


class TestSuperuserSeesAllEvents(unittest.TestCase):
    """A superuser can see and access every event without explicit assignment."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_user("su", "su@test.com", "pw", is_admin=True, is_superuser=True)
        _login(self.client, "su", "pw")

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()
        self.event = Event(name="Sunday Service", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(self.event)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_superuser_sees_event_in_api_list(self):
        resp = self.client.get("/api/events/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Sunday Service")

    def test_superuser_can_get_event_api(self):
        resp = self.client.get(f"/api/events/{self.event.id}")
        self.assertEqual(resp.status_code, 200)

    def test_superuser_sees_event_in_ui_list(self):
        resp = self.client.get("/events")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sunday Service", resp.data)

    def test_superuser_can_access_attendance_page(self):
        resp = self.client.get(f"/events/{self.event.id}/attendance")
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_create_event_api(self):
        group = db.session.execute(db.select(Group).where(Group.name == "Test Group")).scalar_one()
        resp = self.client.post(
            "/api/events/",
            data=json.dumps({"name": "New Event", "date": VALID_DATE, "group_id": group.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)


class TestUnassignedAdminDefaultDeny(unittest.TestCase):
    """An ordinary admin not assigned to an event cannot access it."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_user("admin", "admin@test.com", "pw", is_admin=True, is_superuser=False)
        _login(self.client, "admin", "pw")

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()
        self.event = Event(name="Hidden Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(self.event)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_unassigned_admin_sees_empty_list_api(self):
        resp = self.client.get("/api/events/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, [])

    def test_unassigned_admin_cannot_get_event_api(self):
        resp = self.client.get(f"/api/events/{self.event.id}")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("error", json.loads(resp.data))

    def test_unassigned_admin_sees_empty_state_in_ui(self):
        resp = self.client.get("/events")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"No events assigned", resp.data)
        self.assertNotIn(b"Hidden Event", resp.data)

    def test_unassigned_admin_cannot_access_attendance_page(self):
        resp = self.client.get(f"/events/{self.event.id}/attendance", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"not authorised", resp.data.lower())

    def test_unassigned_admin_cannot_mark_attendance(self):
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/mark",
            data={"member_id": "1"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"not authorised", resp.data.lower())

    def test_unassigned_admin_cannot_unmark_attendance(self):
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/unmark",
            data={"member_id": "1"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"not authorised", resp.data.lower())

    def test_unassigned_admin_cannot_quick_add(self):
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/quick_add",
            data=json.dumps({"name": "Walk-in"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("error", json.loads(resp.data))

    def test_unassigned_admin_cannot_create_event_api(self):
        group = db.session.execute(db.select(Group).where(Group.name == "Test Group")).scalar_one()
        resp = self.client.post(
            "/api/events/",
            data=json.dumps({"name": "New Event", "date": VALID_DATE, "group_id": group.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_unassigned_admin_cannot_edit_event_ui(self):
        resp = self.client.get(f"/events/{self.event.id}/edit")
        self.assertEqual(resp.status_code, 403)

    def test_unassigned_admin_cannot_update_event_api(self):
        resp = self.client.put(
            f"/api/events/{self.event.id}",
            data=json.dumps({"name": "Hacked Name"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


class TestAssignedAdminCanAccess(unittest.TestCase):
    """An ordinary admin explicitly assigned to an event can access it."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        self.admin = _create_user("admin", "admin@test.com", "pw", is_admin=True, is_superuser=False)
        _login(self.client, "admin", "pw")

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()

        self.event = Event(name="Assigned Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(self.event)
        db.session.flush()

        member = Member(name="Test Member", group_id=group.id)
        db.session.add(member)

        # Assign this admin to the event
        db.session.add(EventAdmin(event_id=self.event.id, user_id=self.admin.id))
        db.session.commit()
        self.member_id = member.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_assigned_admin_sees_event_in_api_list(self):
        resp = self.client.get("/api/events/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Assigned Event")

    def test_assigned_admin_can_get_event_api(self):
        resp = self.client.get(f"/api/events/{self.event.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)["name"], "Assigned Event")

    def test_assigned_admin_sees_event_in_ui_list(self):
        resp = self.client.get("/events")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Assigned Event", resp.data)

    def test_assigned_admin_can_access_attendance_page(self):
        resp = self.client.get(f"/events/{self.event.id}/attendance")
        self.assertEqual(resp.status_code, 200)

    def test_assigned_admin_can_mark_attendance(self):
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/mark",
            data={"member_id": str(self.member_id)},
        )
        self.assertEqual(resp.status_code, 302)

    def test_assigned_admin_can_unmark_attendance(self):
        resp = self.client.post(
            f"/events/{self.event.id}/attendance/unmark",
            data={"member_id": str(self.member_id)},
        )
        self.assertEqual(resp.status_code, 302)


class TestEventAdminAssignmentByService(unittest.TestCase):
    """EventService.create / update correctly manage allowed_admin_ids."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        from app.services.event_service import EventService
        self.EventService = EventService

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()
        self.group_id = group.id

        self.admin = _create_user("admin", "admin@test.com", "pw", is_admin=True, is_superuser=False)
        self.su = _create_user("su", "su@test.com", "pw", is_admin=True, is_superuser=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_create_assigns_specified_admins(self):
        event, _ = self.EventService.create(
            name="Test", date=datetime(2026, 6, 1), group_id=self.group_id,
            allowed_admin_ids=[self.admin.id],
        )
        assigned = self.EventService.get_assigned_admins(event.id)
        self.assertEqual(len(assigned), 1)
        self.assertEqual(assigned[0].id, self.admin.id)

    def test_create_does_not_assign_superuser(self):
        event, _ = self.EventService.create(
            name="Test", date=datetime(2026, 6, 1), group_id=self.group_id,
            allowed_admin_ids=[self.su.id],
        )
        assigned = self.EventService.get_assigned_admins(event.id)
        self.assertEqual(len(assigned), 0)

    def test_update_replaces_admin_assignments(self):
        admin2 = _create_user("admin2", "admin2@test.com", "pw", is_admin=True)
        event, _ = self.EventService.create(
            name="Test", date=datetime(2026, 6, 1), group_id=self.group_id,
            allowed_admin_ids=[self.admin.id],
        )
        self.EventService.update(event.id, name="Test Updated", allowed_admin_ids=[admin2.id])
        assigned_ids = {u.id for u in self.EventService.get_assigned_admins(event.id)}
        self.assertIn(admin2.id, assigned_ids)
        self.assertNotIn(self.admin.id, assigned_ids)

    def test_update_empty_list_removes_all_assignments(self):
        event, _ = self.EventService.create(
            name="Test", date=datetime(2026, 6, 1), group_id=self.group_id,
            allowed_admin_ids=[self.admin.id],
        )
        self.EventService.update(event.id, name="No Admins", allowed_admin_ids=[])
        assigned = self.EventService.get_assigned_admins(event.id)
        self.assertEqual(len(assigned), 0)

    def test_get_for_user_superuser_returns_all(self):
        self.EventService.create(name="E1", date=datetime(2026, 6, 1), group_id=self.group_id)
        self.EventService.create(name="E2", date=datetime(2026, 6, 2), group_id=self.group_id)
        events = self.EventService.get_for_user(self.su)
        self.assertEqual(len(events), 2)

    def test_get_for_user_ordinary_admin_returns_assigned_only(self):
        event1, _ = self.EventService.create(
            name="Assigned", date=datetime(2026, 6, 1), group_id=self.group_id,
            allowed_admin_ids=[self.admin.id],
        )
        self.EventService.create(name="Unassigned", date=datetime(2026, 6, 2), group_id=self.group_id)
        events = self.EventService.get_for_user(self.admin)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].id, event1.id)


class TestCanAccessEventHelper(unittest.TestCase):
    """can_access_event() returns correct values for all user types."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        from app.routes.auth import can_access_event
        self.can_access_event = can_access_event

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()

        self.event = Event(name="Test Event", date=datetime(2026, 6, 1), group_id=group.id)
        db.session.add(self.event)
        db.session.flush()

        self.su = _create_user("su", "su@test.com", "pw", is_admin=True, is_superuser=True)
        self.admin = _create_user("admin", "admin@test.com", "pw", is_admin=True, is_superuser=False)
        self.norole = _create_user("norole", "norole@test.com", "pw", is_admin=False, is_superuser=False)

        db.session.add(EventAdmin(event_id=self.event.id, user_id=self.admin.id))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_superuser_always_has_access(self):
        self.assertTrue(self.can_access_event(self.su, self.event))

    def test_assigned_admin_has_access(self):
        self.assertTrue(self.can_access_event(self.admin, self.event))

    def test_norole_user_denied(self):
        self.assertFalse(self.can_access_event(self.norole, self.event))

    def test_unassigned_admin_denied(self):
        unassigned = _create_user("unassigned", "u@test.com", "pw", is_admin=True)
        self.assertFalse(self.can_access_event(unassigned, self.event))


if __name__ == "__main__":
    unittest.main()

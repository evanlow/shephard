"""Smoke tests for event-level access control on /api/attendance routes.

Covers:
- Unassigned admin cannot list attendance for a hidden event.
- Unassigned admin cannot call event status for a hidden event.
- Unassigned admin cannot record attendance for a hidden event.
- Unassigned admin cannot update/delete an attendance record for a hidden event.
- Assigned admin can perform all the above for assigned events.
- Superuser retains full access.
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


class TestUnassignedAdminAttendanceAPIDenied(unittest.TestCase):
    """An ordinary admin not assigned to an event cannot access its attendance API."""

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

        self.event = Event(name="Hidden Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(self.event)

        self.member = Member(name="Test Member", group_id=group.id)
        db.session.add(self.member)
        db.session.commit()

        # Create an attendance record via a superuser so we can test PUT/DELETE
        su = _create_user("su", "su@test.com", "supass", is_admin=True, is_superuser=True)
        _login(self.client, "su", "supass")
        resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event.id, "member_id": self.member.id, "present": True}),
            content_type="application/json",
        )
        self.attendance_id = json.loads(resp.data)["id"]
        # Switch back to unassigned admin
        _login(self.client, "admin", "pw")

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_unassigned_admin_list_with_event_id_returns_403(self):
        resp = self.client.get(f"/api/attendance/?event_id={self.event.id}")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("error", json.loads(resp.data))

    def test_unassigned_admin_list_without_event_id_returns_empty(self):
        # Ordinary admin with no assigned events sees an empty list, not records from hidden events.
        resp = self.client.get("/api/attendance/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data), [])

    def test_unassigned_admin_event_status_returns_403(self):
        resp = self.client.get(f"/api/attendance/event/{self.event.id}/status")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("error", json.loads(resp.data))

    def test_unassigned_admin_post_attendance_returns_403(self):
        member2 = Member(name="Another Member", group_id=self.event.group_id)
        db.session.add(member2)
        db.session.commit()
        resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event.id, "member_id": member2.id, "present": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("error", json.loads(resp.data))

    def test_unassigned_admin_put_attendance_returns_403(self):
        resp = self.client.put(
            f"/api/attendance/{self.attendance_id}",
            data=json.dumps({"present": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("error", json.loads(resp.data))

    def test_unassigned_admin_delete_attendance_returns_403(self):
        resp = self.client.delete(f"/api/attendance/{self.attendance_id}")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("error", json.loads(resp.data))


class TestAssignedAdminAttendanceAPIAllowed(unittest.TestCase):
    """An ordinary admin assigned to an event can access its attendance API."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

        self.admin = _create_user("admin", "admin@test.com", "pw", is_admin=True, is_superuser=False)

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()

        self.event = Event(name="Assigned Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(self.event)
        db.session.flush()

        self.member = Member(name="Test Member", group_id=group.id)
        db.session.add(self.member)

        db.session.add(EventAdmin(event_id=self.event.id, user_id=self.admin.id))
        db.session.commit()

        _login(self.client, "admin", "pw")

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_assigned_admin_can_list_attendance_for_event(self):
        resp = self.client.get(f"/api/attendance/?event_id={self.event.id}")
        self.assertEqual(resp.status_code, 200)

    def test_assigned_admin_list_without_event_id_returns_only_assigned_records(self):
        # Record one attendance entry
        self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event.id, "member_id": self.member.id, "present": True}),
            content_type="application/json",
        )
        resp = self.client.get("/api/attendance/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["event_id"], self.event.id)

    def test_assigned_admin_can_get_event_status(self):
        resp = self.client.get(f"/api/attendance/event/{self.event.id}/status")
        self.assertEqual(resp.status_code, 200)

    def test_assigned_admin_can_post_attendance(self):
        resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event.id, "member_id": self.member.id, "present": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_assigned_admin_can_put_attendance(self):
        create_resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event.id, "member_id": self.member.id, "present": True}),
            content_type="application/json",
        )
        attendance_id = json.loads(create_resp.data)["id"]
        resp = self.client.put(
            f"/api/attendance/{attendance_id}",
            data=json.dumps({"present": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(json.loads(resp.data)["present"])

    def test_assigned_admin_can_delete_attendance(self):
        create_resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event.id, "member_id": self.member.id, "present": True}),
            content_type="application/json",
        )
        attendance_id = json.loads(create_resp.data)["id"]
        resp = self.client.delete(f"/api/attendance/{attendance_id}")
        self.assertEqual(resp.status_code, 204)


class TestSuperuserAttendanceAPIFullAccess(unittest.TestCase):
    """A superuser can access all attendance API endpoints for any event."""

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

        self.event = Event(name="Any Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(self.event)

        self.member = Member(name="Test Member", group_id=group.id)
        db.session.add(self.member)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_superuser_can_list_attendance(self):
        resp = self.client.get(f"/api/attendance/?event_id={self.event.id}")
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_get_event_status(self):
        resp = self.client.get(f"/api/attendance/event/{self.event.id}/status")
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_post_attendance(self):
        resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event.id, "member_id": self.member.id, "present": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_superuser_can_put_attendance(self):
        create_resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event.id, "member_id": self.member.id, "present": True}),
            content_type="application/json",
        )
        attendance_id = json.loads(create_resp.data)["id"]
        resp = self.client.put(
            f"/api/attendance/{attendance_id}",
            data=json.dumps({"present": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_delete_attendance(self):
        create_resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event.id, "member_id": self.member.id, "present": True}),
            content_type="application/json",
        )
        attendance_id = json.loads(create_resp.data)["id"]
        resp = self.client.delete(f"/api/attendance/{attendance_id}")
        self.assertEqual(resp.status_code, 204)


if __name__ == "__main__":
    unittest.main()

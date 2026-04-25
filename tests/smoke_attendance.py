"""Smoke tests for app/routes/attendance.py

Covers: 401 without auth, record/list/update/delete with auth,
duplicate attendance rejection.
Attendance requires a valid event_id and member_id, so both are
created in setUp.
"""

import json
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.group import Group
from app.models.event import Event
from app.models.member import Member
from datetime import datetime


def _make_app():
    return create_app("testing")


def _create_and_login(client):
    user = User(username="admin", email="admin@test.com", is_superuser=True)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    client.post("/login", data={"username": "admin", "password": "password123"})


class TestAttendanceRouteAuth(unittest.TestCase):
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

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/attendance/")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("error", json.loads(resp.data))


class TestAttendanceCRUD(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_and_login(self.client)

        # Create supporting records
        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()

        event = Event(name="Test Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(event)

        member = Member(name="Test Member")
        db.session.add(member)

        db.session.commit()
        self.event_id = event.id
        self.member_id = member.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _record(self, event_id=None, member_id=None, present=True):
        return self.client.post(
            "/api/attendance/",
            data=json.dumps({
                "event_id": event_id or self.event_id,
                "member_id": member_id or self.member_id,
                "present": present,
            }),
            content_type="application/json",
        )

    def test_list_attendance_returns_empty_list(self):
        resp = self.client.get("/api/attendance/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data), [])

    def test_record_attendance_returns_201(self):
        resp = self._record(present=True)
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertEqual(data["event_id"], self.event_id)
        self.assertEqual(data["member_id"], self.member_id)
        self.assertTrue(data["present"])

    def test_record_attendance_no_event_id_returns_400(self):
        resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"member_id": self.member_id, "present": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_record_attendance_no_member_id_returns_400(self):
        resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event_id, "present": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_record_attendance_invalid_event_returns_400(self):
        resp = self._record(event_id=9999)
        self.assertEqual(resp.status_code, 400)

    def test_record_attendance_invalid_member_returns_400(self):
        resp = self._record(member_id=9999)
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_attendance_returns_400(self):
        self._record()
        resp = self._record()  # second record for same event+member
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn("error", data)

    def test_list_attendance_filtered_by_event(self):
        self._record()
        resp = self.client.get(f"/api/attendance/?event_id={self.event_id}")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 1)

    def test_update_attendance_returns_200(self):
        create_resp = self._record(present=True)
        record_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/attendance/{record_id}",
            data=json.dumps({"present": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(json.loads(resp.data)["present"])

    def test_update_attendance_missing_present_returns_400(self):
        create_resp = self._record()
        record_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/attendance/{record_id}",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_attendance_not_found_returns_404(self):
        resp = self.client.put(
            "/api/attendance/9999",
            data=json.dumps({"present": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_attendance_returns_204(self):
        create_resp = self._record()
        record_id = json.loads(create_resp.data)["id"]

        resp = self.client.delete(f"/api/attendance/{record_id}")
        self.assertEqual(resp.status_code, 204)

    def test_delete_attendance_not_found_returns_404(self):
        resp = self.client.delete("/api/attendance/9999")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()

"""Smoke tests for role-based access control.

Covers:
- Unauthenticated requests → 401 on all API routes.
- Authenticated users with no roles (is_admin=False, is_superuser=False) → 403.
- Admin users (is_admin=True) → access to management operations.
- Admin users → 403 on superuser-only DELETE endpoints.
- Superuser → full access including DELETE.
"""

import json
import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.group import Group
from app.models.event import Event
from app.models.member import Member

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


class TestUnauthenticatedReturns401(unittest.TestCase):
    """All API endpoints must return 401 for unauthenticated requests."""

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

    def test_members_401(self):
        self.assertEqual(self.client.get("/api/members/").status_code, 401)

    def test_groups_401(self):
        self.assertEqual(self.client.get("/api/groups/").status_code, 401)

    def test_events_401(self):
        self.assertEqual(self.client.get("/api/events/").status_code, 401)

    def test_attendance_401(self):
        self.assertEqual(self.client.get("/api/attendance/").status_code, 401)


class TestNoRoleUserBlocked(unittest.TestCase):
    """A logged-in user with no roles (is_admin=False, is_superuser=False) gets 403."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_user("norole", "norole@test.com", "password123", is_admin=False, is_superuser=False)
        _login(self.client, "norole", "password123")

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_members_returns_403(self):
        resp = self.client.get("/api/members/")
        self.assertEqual(resp.status_code, 403)

    def test_groups_returns_403(self):
        resp = self.client.get("/api/groups/")
        self.assertEqual(resp.status_code, 403)

    def test_events_returns_403(self):
        resp = self.client.get("/api/events/")
        self.assertEqual(resp.status_code, 403)

    def test_attendance_returns_403(self):
        resp = self.client.get("/api/attendance/")
        self.assertEqual(resp.status_code, 403)


class TestAdminUserAccess(unittest.TestCase):
    """An admin user (is_admin=True) can perform standard management operations."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_user("admin", "admin@test.com", "password123", is_admin=True)
        _login(self.client, "admin", "password123")

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.commit()
        self.group_id = group.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_admin_can_list_members(self):
        resp = self.client.get("/api/members/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_create_member(self):
        resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Alice"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_admin_can_list_groups(self):
        resp = self.client.get("/api/groups/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_create_group(self):
        resp = self.client.post(
            "/api/groups/",
            data=json.dumps({"name": "New Group"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_admin_can_list_events(self):
        resp = self.client.get("/api/events/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_create_event(self):
        resp = self.client.post(
            "/api/events/",
            data=json.dumps({"name": "Sunday Service", "date": VALID_DATE, "group_id": self.group_id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_admin_can_list_attendance(self):
        resp = self.client.get("/api/attendance/")
        self.assertEqual(resp.status_code, 200)


class TestAdminCannotDeleteSuperuserOnlyResources(unittest.TestCase):
    """An admin (not superuser) gets 403 when trying to delete members, groups, or events."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_user("admin", "admin@test.com", "password123", is_admin=True, is_superuser=False)
        _login(self.client, "admin", "password123")

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()

        event = Event(name="Test Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(event)

        member = Member(name="Test Member", group_id=group.id)
        db.session.add(member)

        db.session.commit()
        self.group_id = group.id
        self.event_id = event.id
        self.member_id = member.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_admin_cannot_delete_member(self):
        resp = self.client.delete(f"/api/members/{self.member_id}")
        self.assertEqual(resp.status_code, 403)

    def test_admin_cannot_delete_group(self):
        resp = self.client.delete(f"/api/groups/{self.group_id}")
        self.assertEqual(resp.status_code, 403)

    def test_admin_cannot_delete_event(self):
        resp = self.client.delete(f"/api/events/{self.event_id}")
        self.assertEqual(resp.status_code, 403)


class TestSuperuserFullAccess(unittest.TestCase):
    """A superuser can perform all operations including deletes."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_user("su", "su@test.com", "password123", is_admin=True, is_superuser=True)
        _login(self.client, "su", "password123")

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()

        event = Event(name="Test Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(event)

        member = Member(name="Test Member", group_id=group.id)
        db.session.add(member)

        db.session.commit()
        self.group_id = group.id
        self.event_id = event.id
        self.member_id = member.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_superuser_can_delete_member(self):
        resp = self.client.delete(f"/api/members/{self.member_id}")
        self.assertEqual(resp.status_code, 204)

    def test_superuser_can_delete_group(self):
        resp = self.client.delete(f"/api/groups/{self.group_id}")
        self.assertEqual(resp.status_code, 204)

    def test_superuser_can_delete_event(self):
        resp = self.client.delete(f"/api/events/{self.event_id}")
        self.assertEqual(resp.status_code, 204)


class TestMarkedByFieldRecorded(unittest.TestCase):
    """Attendance records include marked_by set to the current user's ID."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        self.admin = _create_user("admin", "admin@test.com", "password123", is_admin=True)
        _login(self.client, "admin", "password123")

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()

        event = Event(name="Test Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(event)

        member = Member(name="Test Member", group_id=group.id)
        db.session.add(member)

        db.session.commit()
        self.event_id = event.id
        self.member_id = member.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_record_attendance_includes_marked_by(self):
        resp = self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event_id, "member_id": self.member_id, "present": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertIn("marked_by", data)
        self.assertEqual(data["marked_by"], self.admin.id)

    def test_list_attendance_includes_marked_by(self):
        self.client.post(
            "/api/attendance/",
            data=json.dumps({"event_id": self.event_id, "member_id": self.member_id, "present": True}),
            content_type="application/json",
        )
        resp = self.client.get("/api/attendance/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 1)
        self.assertIn("marked_by", data[0])
        self.assertEqual(data[0]["marked_by"], self.admin.id)


class TestUserCreationSetsIsAdmin(unittest.TestCase):
    """Users created via the web form get is_admin=True."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_user("su", "su@test.com", "password123", is_admin=True, is_superuser=True)
        _login(self.client, "su", "password123")

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_created_user_has_is_admin_true(self):
        self.client.post(
            "/admin/users/new",
            data={
                "username": "newadmin",
                "email": "newadmin@test.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        user = db.session.execute(
            db.select(User).where(User.username == "newadmin")
        ).scalar_one_or_none()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_admin)
        self.assertFalse(user.is_superuser)


class TestToggleAdmin(unittest.TestCase):
    """Superuser can grant or revoke admin flag on other users."""

    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        self.su = _create_user("su", "su@test.com", "password123", is_admin=True, is_superuser=True)
        self.norole = _create_user("norole", "norole@test.com", "password123", is_admin=False)
        self.admin = _create_user("admin2", "admin2@test.com", "password123", is_admin=True)
        _login(self.client, "su", "password123")

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_grant_admin_to_norole_user(self):
        resp = self.client.post(f"/admin/users/{self.norole.id}/toggle-admin")
        self.assertEqual(resp.status_code, 302)
        db.session.refresh(self.norole)
        self.assertTrue(self.norole.is_admin)

    def test_revoke_admin_from_admin_user(self):
        resp = self.client.post(f"/admin/users/{self.admin.id}/toggle-admin")
        self.assertEqual(resp.status_code, 302)
        db.session.refresh(self.admin)
        self.assertFalse(self.admin.is_admin)

    def test_cannot_toggle_own_account(self):
        resp = self.client.post(f"/admin/users/{self.su.id}/toggle-admin")
        self.assertEqual(resp.status_code, 302)
        db.session.refresh(self.su)
        # Superuser status must be unchanged
        self.assertTrue(self.su.is_superuser)

    def test_cannot_toggle_superuser_account(self):
        su2 = _create_user("su2", "su2@test.com", "password123", is_admin=True, is_superuser=True)
        resp = self.client.post(f"/admin/users/{su2.id}/toggle-admin")
        self.assertEqual(resp.status_code, 302)
        db.session.refresh(su2)
        self.assertTrue(su2.is_superuser)

    def test_non_superuser_cannot_toggle_admin(self):
        self.client.post("/logout")
        _login(self.client, "admin2", "password123")
        resp = self.client.post(f"/admin/users/{self.norole.id}/toggle-admin")
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()

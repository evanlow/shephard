"""Smoke tests for app/routes/auth.py

Covers: login page, login success/failure, dashboard auth guard,
logout, superuser-only user management, create/delete user flows.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User


def _make_app():
    app = create_app("testing")
    return app


def _create_user(username, email, password, is_superuser=False):
    user = User(username=username, email=email, is_superuser=is_superuser)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


class TestLoginPage(unittest.TestCase):
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

    def test_login_page_loads(self):
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Login", resp.data)

    def test_login_redirects_when_already_authenticated(self):
        _create_user("su", "su@test.com", "password123", is_superuser=True)
        self.client.post("/login", data={"username": "su", "password": "password123"})
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 302)


class TestLoginPost(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        _create_user("admin", "admin@test.com", "password123", is_superuser=True)
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_login_success_redirects(self):
        resp = self.client.post(
            "/login", data={"username": "admin", "password": "password123"}
        )
        self.assertEqual(resp.status_code, 302)

    def test_login_wrong_password_returns_401(self):
        resp = self.client.post(
            "/login", data={"username": "admin", "password": "wrongpassword"}
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_unknown_user_returns_401(self):
        resp = self.client.post(
            "/login", data={"username": "nobody", "password": "password123"}
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_missing_fields_returns_400(self):
        resp = self.client.post("/login", data={})
        self.assertEqual(resp.status_code, 400)


class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        _create_user("admin", "admin@test.com", "password123", is_superuser=True)
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_dashboard_requires_auth(self):
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])
        self.assertIn("next=/dashboard", resp.headers["Location"])

    def test_dashboard_requires_auth_preserves_relative_query_next(self):
        resp = self.client.get("/dashboard?tab=weekly")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("next=/dashboard?tab%3Dweekly", resp.headers["Location"])

    def test_invalid_session_user_id_treated_as_anonymous(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = "not-an-int"
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_dashboard_accessible_when_logged_in(self):
        self.client.post("/login", data={"username": "admin", "password": "password123"})
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)

    def test_logout_redirects(self):
        self.client.post("/login", data={"username": "admin", "password": "password123"})
        resp = self.client.post("/logout")
        self.assertEqual(resp.status_code, 302)


class TestUserManagement(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.superuser = _create_user("su", "su@test.com", "password123", is_superuser=True)
        self.plain_user = _create_user("plain", "plain@test.com", "password123", is_superuser=False)
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login_as_superuser(self):
        self.client.post("/login", data={"username": "su", "password": "password123"})

    def _login_as_plain(self):
        self.client.post("/login", data={"username": "plain", "password": "password123"})

    def test_admin_users_requires_auth(self):
        resp = self.client.get("/admin/users")
        self.assertEqual(resp.status_code, 302)

    def test_admin_users_blocked_for_non_superuser(self):
        self._login_as_plain()
        resp = self.client.get("/admin/users")
        self.assertEqual(resp.status_code, 403)

    def test_admin_users_accessible_to_superuser(self):
        self._login_as_superuser()
        resp = self.client.get("/admin/users")
        self.assertEqual(resp.status_code, 200)

    def test_new_user_form_loads(self):
        self._login_as_superuser()
        resp = self.client.get("/admin/users/new")
        self.assertEqual(resp.status_code, 200)

    def test_create_user_success(self):
        self._login_as_superuser()
        resp = self.client.post(
            "/admin/users/new",
            data={
                "username": "newuser",
                "email": "new@test.com",
                "password": "validpass1",
                "confirm_password": "validpass1",
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        created = db.session.execute(
            db.select(User).where(User.username == "newuser")
        ).scalar_one_or_none()
        self.assertIsNotNone(created)

    def test_create_user_short_password_returns_400(self):
        self._login_as_superuser()
        resp = self.client.post(
            "/admin/users/new",
            data={
                "username": "newuser",
                "email": "new@test.com",
                "password": "short",
                "confirm_password": "short",
            },
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_user_password_mismatch_returns_400(self):
        self._login_as_superuser()
        resp = self.client.post(
            "/admin/users/new",
            data={
                "username": "newuser",
                "email": "new@test.com",
                "password": "password123",
                "confirm_password": "different123",
            },
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_user_duplicate_username_returns_400(self):
        self._login_as_superuser()
        resp = self.client.post(
            "/admin/users/new",
            data={
                "username": "plain",
                "email": "unique@test.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        self.assertEqual(resp.status_code, 400)

    def test_delete_user_success(self):
        self._login_as_superuser()
        target_id = self.plain_user.id
        resp = self.client.post(
            f"/admin/users/{target_id}/delete", follow_redirects=False
        )
        self.assertEqual(resp.status_code, 302)
        deleted = db.session.get(User, target_id)
        self.assertIsNone(deleted)

    def test_cannot_delete_self(self):
        self._login_as_superuser()
        su_id = self.superuser.id
        resp = self.client.post(
            f"/admin/users/{su_id}/delete", follow_redirects=False
        )
        # Redirects back to list (not deleted)
        self.assertEqual(resp.status_code, 302)
        still_there = db.session.get(User, su_id)
        self.assertIsNotNone(still_there)


# ---------------------------------------------------------------------------
# System Purge
# ---------------------------------------------------------------------------

class TestSystemPurge(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.superuser = _create_user("su", "su@test.com", "password123", is_superuser=True)
        self.plain_user = _create_user("plain", "plain@test.com", "password123", is_superuser=False)
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login_as_superuser(self):
        self.client.post("/login", data={"username": "su", "password": "password123"})

    def _login_as_plain(self):
        self.client.post("/login", data={"username": "plain", "password": "password123"})

    def _seed(self):
        """Create minimal data: one group, one member, one event, one attendance record."""
        from app.models.group import Group
        from app.models.member import Member
        from app.models.event import Event
        from app.models.attendance import Attendance
        from app.services.group_service import GroupService
        from datetime import datetime
        default = GroupService.get_default_group()
        group = Group(name="Worship")
        db.session.add(group)
        db.session.commit()
        member = Member(name="Test Person")
        db.session.add(member)
        db.session.commit()
        event = Event(name="Sunday", date=datetime(2026, 5, 1, 10, 0), group_id=group.id)
        db.session.add(event)
        db.session.commit()
        att = Attendance(event_id=event.id, member_id=member.id, present=True)
        db.session.add(att)
        db.session.commit()
        return group, member, event, att

    # --- access control ---

    def test_purge_page_requires_superuser(self):
        self._login_as_plain()
        resp = self.client.get("/admin/purge")
        self.assertEqual(resp.status_code, 403)

    def test_purge_page_requires_auth(self):
        resp = self.client.get("/admin/purge")
        self.assertEqual(resp.status_code, 302)

    def test_purge_page_loads_for_superuser(self):
        self._login_as_superuser()
        resp = self.client.get("/admin/purge")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"System Purge", resp.data)

    # --- confirmation validation ---

    def test_purge_attendance_wrong_confirm_redirects_with_error(self):
        self._login_as_superuser()
        self._seed()
        resp = self.client.post("/admin/purge/attendance", data={"confirm": "yes"})
        self.assertEqual(resp.status_code, 302)
        from app.models.attendance import Attendance
        count = db.session.query(Attendance).count()
        self.assertEqual(count, 1)  # not deleted

    # --- purge attendance ---

    def test_purge_attendance_deletes_all_records(self):
        self._login_as_superuser()
        self._seed()
        resp = self.client.post("/admin/purge/attendance", data={"confirm": "PURGE"})
        self.assertEqual(resp.status_code, 302)
        from app.models.attendance import Attendance
        self.assertEqual(db.session.query(Attendance).count(), 0)

    def test_purge_attendance_preserves_members_and_events(self):
        self._login_as_superuser()
        self._seed()
        self.client.post("/admin/purge/attendance", data={"confirm": "PURGE"})
        from app.models.member import Member
        from app.models.event import Event
        self.assertGreater(db.session.query(Member).count(), 0)
        self.assertGreater(db.session.query(Event).count(), 0)

    # --- purge members ---

    def test_purge_members_deletes_all_members(self):
        self._login_as_superuser()
        self._seed()
        resp = self.client.post("/admin/purge/members", data={"confirm": "PURGE"})
        self.assertEqual(resp.status_code, 302)
        from app.models.member import Member
        self.assertEqual(db.session.query(Member).count(), 0)

    def test_purge_members_also_deletes_attendance(self):
        self._login_as_superuser()
        self._seed()
        self.client.post("/admin/purge/members", data={"confirm": "PURGE"})
        from app.models.attendance import Attendance
        self.assertEqual(db.session.query(Attendance).count(), 0)

    def test_purge_members_preserves_groups_and_events(self):
        self._login_as_superuser()
        self._seed()
        self.client.post("/admin/purge/members", data={"confirm": "PURGE"})
        from app.models.group import Group
        from app.models.event import Event
        self.assertGreater(db.session.query(Group).count(), 0)
        self.assertGreater(db.session.query(Event).count(), 0)

    # --- purge groups ---

    def test_purge_groups_deletes_custom_groups(self):
        self._login_as_superuser()
        self._seed()
        resp = self.client.post("/admin/purge/groups", data={"confirm": "PURGE"})
        self.assertEqual(resp.status_code, 302)
        from app.models.group import Group
        from app.models.membership import DEFAULT_GROUP_NAME
        custom = db.session.query(Group).filter(Group.name != DEFAULT_GROUP_NAME).count()
        self.assertEqual(custom, 0)

    def test_purge_groups_preserves_all_members_group(self):
        self._login_as_superuser()
        self._seed()
        self.client.post("/admin/purge/groups", data={"confirm": "PURGE"})
        from app.models.group import Group
        from app.models.membership import DEFAULT_GROUP_NAME
        default = db.session.query(Group).filter(Group.name == DEFAULT_GROUP_NAME).first()
        self.assertIsNotNone(default)

    def test_purge_groups_also_deletes_events_and_attendance(self):
        self._login_as_superuser()
        self._seed()
        self.client.post("/admin/purge/groups", data={"confirm": "PURGE"})
        from app.models.event import Event
        from app.models.attendance import Attendance
        self.assertEqual(db.session.query(Event).count(), 0)
        self.assertEqual(db.session.query(Attendance).count(), 0)


# ---------------------------------------------------------------------------
# Full-system Excel export
# ---------------------------------------------------------------------------

class TestExport(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.superuser = _create_user("su", "su@test.com", "password123", is_superuser=True)
        self.plain_user = _create_user("plain", "plain@test.com", "password123", is_superuser=False)
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login_as_superuser(self):
        self.client.post("/login", data={"username": "su", "password": "password123"})

    def _login_as_plain(self):
        self.client.post("/login", data={"username": "plain", "password": "password123"})

    def _seed(self):
        from app.models.group import Group
        from app.models.member import Member
        from app.models.event import Event
        from app.models.attendance import Attendance
        from app.services.group_service import GroupService
        from datetime import datetime
        GroupService.get_default_group()
        group = Group(name="Choir")
        db.session.add(group)
        db.session.commit()
        member = Member(name="Alice")
        db.session.add(member)
        db.session.commit()
        event = Event(name="Sunday Service", date=datetime(2026, 5, 4, 10, 0), group_id=group.id)
        db.session.add(event)
        db.session.commit()
        att = Attendance(event_id=event.id, member_id=member.id, present=True)
        db.session.add(att)
        db.session.commit()
        return group, member, event, att

    def test_export_requires_auth(self):
        resp = self.client.get("/admin/export")
        self.assertEqual(resp.status_code, 302)

    def test_export_requires_superuser(self):
        self._login_as_plain()
        resp = self.client.get("/admin/export")
        self.assertEqual(resp.status_code, 403)

    def test_export_returns_xlsx_for_superuser(self):
        self._login_as_superuser()
        resp = self.client.get("/admin/export")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resp.content_type,
        )

    def test_export_is_attachment_with_filename(self):
        self._login_as_superuser()
        resp = self.client.get("/admin/export")
        disposition = resp.headers.get("Content-Disposition", "")
        self.assertIn("attachment", disposition)
        self.assertIn("shepherd_export_", disposition)
        self.assertIn(".xlsx", disposition)

    def test_export_first_sheet_is_members(self):
        import io
        import openpyxl
        self._login_as_superuser()
        self._seed()
        resp = self.client.get("/admin/export")
        wb = openpyxl.load_workbook(io.BytesIO(resp.data))
        self.assertEqual(wb.sheetnames[0], "Members")

    def test_export_members_sheet_contains_member_data(self):
        import io
        import openpyxl
        self._login_as_superuser()
        self._seed()
        resp = self.client.get("/admin/export")
        wb = openpyxl.load_workbook(io.BytesIO(resp.data))
        ws = wb["Members"]
        names = [ws.cell(row=r, column=2).value for r in range(2, ws.max_row + 1)]
        self.assertIn("Alice", names)

    def test_export_has_event_sheet(self):
        import io
        import openpyxl
        self._login_as_superuser()
        self._seed()
        resp = self.client.get("/admin/export")
        wb = openpyxl.load_workbook(io.BytesIO(resp.data))
        # There should be more than just the Members sheet
        self.assertGreater(len(wb.sheetnames), 1)

    def test_export_empty_db_returns_only_members_sheet(self):
        import io
        import openpyxl
        self._login_as_superuser()
        resp = self.client.get("/admin/export")
        wb = openpyxl.load_workbook(io.BytesIO(resp.data))
        self.assertEqual(wb.sheetnames, ["Members"])


if __name__ == "__main__":
    unittest.main()

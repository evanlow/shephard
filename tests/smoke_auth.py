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


if __name__ == "__main__":
    unittest.main()

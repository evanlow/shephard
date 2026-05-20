"""Smoke tests for app bootstrap and CLI commands in app.__init__.py."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, _ensure_default_group_membership, _ensure_sqlite_schema_compatibility
from app.extensions import db
from app.models.group import Group
from app.models.member import Member
from app.models.user import User
from config import config as app_config
from sqlalchemy import text


def _make_app(env="testing"):
    return create_app(env)


class TestAppBootstrap(unittest.TestCase):
    def setUp(self):
        self.app = _make_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_index_redirects_to_login_when_anonymous(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_index_redirects_to_dashboard_when_authenticated(self):
        user = User(username="root", email="root@test.com", is_superuser=True, is_admin=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        self.client.post("/login", data={"username": "root", "password": "password123"})

        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers["Location"])

    def test_non_api_forbidden_renders_403_template(self):
        user = User(username="plain", email="plain@test.com", is_superuser=False, is_admin=False)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        self.client.post("/login", data={"username": "plain", "password": "password123"})

        resp = self.client.get("/members")
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b"Access Denied", resp.data)


class TestCreateAdminCli(unittest.TestCase):
    def setUp(self):
        self.app = _make_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.runner = self.app.test_cli_runner()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_create_admin_missing_required_values(self):
        with patch("builtins.input", side_effect=["", "missing@test.com"]), patch(
            "getpass.getpass", side_effect=["password123", "password123"]
        ):
            result = self.runner.invoke(args=["create-admin"])
        self.assertIn("required", result.output)

    def test_create_admin_short_password(self):
        with patch("builtins.input", side_effect=["admin1", "admin1@test.com"]), patch(
            "getpass.getpass", side_effect=["short", "short"]
        ):
            result = self.runner.invoke(args=["create-admin"])
        self.assertIn("at least 8 characters", result.output)

    def test_create_admin_password_mismatch(self):
        with patch("builtins.input", side_effect=["admin2", "admin2@test.com"]), patch(
            "getpass.getpass", side_effect=["password123", "different123"]
        ):
            result = self.runner.invoke(args=["create-admin"])
        self.assertIn("do not match", result.output)

    def test_create_admin_duplicate_user(self):
        user = User(username="dup", email="dup@test.com", is_superuser=True, is_admin=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        with patch("builtins.input", side_effect=["dup", "dup@test.com"]), patch(
            "getpass.getpass", side_effect=["password123", "password123"]
        ):
            result = self.runner.invoke(args=["create-admin"])
        self.assertIn("already exists", result.output)

    def test_create_admin_success(self):
        with patch("builtins.input", side_effect=["newadmin", "newadmin@test.com"]), patch(
            "getpass.getpass", side_effect=["password123", "password123"]
        ):
            result = self.runner.invoke(args=["create-admin"])

        self.assertIn("created", result.output)
        created = db.session.execute(
            db.select(User).where(User.username == "newadmin")
        ).scalar_one_or_none()
        self.assertIsNotNone(created)
        self.assertTrue(created.is_superuser)
        self.assertTrue(created.is_admin)

    def test_init_db_command(self):
        result = self.runner.invoke(args=["init-db"])
        self.assertIn("Database tables created", result.output)


class TestProductionValidateBranch(unittest.TestCase):
    def test_create_app_production_with_validated_config(self):
        production_cfg = app_config["production"]
        old_secret = production_cfg.SECRET_KEY
        old_db = production_cfg.SQLALCHEMY_DATABASE_URI
        try:
            production_cfg.SECRET_KEY = "strong-test-secret"
            production_cfg.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            app = create_app("production")
            with app.app_context():
                self.assertIsNotNone(db.engine)
        finally:
            production_cfg.SECRET_KEY = old_secret
            production_cfg.SQLALCHEMY_DATABASE_URI = old_db


class TestInitHelpers(unittest.TestCase):
    def setUp(self):
        self.app = _make_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_ensure_default_group_membership_assigns_primary_and_default(self):
        extra_group = Group(name="Extra")
        db.session.add(extra_group)
        db.session.commit()

        no_primary = Member(name="No Primary")
        with_primary = Member(name="With Primary", group_id=extra_group.id)
        db.session.add_all([no_primary, with_primary])
        db.session.commit()

        _ensure_default_group_membership()
        db.session.refresh(no_primary)
        db.session.refresh(with_primary)

        self.assertIsNotNone(no_primary.group_id)
        self.assertTrue(any(group.name == "ALL MEMBERS" for group in no_primary.groups))
        self.assertTrue(any(group.name == "ALL MEMBERS" for group in with_primary.groups))
        self.assertTrue(any(group.name == "Extra" for group in with_primary.groups))

    def test_sqlite_schema_compatibility_returns_for_non_sqlite(self):
        with patch("app.db.engine.dialect.name", "postgresql"):
            _ensure_sqlite_schema_compatibility()

    def test_sqlite_schema_compatibility_skips_when_target_tables_missing(self):
        # Exercise branches where users/attendance tables are absent.
        db.session.execute(text("DROP TABLE IF EXISTS attendance"))
        db.session.execute(text("DROP TABLE IF EXISTS users"))
        db.session.commit()

        _ensure_sqlite_schema_compatibility()

    def test_ensure_default_group_membership_adds_missing_links(self):
        default_group = db.session.execute(
            db.select(Group).where(Group.name == "ALL MEMBERS")
        ).scalar_one()
        extra = Group(name="Extra Link")
        db.session.add(extra)
        db.session.commit()

        # Missing default group path (line adding default group membership).
        member_missing_default = Member(name="Missing Default", group_id=extra.id)
        member_missing_default.groups.append(extra)
        db.session.add(member_missing_default)
        db.session.commit()

        # Missing primary group path (line adding primary group membership).
        member_missing_primary = Member(name="Missing Primary", group_id=extra.id)
        member_missing_primary.groups.append(default_group)
        db.session.add(member_missing_primary)
        db.session.commit()

        _ensure_default_group_membership()
        db.session.refresh(member_missing_default)
        db.session.refresh(member_missing_primary)

        self.assertTrue(any(group.name == "ALL MEMBERS" for group in member_missing_default.groups))
        self.assertTrue(any(group.name == "Extra Link" for group in member_missing_primary.groups))


if __name__ == "__main__":
    unittest.main(verbosity=2)
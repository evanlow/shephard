"""Smoke test for SQLite schema compatibility upgrades.

Verifies legacy SQLite databases missing newly introduced columns are
upgraded automatically at app startup.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from sqlalchemy import text

from app import create_app
from app.extensions import db


class TestSQLiteSchemaUpgrade(unittest.TestCase):
    def test_legacy_db_gets_missing_columns(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        previous_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

        try:
            legacy_app = Flask(__name__)
            legacy_app.config.from_mapping(
                SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
                SQLALCHEMY_TRACK_MODIFICATIONS=False,
                SECRET_KEY="test-secret",
            )
            db.init_app(legacy_app)

            # Build a legacy schema equivalent to pre-RBAC / pre-marked_by state.
            with legacy_app.app_context():
                db.session.execute(
                    text(
                        "CREATE TABLE users ("
                        "id INTEGER PRIMARY KEY, "
                        "username VARCHAR(64) UNIQUE NOT NULL, "
                        "email VARCHAR(120) UNIQUE NOT NULL, "
                        "password_hash VARCHAR(256) NOT NULL, "
                        "is_superuser BOOLEAN NOT NULL DEFAULT 0, "
                        "created_at DATETIME NOT NULL"
                        ")"
                    )
                )
                db.session.execute(
                    text(
                        "CREATE TABLE attendance ("
                        "id INTEGER PRIMARY KEY, "
                        "event_id INTEGER NOT NULL, "
                        "member_id INTEGER NOT NULL, "
                        "present BOOLEAN NOT NULL DEFAULT 0, "
                        "recorded_at DATETIME NOT NULL"
                        ")"
                    )
                )
                db.session.commit()
                db.session.remove()
                db.engine.dispose()

            # Startup should upgrade the legacy schema in-place.
            app = create_app("development")
            with app.app_context():
                user_columns = {
                    row[1] for row in db.session.execute(text("PRAGMA table_info(users)"))
                }
                attendance_columns = {
                    row[1] for row in db.session.execute(text("PRAGMA table_info(attendance)"))
                }
                db.session.remove()
                db.engine.dispose()

            self.assertIn("is_admin", user_columns)
            self.assertIn("marked_by", attendance_columns)
        finally:
            if previous_db_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_db_url

            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)

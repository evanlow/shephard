from __future__ import annotations

from flask import Flask, jsonify, redirect, request, url_for
from flask_login import current_user
from sqlalchemy import text

from config import config
from .extensions import db, login_manager
from .models.user import User
from .models.member import Member
from .models.group import Group
from .models.membership import DEFAULT_GROUP_NAME
from .services.group_service import GroupService
from .routes import attendance, auth, events, groups, members, ui


def _ensure_sqlite_schema_compatibility() -> None:
    """Apply additive schema fixes for legacy SQLite databases.

    SQLite's ALTER TABLE support is limited and db.create_all() does not add
    missing columns on existing tables. This keeps local/dev databases usable
    after pulling model updates.
    """

    if db.engine.dialect.name != "sqlite":
        return

    with db.engine.begin() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }

        if "users" in tables:
            user_columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(users)"))
            }
            if "is_admin" not in user_columns:
                conn.execute(
                    text(
                        "ALTER TABLE users "
                        "ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
                    )
                )

        if "attendance" in tables:
            attendance_columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(attendance)"))
            }
            if "marked_by" not in attendance_columns:
                conn.execute(text("ALTER TABLE attendance ADD COLUMN marked_by INTEGER"))

        if "events" in tables:
            event_columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(events)"))
            }
            if "is_archived" not in event_columns:
                conn.execute(
                    text(
                        "ALTER TABLE events "
                        "ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0"
                    )
                )

        if "member_groups" in tables:
            mg_columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(member_groups)"))
            }
            if "joined_at" not in mg_columns:
                conn.execute(
                    text(
                        "ALTER TABLE member_groups "
                        "ADD COLUMN joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    )
                )
                # Backfill existing rows with the epoch so they predate all events
                # and are never incorrectly excluded from historical reports.
                # New rows created after this migration will get CURRENT_TIMESTAMP.
                conn.execute(
                    text("UPDATE member_groups SET joined_at = '1970-01-01 00:00:00'")
                )


def _ensure_default_group_membership() -> None:
    default_group = GroupService.get_default_group()

    members = db.session.execute(db.select(Member).order_by(Member.id)).scalars().all()
    for member in members:
        if member.group_id is None:
            member.group_id = default_group.id
        if default_group not in member.groups:
            member.groups.append(default_group)
        if member.group and member.group not in member.groups:
            member.groups.append(member.group)

    db.session.commit()


def create_app(env: str = "development") -> Flask:
    app = Flask(__name__)
    cfg = config.get(env, config["default"])
    app.config.from_object(cfg)

    if hasattr(cfg, "validate"):
        cfg.validate()

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required"}), 401
        next_path = request.full_path if request.query_string else request.path
        return redirect(url_for(login_manager.login_view, next=next_path))

    @app.errorhandler(403)
    def forbidden_template(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Forbidden"}), 403
        from flask import render_template

        return render_template("403.html"), 403

    app.register_blueprint(auth.bp)
    app.register_blueprint(ui.bp)
    app.register_blueprint(members.bp, url_prefix="/api/members")
    app.register_blueprint(groups.bp, url_prefix="/api/groups")
    app.register_blueprint(events.bp, url_prefix="/api/events")
    app.register_blueprint(attendance.bp, url_prefix="/api/attendance")

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            from flask import redirect, url_for

            return redirect(url_for("auth.dashboard"))
        from flask import redirect, url_for

        return redirect(url_for("auth.login"))

    @app.cli.command("create-admin")
    def create_admin():
        import getpass

        username = input("Username: ").strip()
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm Password: ")

        if not username or not email or not password:
            print("Username, email, and password are required.")
            return
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            return
        if password != confirm:
            print("Passwords do not match.")
            return

        existing = db.session.execute(
            db.select(User).where((User.username == username) | (User.email == email))
        ).scalar_one_or_none()
        if existing:
            print("A user with that username or email already exists.")
            return

        user = User(username=username, email=email, is_superuser=True, is_admin=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Superuser '{username}' created.")

    @app.cli.command("init-db")
    def init_db():
        with app.app_context():
            db.create_all()
            _ensure_sqlite_schema_compatibility()
            _ensure_default_group_membership()
        print("Database tables created.")

    with app.app_context():
        db.create_all()
        _ensure_sqlite_schema_compatibility()
        _ensure_default_group_membership()

    return app

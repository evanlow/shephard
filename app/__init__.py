from __future__ import annotations

from flask import Flask, jsonify, redirect, request, url_for
from flask_login import current_user

from config import config
from .extensions import db, login_manager
from .models.user import User
from .routes import attendance, auth, events, groups, members


def create_app(env: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config.get(env, config["default"]))

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required"}), 401
        return redirect(url_for(login_manager.login_view, next=request.url))

    @app.errorhandler(403)
    def forbidden_template(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Forbidden"}), 403
        from flask import render_template

        return render_template("403.html"), 403

    app.register_blueprint(auth.bp)
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

        user = User(username=username, email=email, is_superuser=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Superuser '{username}' created.")

    with app.app_context():
        db.create_all()

    return app

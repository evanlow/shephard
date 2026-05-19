from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models.user import User

bp = Blueprint("auth", __name__)


def admin_required(f):
    """Decorator: requires the current user to be an admin or superuser."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not (current_user.is_admin or current_user.is_superuser):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def superuser_required(f):
    """Decorator: requires the current user to have is_superuser=True."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_superuser:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# User management (superuser only)
# ---------------------------------------------------------------------------

@bp.get("/admin/users")
@superuser_required
def list_users():
    users = db.session.execute(db.select(User).order_by(User.username)).scalars().all()
    return render_template("auth/users.html", users=users)


@bp.get("/admin/users/new")
@superuser_required
def new_user():
    return render_template("auth/user_form.html")


@bp.post("/admin/users/new")
@superuser_required
def create_user():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    errors = []
    if not username:
        errors.append("Username is required.")
    if not email:
        errors.append("Email is required.")
    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif password != confirm:
        errors.append("Passwords do not match.")

    if not errors:
        existing = db.session.execute(
            db.select(User).where(
                (User.username == username) | (User.email == email)
            )
        ).scalar_one_or_none()
        if existing:
            errors.append("A user with that username or email already exists.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("auth/user_form.html",
                               username=username, email=email), 400

    user = User(username=username, email=email, is_admin=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"User '{username}' created successfully.", "success")
    return redirect(url_for("auth.list_users"))


@bp.post("/admin/users/<int:user_id>/delete")
@superuser_required
def delete_user(user_id: int):
    if user_id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("auth.list_users"))

    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("auth.list_users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' deleted.", "success")
    return redirect(url_for("auth.list_users"))


@bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return render_template("auth/login.html")


@bp.post("/login")
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    remember = bool(request.form.get("remember"))

    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("auth/login.html"), 400

    user = db.session.execute(
        db.select(User).where(User.username == username)
    ).scalar_one_or_none()

    if user is None or not user.check_password(password):
        flash("Invalid username or password.", "error")
        return render_template("auth/login.html"), 401

    login_user(user, remember=remember)

    next_page = request.args.get("next")
    # Guard against open-redirect: only allow relative paths
    if next_page and next_page.startswith("/") and not next_page.startswith("//"):
        return redirect(next_page)
    return redirect(url_for("auth.dashboard"))


@bp.get("/dashboard")
@login_required
def dashboard():
    from ..services.event_service import EventService
    from ..services.group_service import GroupService
    from ..services.member_service import MemberService

    members = MemberService.get_all()
    groups = GroupService.get_all()
    events = EventService.get_all()
    recent_events = events[:5]

    return render_template(
        "auth/dashboard.html",
        member_count=len(members),
        group_count=len(groups),
        event_count=len(events),
        recent_events=recent_events,
    )


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

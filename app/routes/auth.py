import io
from datetime import datetime, timezone
from functools import wraps

import openpyxl
from openpyxl.styles import Font

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import text

from ..extensions import db
from ..models.attendance import Attendance
from ..models.event import Event
from ..models.group import Group
from ..models.member import Member
from ..models.membership import DEFAULT_GROUP_NAME, member_groups
from ..models.user import User
from ..services.attendance_service import AttendanceService

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


@bp.post("/admin/users/<int:user_id>/toggle-admin")
@superuser_required
def toggle_admin(user_id: int):
    if user_id == current_user.id:
        flash("You cannot change your own admin status.", "error")
        return redirect(url_for("auth.list_users"))

    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("auth.list_users"))

    if user.is_superuser:
        flash("Superuser accounts cannot be modified this way.", "error")
        return redirect(url_for("auth.list_users"))

    user.is_admin = not user.is_admin
    db.session.commit()

    status = "granted" if user.is_admin else "revoked"
    flash(f"Admin access {status} for '{user.username}'.", "success")
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


# ---------------------------------------------------------------------------
# System Purge (superuser only)
# ---------------------------------------------------------------------------

@bp.get("/admin/purge")
@superuser_required
def purge_page():
    return render_template("auth/purge.html")


@bp.post("/admin/purge/attendance")
@superuser_required
def purge_attendance():
    if request.form.get("confirm", "").strip().upper() != "PURGE":
        flash("Type PURGE to confirm.", "error")
        return redirect(url_for("auth.purge_page"))
    count = db.session.query(Attendance).delete(synchronize_session=False)
    db.session.commit()
    flash(f"All attendance records deleted ({count} record{'s' if count != 1 else ''} removed).", "success")
    return redirect(url_for("auth.purge_page"))


@bp.post("/admin/purge/members")
@superuser_required
def purge_members():
    if request.form.get("confirm", "").strip().upper() != "PURGE":
        flash("Type PURGE to confirm.", "error")
        return redirect(url_for("auth.purge_page"))
    # Delete in FK order: attendance → member_groups junction → members
    db.session.query(Attendance).delete(synchronize_session=False)
    db.session.execute(text("DELETE FROM member_groups"))
    count = db.session.query(Member).delete(synchronize_session=False)
    db.session.commit()
    flash(f"All members deleted ({count} member{'s' if count != 1 else ''} removed).", "success")
    return redirect(url_for("auth.purge_page"))


@bp.post("/admin/purge/groups")
@superuser_required
def purge_groups():
    if request.form.get("confirm", "").strip().upper() != "PURGE":
        flash("Type PURGE to confirm.", "error")
        return redirect(url_for("auth.purge_page"))
    # Collect non-default group IDs
    non_default_ids = db.session.execute(
        db.select(Group.id).where(Group.name != DEFAULT_GROUP_NAME)
    ).scalars().all()

    if non_default_ids:
        # Cascade manually: attendance for events → events → member_groups → groups
        event_ids = db.session.execute(
            db.select(Event.id).where(Event.group_id.in_(non_default_ids))
        ).scalars().all()
        if event_ids:
            db.session.query(Attendance).filter(
                Attendance.event_id.in_(event_ids)
            ).delete(synchronize_session=False)
        db.session.query(Event).filter(
            Event.group_id.in_(non_default_ids)
        ).delete(synchronize_session=False)
        db.session.execute(
            member_groups.delete().where(member_groups.c.group_id.in_(non_default_ids))
        )
        db.session.query(Member).filter(
            Member.group_id.in_(non_default_ids)
        ).update({"group_id": None}, synchronize_session=False)
        db.session.query(Group).filter(
            Group.id.in_(non_default_ids)
        ).delete(synchronize_session=False)
        db.session.commit()

    n = len(non_default_ids)
    flash(f"All custom groups deleted ({n} group{'s' if n != 1 else ''} removed; ALL MEMBERS preserved).", "success")
    return redirect(url_for("auth.purge_page"))


# ---------------------------------------------------------------------------
# Full-system Excel export (superuser only)
# ---------------------------------------------------------------------------

@bp.get("/admin/export")
@superuser_required
def export_all():
    wb = openpyxl.Workbook()

    # ── Sheet 1: Members ─────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Members"

    header = ["#", "Name", "Primary Group", "All Groups", "Status", "Member Since", "Deactivated"]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    members = db.session.execute(db.select(Member).order_by(Member.name)).scalars().all()
    for i, m in enumerate(members, 1):
        primary = m.group.name if m.group else "—"
        all_groups = ", ".join(g.name for g in m.groups)
        status = "Inactive" if m.deactivated_at else "Active"
        since = m.created_at.strftime("%d %b %Y") if m.created_at else "—"
        deactivated = m.deactivated_at.strftime("%d %b %Y") if m.deactivated_at else ""
        ws.append([i, m.name, primary, all_groups, status, since, deactivated])

    # Set column widths
    for col, width in zip("ABCDEFG", [5, 30, 20, 40, 12, 15, 15]):
        ws.column_dimensions[col].width = width

    # ── One sheet per event (oldest first) ───────────────────────────────────
    events = db.session.execute(
        db.select(Event).order_by(Event.date.asc(), Event.name)
    ).scalars().all()

    used_names = {"Members"}
    for event in events:
        # Build a unique sheet name within Excel's 31-char limit
        raw = f"{event.date.strftime('%d%b%y')} {event.name}"
        sheet_name = raw[:31]
        if sheet_name in used_names:
            base = raw[:28]
            n = 2
            while f"{base}({n})" in used_names:
                n += 1
            sheet_name = f"{base}({n})"
        used_names.add(sheet_name)

        ws_ev = wb.create_sheet(title=sheet_name)

        # Event metadata header block
        meta = [
            ("Event:", event.name),
            ("Date:", event.date.strftime("%d %b %Y")),
            ("Group:", event.group.name if event.group else "—"),
            ("Archived:", "Yes" if event.is_archived else "No"),
        ]
        for label, value in meta:
            ws_ev.append([label, value])
            ws_ev.cell(row=ws_ev.max_row, column=1).font = Font(bold=True)
        ws_ev.append([])  # blank separator

        # Attendance table header
        att_header_row = ws_ev.max_row + 1
        ws_ev.append(["#", "Name", "Present"])
        for cell in ws_ev[att_header_row]:
            cell.font = Font(bold=True)

        # Attendance data
        status_data, _ = AttendanceService.get_event_status(event.id)
        if status_data and status_data["expected_members"]:
            present_ids = {m["id"] for m in status_data["present_members"]}
            for j, m_data in enumerate(status_data["expected_members"], 1):
                present = "Yes" if m_data["id"] in present_ids else "No"
                ws_ev.append([j, m_data["name"], present])
            ws_ev.append([])
            ws_ev.append(["", "Present:", status_data["present_count"]])
            ws_ev.append(["", "Absent:", status_data["absent_count"]])
            ws_ev.append(["", "Total:", status_data["expected_count"]])
            for row in ws_ev.iter_rows(min_row=ws_ev.max_row - 2, max_row=ws_ev.max_row, min_col=2, max_col=2):
                for cell in row:
                    cell.font = Font(bold=True)
        else:
            ws_ev.append(["", "(No eligible members for this event)", ""])

        ws_ev.column_dimensions["A"].width = 5
        ws_ev.column_dimensions["B"].width = 30
        ws_ev.column_dimensions["C"].width = 10

    # ── Stream to response ───────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"shepherd_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )

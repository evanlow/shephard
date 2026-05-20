"""HTML UI routes for the Shepherd admin interface.

All routes require admin login (enforced via @admin_required on each view).
These routes render Bootstrap-based templates and use the existing service
layer — no direct DB calls except where the service layer doesn't expose
the needed query.
"""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..extensions import db
from ..models.attendance import Attendance
from ..models.member import Member
from ..routes.auth import admin_required, superuser_required
from ..services.attendance_service import AttendanceService
from ..services.event_service import EventService
from ..services.group_service import GroupService
from ..services.member_service import MemberService

bp = Blueprint("ui", __name__)


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@bp.get("/members")
@admin_required
def members():
    all_members = MemberService.get_all()
    default_group = GroupService.get_default_group()
    all_groups = [group for group in GroupService.get_all() if group.id != default_group.id]
    return render_template(
        "ui/members.html",
        members=all_members,
        groups=all_groups,
        default_group=default_group,
    )


@bp.post("/members")
@admin_required
def create_member():
    name = request.form.get("name", "").strip()
    group_id = request.form.get("group_id") or None
    group_ids = [int(group_id) for group_id in request.form.getlist("group_ids") if group_id]
    if group_id:
        try:
            group_id = int(group_id)
        except ValueError:
            group_id = None

    if not name:
        flash("Member name is required.", "error")
        return redirect(url_for("ui.members"))

    member, error = MemberService.create(name=name, group_id=group_id, group_ids=group_ids)
    if error:
        flash(error, "error")
    else:
        flash(f"Member '{member.name}' added.", "success")
    return redirect(url_for("ui.members"))


@bp.get("/members/<int:member_id>/edit")
@admin_required
def edit_member(member_id: int):
    member = MemberService.get_by_id(member_id)
    if not member:
        flash("Member not found.", "error")
        return redirect(url_for("ui.members"))
    default_group = GroupService.get_default_group()
    all_groups = [group for group in GroupService.get_all() if group.id != default_group.id]
    return render_template("ui/member_edit.html", member=member, groups=all_groups, default_group=default_group)


@bp.post("/members/<int:member_id>/edit")
@admin_required
def update_member(member_id: int):
    name = request.form.get("name", "").strip() or None
    raw_group = request.form.get("group_id")
    group_id = int(raw_group) if raw_group and raw_group != "0" else None
    group_ids = [int(group_id) for group_id in request.form.getlist("group_ids") if group_id]
    groups_provided = raw_group is not None or bool(request.form.getlist("group_ids"))

    member, error = MemberService.update(
        member_id,
        name=name,
        group_id=group_id,
        group_ids=group_ids,
        groups_provided=groups_provided,
    )
    if error == "Member not found":
        flash("Member not found.", "error")
        return redirect(url_for("ui.members"))
    if error:
        flash(error, "error")
        return redirect(url_for("ui.edit_member", member_id=member_id))

    flash(f"Member '{member.name}' updated.", "success")
    return redirect(url_for("ui.members"))


@bp.post("/members/<int:member_id>/delete")
@superuser_required
def delete_member(member_id: int):
    member = MemberService.get_by_id(member_id)
    if not member:
        flash("Member not found.", "error")
        return redirect(url_for("ui.members"))
    name = member.name
    MemberService.delete(member_id)
    flash(f"Member '{name}' deleted.", "success")
    return redirect(url_for("ui.members"))


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

@bp.get("/groups")
@admin_required
def groups():
    all_groups = GroupService.get_all()
    default_group = GroupService.get_default_group()
    # Attach member counts
    groups_data = []
    for g in all_groups:
        count = len(g.members)
        groups_data.append({"group": g, "member_count": count})
    return render_template("ui/groups.html", groups_data=groups_data, default_group=default_group)


@bp.post("/groups")
@admin_required
def create_group():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip() or None
    if not name:
        flash("Group name is required.", "error")
        return redirect(url_for("ui.groups"))

    try:
        group = GroupService.create(name=name, description=description)
        flash(f"Group '{group.name}' created.", "success")
    except Exception:
        db.session.rollback()
        flash("A group with that name already exists.", "error")
    return redirect(url_for("ui.groups"))


@bp.get("/groups/<int:group_id>/edit")
@admin_required
def edit_group(group_id: int):
    group = GroupService.get_by_id(group_id)
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("ui.groups"))
    return render_template("ui/group_edit.html", group=group)


@bp.post("/groups/<int:group_id>/edit")
@admin_required
def update_group(group_id: int):
    name = request.form.get("name", "").strip() or None
    description = request.form.get("description", "").strip()

    group = GroupService.get_by_id(group_id)
    if group and group.name == "ALL MEMBERS" and name and name != group.name:
        flash("The ALL MEMBERS group cannot be renamed.", "error")
        return redirect(url_for("ui.edit_group", group_id=group_id))

    if not name:
        flash("Group name is required.", "error")
        return redirect(url_for("ui.edit_group", group_id=group_id))

    group = GroupService.update(group_id, name=name, description=description)
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("ui.groups"))

    flash(f"Group '{group.name}' updated.", "success")
    return redirect(url_for("ui.groups"))


@bp.post("/groups/<int:group_id>/delete")
@superuser_required
def delete_group(group_id: int):
    group = GroupService.get_by_id(group_id)
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("ui.groups"))
    name = group.name
    GroupService.delete(group_id)
    flash(f"Group '{name}' deleted. Members have been unassigned.", "success")
    return redirect(url_for("ui.groups"))


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@bp.get("/events")
@admin_required
def events():
    all_events = EventService.get_all()
    all_groups = GroupService.get_all()
    return render_template("ui/events.html", events=all_events, groups=all_groups)


@bp.post("/events")
@admin_required
def create_event():
    name = request.form.get("name", "").strip()
    date_str = request.form.get("date", "").strip()
    group_id = request.form.get("group_id") or None

    errors = []
    if not name:
        errors.append("Event name is required.")
    if not date_str:
        errors.append("Date and time are required.")
    if not group_id:
        errors.append("Group is required.")

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("ui.events"))

    try:
        date = datetime.fromisoformat(date_str)
    except ValueError:
        flash("Invalid date/time format.", "error")
        return redirect(url_for("ui.events"))

    event, error = EventService.create(name=name, date=date, group_id=int(group_id))
    if error:
        flash(error, "error")
    else:
        flash(f"Event '{event.name}' created.", "success")
    return redirect(url_for("ui.events"))


@bp.post("/events/<int:event_id>/delete")
@superuser_required
def delete_event(event_id: int):
    event = EventService.get_by_id(event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("ui.events"))
    name = event.name
    EventService.delete(event_id)
    flash(f"Event '{name}' deleted.", "success")
    return redirect(url_for("ui.events"))


# ---------------------------------------------------------------------------
# Attendance taking
# ---------------------------------------------------------------------------

@bp.get("/events/<int:event_id>/attendance")
@admin_required
def attendance(event_id: int):
    event = EventService.get_by_id(event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("ui.events"))

    group = GroupService.get_by_id(event.group_id)

    expected_members = list(event.group.members)
    expected_members.sort(key=lambda member: member.name)

    records = AttendanceService.get_all(event_id=event_id)
    attendance_by_member = {r.member_id: r for r in records}

    members_status = []
    for m in expected_members:
        rec = attendance_by_member.get(m.id)
        members_status.append({
            "member": m,
            "attendance_id": rec.id if rec else None,
            "present": rec.present if rec else False,
        })

    present_count = sum(1 for ms in members_status if ms["present"])
    absent_count = len(members_status) - present_count

    return render_template(
        "ui/attendance.html",
        event=event,
        group=group,
        members_status=members_status,
        expected_count=len(members_status),
        present_count=present_count,
        absent_count=absent_count,
    )


@bp.post("/events/<int:event_id>/attendance/mark")
@admin_required
def mark_present(event_id: int):
    member_id = request.form.get("member_id", type=int)
    if not member_id:
        flash("Member ID is required.", "error")
        return redirect(url_for("ui.attendance", event_id=event_id))

    records = AttendanceService.get_all(event_id=event_id, member_id=member_id)
    if records:
        AttendanceService.update(records[0].id, present=True)
    else:
        _, error = AttendanceService.record(
            event_id=event_id,
            member_id=member_id,
            present=True,
            marked_by=current_user.id,
        )
        if error:
            flash(error, "error")
    return redirect(url_for("ui.attendance", event_id=event_id))


@bp.post("/events/<int:event_id>/attendance/unmark")
@admin_required
def mark_absent(event_id: int):
    member_id = request.form.get("member_id", type=int)
    if not member_id:
        flash("Member ID is required.", "error")
        return redirect(url_for("ui.attendance", event_id=event_id))

    records = AttendanceService.get_all(event_id=event_id, member_id=member_id)
    if records:
        AttendanceService.update(records[0].id, present=False)
    return redirect(url_for("ui.attendance", event_id=event_id))


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@bp.get("/reports")
@admin_required
def reports():
    all_events = EventService.get_all()
    event_id = request.args.get("event_id", type=int)
    status = None
    selected_event = None
    if event_id:
        selected_event = EventService.get_by_id(event_id)
        if selected_event:
            status, _ = AttendanceService.get_event_status(event_id)
    return render_template(
        "ui/reports.html",
        events=all_events,
        selected_event=selected_event,
        status=status,
        event_id=event_id,
    )

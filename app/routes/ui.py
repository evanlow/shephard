"""HTML UI routes for the Shepherd admin interface.

All routes require admin login (enforced via @admin_required on each view).
These routes render Bootstrap-based templates and use the existing service
layer — no direct DB calls except where the service layer doesn't expose
the needed query.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

import io

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from ..extensions import db
from ..models.attendance import Attendance
from ..models.group import Group
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

    expected_members = db.session.execute(
        db.select(Member)
        .join(Member.groups)
        .where(Group.id == event.group_id)
        .order_by(Member.name)
    ).scalars().all()

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


@bp.get("/events/<int:event_id>/attendance/pdf")
@admin_required
def attendance_pdf(event_id: int):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    status, error = AttendanceService.get_event_status(event_id)
    if error:
        flash("Event not found.", "error")
        return redirect(url_for("ui.events"))

    event = EventService.get_by_id(event_id)
    group = GroupService.get_by_id(event.group_id) if event else None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    event_name = escape(status["event_name"])
    elements.append(Paragraph(f"Attendance Report: {event_name}", styles["Title"]))
    date_str = event.date.strftime("%A, %d %B %Y — %H:%M") if event else ""
    group_str = f"Group: {escape(group.name)}" if group else ""
    if date_str or group_str:
        elements.append(Paragraph(f"{date_str}{'  |  ' + group_str if group_str else ''}", styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    # Summary row
    summary_data = [
        ["Expected", "Present", "Absent"],
        [str(status["expected_count"]), str(status["present_count"]), str(status["absent_count"])],
    ]
    summary_table = Table(summary_data, colWidths=[4 * cm, 4 * cm, 4 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6c757d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#d4edda")),
        ("BACKGROUND", (2, 1), (2, 1), colors.HexColor("#f8d7da")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Attendance table
    present_ids = {m["id"] for m in status["present_members"]}
    all_members = status["expected_members"]
    table_data = [["#", "Member Name", "Status"]]
    for i, m in enumerate(all_members, start=1):
        is_present = m["id"] in present_ids
        table_data.append([str(i), m["name"], "Present" if is_present else "Absent"])

    col_widths = [1.2 * cm, None, 3.5 * cm]
    att_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    row_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#343a40")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_idx, m in enumerate(all_members, start=1):
        is_present = m["id"] in present_ids
        if is_present:
            row_styles.append(("TEXTCOLOR", (2, row_idx), (2, row_idx), colors.HexColor("#198754")))
            row_styles.append(("FONTNAME", (2, row_idx), (2, row_idx), "Helvetica-Bold"))
        else:
            row_styles.append(("TEXTCOLOR", (2, row_idx), (2, row_idx), colors.HexColor("#dc3545")))

    att_table.setStyle(TableStyle(row_styles))
    elements.append(att_table)

    doc.build(elements)
    buf.seek(0)

    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in status["event_name"])
    filename = f"attendance_{safe_name}.pdf"
    return send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name=filename)


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

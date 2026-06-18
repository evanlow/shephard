from flask import Blueprint, jsonify, request
from flask_login import current_user

from ..extensions import db
from ..models.attendance import Attendance
from ..models.event import Event
from ..routes.auth import admin_required, can_access_event
from ..services.attendance_service import AttendanceService
from ..services.event_service import EventService

bp = Blueprint("attendance", __name__)


@bp.before_request
@admin_required
def protect():
    pass


def _serialize(r):
    return {
        "id": r.id,
        "event_id": r.event_id,
        "member_id": r.member_id,
        "present": r.present,
        "marked_by": r.marked_by,
        "recorded_at": r.recorded_at.isoformat(),
    }


@bp.get("/")
def list_attendance():
    event_id = request.args.get("event_id", type=int)
    member_id = request.args.get("member_id", type=int)

    if not current_user.is_superuser:
        if event_id is not None:
            event = db.session.get(Event, event_id)
            if not event or not can_access_event(current_user, event):
                return jsonify({"error": "Not authorized for this event"}), 403
        else:
            # Ordinary admins see only records for their assigned events.
            assigned_ids = {e.id for e in EventService.get_for_user(current_user)}
            if not assigned_ids:
                return jsonify([])
            stmt = db.select(Attendance).where(Attendance.event_id.in_(assigned_ids))
            if member_id is not None:
                stmt = stmt.where(Attendance.member_id == member_id)
            return jsonify([_serialize(r) for r in db.session.execute(stmt).scalars().all()])

    records = AttendanceService.get_all(event_id=event_id, member_id=member_id)
    return jsonify([_serialize(r) for r in records])


@bp.get("/event/<int:event_id>/status")
def event_attendance_status(event_id: int):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": f"Event {event_id} not found"}), 404
    if not can_access_event(current_user, event):
        return jsonify({"error": "Not authorized for this event"}), 403
    status, error = AttendanceService.get_event_status(event_id)
    if error:
        return jsonify({"error": error}), 404
    return jsonify(status)


@bp.post("/")
def record_attendance():
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    member_id = data.get("member_id")
    present = data.get("present", False)

    if not event_id:
        return jsonify({"error": "event_id is required"}), 400
    if not member_id:
        return jsonify({"error": "member_id is required"}), 400

    try:
        event_id = int(event_id)
        member_id = int(member_id)
    except (TypeError, ValueError):
        return jsonify({"error": "event_id and member_id must be integers"}), 400

    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": f"Event {event_id} not found"}), 400
    if not can_access_event(current_user, event):
        return jsonify({"error": "Not authorized for this event"}), 403

    record, error = AttendanceService.record(event_id=event_id, member_id=member_id, present=bool(present), marked_by=current_user.id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "id": record.id,
        "event_id": record.event_id,
        "member_id": record.member_id,
        "present": record.present,
        "marked_by": record.marked_by,
    }), 201


@bp.put("/<int:attendance_id>")
def update_attendance(attendance_id: int):
    data = request.get_json(silent=True) or {}
    if "present" not in data:
        return jsonify({"error": "present is required"}), 400

    record = db.session.get(Attendance, attendance_id)
    if not record:
        return jsonify({"error": "Attendance record not found"}), 404
    event = db.session.get(Event, record.event_id)
    if not can_access_event(current_user, event):
        return jsonify({"error": "Not authorized for this event"}), 403

    record, error = AttendanceService.update(attendance_id, present=bool(data["present"]))
    if error == "Event is archived":
        return jsonify({"error": error}), 409
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"id": record.id, "event_id": record.event_id, "member_id": record.member_id, "present": record.present})


@bp.delete("/<int:attendance_id>")
def delete_attendance(attendance_id: int):
    record = db.session.get(Attendance, attendance_id)
    if not record:
        return jsonify({"error": "Attendance record not found"}), 404
    event = db.session.get(Event, record.event_id)
    if not can_access_event(current_user, event):
        return jsonify({"error": "Not authorized for this event"}), 403

    deleted, error = AttendanceService.delete(attendance_id)
    if error == "Event is archived":
        return jsonify({"error": error}), 409
    if error:
        return jsonify({"error": error}), 400
    return "", 204

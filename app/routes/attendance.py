from flask import Blueprint, jsonify, request
from flask_login import current_user

from ..routes.auth import admin_required
from ..services.attendance_service import AttendanceService

bp = Blueprint("attendance", __name__)


@bp.before_request
@admin_required
def protect():
    pass


@bp.get("/")
def list_attendance():
    event_id = request.args.get("event_id", type=int)
    member_id = request.args.get("member_id", type=int)
    records = AttendanceService.get_all(event_id=event_id, member_id=member_id)
    return jsonify([
        {
            "id": r.id,
            "event_id": r.event_id,
            "member_id": r.member_id,
            "present": r.present,
            "marked_by": r.marked_by,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in records
    ])


@bp.get("/event/<int:event_id>/status")
def event_attendance_status(event_id: int):
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

    record = AttendanceService.update(attendance_id, present=bool(data["present"]))
    if not record:
        return jsonify({"error": "Attendance record not found"}), 404
    return jsonify({"id": record.id, "event_id": record.event_id, "member_id": record.member_id, "present": record.present})


@bp.delete("/<int:attendance_id>")
def delete_attendance(attendance_id: int):
    deleted = AttendanceService.delete(attendance_id)
    if not deleted:
        return jsonify({"error": "Attendance record not found"}), 404
    return "", 204

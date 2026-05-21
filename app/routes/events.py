from datetime import datetime

from flask import Blueprint, jsonify, request

from ..routes.auth import admin_required, superuser_required
from ..services.event_service import EventService

bp = Blueprint("events", __name__)


@bp.before_request
@admin_required
def protect():
    pass


@bp.get("/")
def list_events():
    group_id = request.args.get("group_id", type=int)
    events = EventService.get_all(group_id=group_id)
    return jsonify([
        {
            "id": e.id,
            "name": e.name,
            "date": e.date.isoformat(),
            "group_id": e.group_id,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ])


@bp.post("/")
def create_event():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    date_str = data.get("date")
    group_id = data.get("group_id")

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not date_str:
        return jsonify({"error": "date is required (ISO 8601)"}), 400
    if not group_id:
        return jsonify({"error": "group_id is required"}), 400

    try:
        date = datetime.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "date must be a valid ISO 8601 string"}), 400

    event, error = EventService.create(name=name, date=date, group_id=group_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({"id": event.id, "name": event.name, "date": event.date.isoformat(), "group_id": event.group_id}), 201


@bp.get("/<int:event_id>")
def get_event(event_id: int):
    event = EventService.get_by_id(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify({"id": event.id, "name": event.name, "date": event.date.isoformat(), "group_id": event.group_id})


@bp.put("/<int:event_id>")
def update_event(event_id: int):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip() or None
    date_str = data.get("date")
    date = None

    if date_str is not None:
        try:
            date = datetime.fromisoformat(date_str)
        except ValueError:
            return jsonify({"error": "date must be a valid ISO 8601 string"}), 400

    if name is None and date is None:
        return jsonify({"error": "provide name and/or date"}), 400

    event, error = EventService.update(event_id, name=name, date=date)
    if error == "Event not found":
        return jsonify({"error": error}), 404
    if error:
        return jsonify({"error": error}), 400

    return jsonify({"id": event.id, "name": event.name, "date": event.date.isoformat(), "group_id": event.group_id})


@bp.delete("/<int:event_id>")
@superuser_required
def delete_event(event_id: int):
    deleted = EventService.delete(event_id)
    if not deleted:
        return jsonify({"error": "Event not found"}), 404
    return "", 204

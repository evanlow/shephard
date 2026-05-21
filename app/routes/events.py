from datetime import datetime

from flask import Blueprint, jsonify, request

from ..routes.auth import admin_required, superuser_required
from ..services.event_service import EventService

bp = Blueprint("events", __name__)


@bp.before_request
@admin_required
def protect():
    pass


def _event_dict(e):
    return {
        "id": e.id,
        "name": e.name,
        "date": e.date.isoformat(),
        "group_id": e.group_id,
        "created_at": e.created_at.isoformat(),
        "is_archived": e.is_archived,
    }


@bp.get("/")
def list_events():
    group_id = request.args.get("group_id", type=int)
    archived_param = request.args.get("archived")
    if archived_param == "true":
        archived = True
    elif archived_param == "false":
        archived = False
    else:
        archived = None
    events = EventService.get_all(group_id=group_id, archived=archived)
    return jsonify([_event_dict(e) for e in events])


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

    return jsonify(_event_dict(event)), 201


@bp.get("/<int:event_id>")
def get_event(event_id: int):
    event = EventService.get_by_id(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(_event_dict(event))


@bp.put("/<int:event_id>")
def update_event(event_id: int):
    data = request.get_json(silent=True) or {}
    name = None
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name cannot be blank"}), 400

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
    if error == EventService.ERROR_EVENT_NOT_FOUND:
        return jsonify({"error": error}), 404
    if error == EventService.ERROR_EVENT_ARCHIVED:
        return jsonify({"error": error}), 409
    if error:
        return jsonify({"error": error}), 400

    return jsonify(_event_dict(event))


@bp.delete("/<int:event_id>")
@superuser_required
def delete_event(event_id: int):
    deleted, error = EventService.delete(event_id)
    if error == EventService.ERROR_EVENT_NOT_FOUND:
        return jsonify({"error": error}), 404
    if error == EventService.ERROR_EVENT_NOT_ARCHIVED:
        return jsonify({"error": error}), 409
    if error:
        return jsonify({"error": error}), 400
    return "", 204


@bp.post("/<int:event_id>/archive")
@superuser_required
def archive_event(event_id: int):
    event, error = EventService.archive(event_id)
    if error == EventService.ERROR_EVENT_NOT_FOUND:
        return jsonify({"error": error}), 404
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_event_dict(event))


@bp.post("/<int:event_id>/unarchive")
@superuser_required
def unarchive_event(event_id: int):
    event, error = EventService.unarchive(event_id)
    if error == EventService.ERROR_EVENT_NOT_FOUND:
        return jsonify({"error": error}), 404
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_event_dict(event))

from flask import Blueprint, jsonify, request

from ..routes.auth import admin_required, superuser_required
from ..services.group_service import GroupService

bp = Blueprint("groups", __name__)


@bp.before_request
@admin_required
def protect():
    pass


@bp.get("/")
def list_groups():
    groups = GroupService.get_all()
    return jsonify([
        {"id": g.id, "name": g.name, "description": g.description, "created_at": g.created_at.isoformat()}
        for g in groups
    ])


@bp.post("/")
def create_group():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    group = GroupService.create(name=name, description=data.get("description"))
    return jsonify({"id": group.id, "name": group.name, "description": group.description}), 201


@bp.get("/<int:group_id>")
def get_group(group_id: int):
    group = GroupService.get_by_id(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    return jsonify({"id": group.id, "name": group.name, "description": group.description, "created_at": group.created_at.isoformat()})


@bp.put("/<int:group_id>")
def update_group(group_id: int):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip() or None
    group = GroupService.update(group_id, name=name, description=data.get("description"))
    if not group:
        return jsonify({"error": "Group not found"}), 404
    return jsonify({"id": group.id, "name": group.name, "description": group.description})


@bp.delete("/<int:group_id>")
@superuser_required
def delete_group(group_id: int):
    deleted = GroupService.delete(group_id)
    if not deleted:
        return jsonify({"error": "Group not found"}), 404
    return "", 204

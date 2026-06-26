from flask import Blueprint, jsonify, request

from ..routes.auth import admin_required, superuser_required
from ..services.member_service import MemberService

bp = Blueprint("members", __name__)


@bp.before_request
@admin_required
def protect():
    pass


def _parse_group_ids(data: dict) -> list[int] | None:
    if "group_ids" in data:
        raw_group_ids = data.get("group_ids") or []
        if isinstance(raw_group_ids, list):
            return [int(group_id) for group_id in raw_group_ids if group_id not in (None, "")]
        return [int(raw_group_ids)] if raw_group_ids not in (None, "") else []
    return None


def _member_to_dict(m, include_created_at: bool = True) -> dict:
    data = {
        "id": m.id,
        "name": m.name,
        "group_id": m.group_id,
        "group_ids": [g.id for g in m.groups],
        "groups": [{"id": g.id, "name": g.name} for g in m.groups],
        "remarks": m.remarks,
        "deactivation_reason": m.deactivation_reason,
        "deactivated_at": m.deactivated_at.isoformat() if m.deactivated_at else None,
    }
    if include_created_at:
        data["created_at"] = m.created_at.isoformat()
    return data


@bp.get("/")
def list_members():
    members = MemberService.get_all()
    return jsonify([_member_to_dict(m) for m in members])


@bp.post("/")
def create_member():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    group_id = data.get("group_id")
    group_ids = _parse_group_ids(data)
    remarks = data.get("remarks")
    if not name:
        return jsonify({"error": "name is required"}), 400

    member, error = MemberService.create(
        name=name, group_ids=group_ids, group_id=group_id, remarks=remarks,
    )
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_member_to_dict(member, include_created_at=False)), 201


@bp.get("/<int:member_id>")
def get_member(member_id: int):
    member = MemberService.get_by_id(member_id)
    if not member:
        return jsonify({"error": "Member not found"}), 404
    return jsonify(_member_to_dict(member))


@bp.put("/<int:member_id>")
def update_member(member_id: int):
    data = request.get_json(silent=True) or {}
    name = ((data.get("name") or "").strip()) or None
    group_id = data.get("group_id") if "group_id" in data else None
    group_ids = _parse_group_ids(data)
    groups_provided = group_ids is not None or "group_id" in data
    remarks_provided = "remarks" in data
    remarks = data.get("remarks") if remarks_provided else None
    if not name and not groups_provided and not remarks_provided:
        return jsonify({"error": "provide name, group_id(s), and/or remarks"}), 400

    member, error = MemberService.update(
        member_id,
        name=name,
        group_ids=group_ids,
        group_id=group_id,
        groups_provided=groups_provided,
        remarks=remarks,
        remarks_provided=remarks_provided,
    )
    if error == "Member not found":
        return jsonify({"error": error}), 404
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_member_to_dict(member, include_created_at=False))


@bp.delete("/<int:member_id>")
@superuser_required
def delete_member(member_id: int):
    deleted = MemberService.delete(member_id)
    if not deleted:
        return jsonify({"error": "Member not found"}), 404
    return "", 204

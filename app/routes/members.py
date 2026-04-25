from flask import Blueprint, jsonify, request
from flask_login import login_required

from ..services.member_service import MemberService

bp = Blueprint("members", __name__)


@bp.before_request
@login_required
def protect():
    pass


@bp.get("/")
def list_members():
    members = MemberService.get_all()
    return jsonify([{"id": m.id, "name": m.name, "created_at": m.created_at.isoformat()} for m in members])


@bp.post("/")
def create_member():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    member = MemberService.create(name=name)
    return jsonify({"id": member.id, "name": member.name}), 201


@bp.get("/<int:member_id>")
def get_member(member_id: int):
    member = MemberService.get_by_id(member_id)
    if not member:
        return jsonify({"error": "Member not found"}), 404
    return jsonify({"id": member.id, "name": member.name, "created_at": member.created_at.isoformat()})


@bp.put("/<int:member_id>")
def update_member(member_id: int):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    member = MemberService.update(member_id, name=name)
    if not member:
        return jsonify({"error": "Member not found"}), 404
    return jsonify({"id": member.id, "name": member.name})


@bp.delete("/<int:member_id>")
def delete_member(member_id: int):
    deleted = MemberService.delete(member_id)
    if not deleted:
        return jsonify({"error": "Member not found"}), 404
    return "", 204

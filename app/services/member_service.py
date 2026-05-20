from __future__ import annotations

from ..extensions import db
from ..models.group import Group
from ..models.member import Member
from .group_service import GroupService


def _resolve_membership(
    group_ids: list[int] | None,
    primary_group_id: int | None,
) -> tuple[Group, list[Group] | None, str | None]:
    default_group = GroupService.get_default_group()
    resolved_groups: list[Group] = []
    seen_ids = {default_group.id}
    primary_group = default_group

    candidate_ids = list(group_ids or [])
    if primary_group_id is not None:
        candidate_ids.insert(0, primary_group_id)

    if candidate_ids:
        first_group = db.session.get(Group, int(candidate_ids[0]))
        if not first_group:
            return default_group, None, f"Group {candidate_ids[0]} not found"
        primary_group = first_group
        if first_group.id not in seen_ids:
            resolved_groups.append(first_group)
            seen_ids.add(first_group.id)

        for raw_group_id in candidate_ids[1:]:
            if raw_group_id is None:
                continue
            group = db.session.get(Group, int(raw_group_id))
            if not group:
                return default_group, None, f"Group {raw_group_id} not found"
            if group.id not in seen_ids:
                resolved_groups.append(group)
                seen_ids.add(group.id)

    return primary_group, [default_group, *resolved_groups], None


class MemberService:
    @staticmethod
    def get_all() -> list[Member]:
        return db.session.execute(db.select(Member).order_by(Member.name)).scalars().all()

    @staticmethod
    def get_by_id(member_id: int) -> Member | None:
        return db.session.get(Member, member_id)

    @staticmethod
    def create(
        name: str,
        group_ids: list[int] | None = None,
        group_id: int | None = None,
    ) -> tuple[Member | None, str | None]:
        primary_group, groups, error = _resolve_membership(group_ids, group_id)
        if error:
            return None, error

        member = Member(name=name, group_id=primary_group.id)
        member.groups = groups or []
        db.session.add(member)
        db.session.commit()
        return member, None

    @staticmethod
    def update(
        member_id: int,
        name: str | None = None,
        group_ids: list[int] | None = None,
        group_id: int | None = None,
        groups_provided: bool = False,
    ) -> tuple[Member | None, str | None]:
        member = db.session.get(Member, member_id)
        if not member:
            return None, "Member not found"

        if name:
            member.name = name

        if groups_provided:
            primary_group, groups, error = _resolve_membership(group_ids, group_id)
            if error:
                return None, error
            member.group_id = primary_group.id
            member.groups = groups or []

        db.session.commit()
        return member, None

    @staticmethod
    def delete(member_id: int) -> bool:
        member = db.session.get(Member, member_id)
        if not member:
            return False
        db.session.delete(member)
        db.session.commit()
        return True

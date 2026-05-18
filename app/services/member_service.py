from __future__ import annotations

from ..extensions import db
from ..models.group import Group
from ..models.member import Member


class MemberService:
    @staticmethod
    def get_all() -> list[Member]:
        return db.session.execute(db.select(Member).order_by(Member.name)).scalars().all()

    @staticmethod
    def get_by_id(member_id: int) -> Member | None:
        return db.session.get(Member, member_id)

    @staticmethod
    def create(name: str, group_id: int | None = None) -> tuple[Member | None, str | None]:
        if group_id is not None and not db.session.get(Group, group_id):
            return None, f"Group {group_id} not found"

        member = Member(name=name, group_id=group_id)
        db.session.add(member)
        db.session.commit()
        return member, None

    @staticmethod
    def update(
        member_id: int,
        name: str | None = None,
        group_id: int | None = None,
        group_id_provided: bool = False,
    ) -> tuple[Member | None, str | None]:
        member = db.session.get(Member, member_id)
        if not member:
            return None, "Member not found"

        if name:
            member.name = name
        if group_id_provided:
            if group_id is not None and not db.session.get(Group, group_id):
                return None, f"Group {group_id} not found"
            member.group_id = group_id

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

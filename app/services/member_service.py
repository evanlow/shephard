from __future__ import annotations

from ..extensions import db
from ..models.member import Member


class MemberService:
    @staticmethod
    def get_all() -> list[Member]:
        return db.session.execute(db.select(Member).order_by(Member.name)).scalars().all()

    @staticmethod
    def get_by_id(member_id: int) -> Member | None:
        return db.session.get(Member, member_id)

    @staticmethod
    def create(name: str) -> Member:
        member = Member(name=name)
        db.session.add(member)
        db.session.commit()
        return member

    @staticmethod
    def update(member_id: int, name: str) -> Member | None:
        member = db.session.get(Member, member_id)
        if not member:
            return None
        member.name = name
        db.session.commit()
        return member

    @staticmethod
    def delete(member_id: int) -> bool:
        member = db.session.get(Member, member_id)
        if not member:
            return False
        db.session.delete(member)
        db.session.commit()
        return True

from __future__ import annotations

from ..extensions import db
from ..models.group import Group
from ..models.member import Member
from ..models.membership import DEFAULT_GROUP_NAME


class GroupService:
    @staticmethod
    def get_default_group() -> Group:
        group = db.session.execute(
            db.select(Group).where(Group.name == DEFAULT_GROUP_NAME)
        ).scalar_one_or_none()
        if group:
            return group

        group = Group(name=DEFAULT_GROUP_NAME)
        db.session.add(group)
        db.session.flush()
        return group

    @staticmethod
    def ensure_default_group() -> Group:
        group = GroupService.get_default_group()
        db.session.commit()
        return group

    @staticmethod
    def get_all() -> list[Group]:
        return db.session.execute(db.select(Group).order_by(Group.name)).scalars().all()

    @staticmethod
    def get_by_id(group_id: int) -> Group | None:
        return db.session.get(Group, group_id)

    @staticmethod
    def create(name: str, description: str | None = None) -> Group:
        group = Group(name=name, description=description)
        db.session.add(group)
        db.session.commit()
        return group

    @staticmethod
    def update(group_id: int, name: str | None = None, description: str | None = None) -> Group | None:
        group = db.session.get(Group, group_id)
        if not group:
            return None
        if name:
            group.name = name
        if description is not None:
            group.description = description
        db.session.commit()
        return group

    @staticmethod
    def delete(group_id: int) -> bool:
        group = db.session.get(Group, group_id)
        if not group:
            return False
        if group.name == DEFAULT_GROUP_NAME:
            return False
        default_group = GroupService.get_default_group()
        members = db.session.execute(
            db.select(Member).where(Member.group_id == group_id)
        ).scalars().all()
        for member in members:
            member.group_id = default_group.id
        db.session.delete(group)
        db.session.commit()
        return True

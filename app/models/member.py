from datetime import datetime, timezone

from sqlalchemy import event, text

from ..extensions import db
from .membership import DEFAULT_GROUP_NAME, member_groups


class Member(db.Model):
    """A church member who can be tracked for attendance."""

    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    group = db.relationship("Group", foreign_keys=[group_id], back_populates="primary_members")
    groups = db.relationship("Group", secondary=member_groups, back_populates="members", order_by="Group.name")
    attendance_records = db.relationship("Attendance", back_populates="member", cascade="all, delete-orphan")

    @property
    def default_group(self):
        for group in self.groups:
            if group.name == DEFAULT_GROUP_NAME:
                return group
        return self.groups[0] if self.groups else None

    def __repr__(self) -> str:
        return f"<Member {self.name}>"


@event.listens_for(Member, "after_insert")
def ensure_default_memberships(mapper, connection, target):
    """Add default and primary memberships for direct Member inserts."""

    if target.groups:
        return

    default_group_id = connection.execute(
        text("SELECT id FROM groups WHERE name = :name LIMIT 1"),
        {"name": DEFAULT_GROUP_NAME},
    ).scalar_one_or_none()
    if default_group_id is None:
        return

    memberships = [{"member_id": target.id, "group_id": default_group_id}]
    if target.group_id is not None:
        memberships.append({"member_id": target.id, "group_id": target.group_id})

    connection.execute(member_groups.insert(), memberships)

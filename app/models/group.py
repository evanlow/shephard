from datetime import datetime, timezone

from ..extensions import db
from .membership import member_groups


class Group(db.Model):
    """A ministry group, e.g. Worship Service, Sunday School."""

    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    events = db.relationship("Event", back_populates="group", cascade="all, delete-orphan")
    members = db.relationship("Member", secondary=member_groups, back_populates="groups", order_by="Member.name")
    primary_members = db.relationship("Member", foreign_keys="Member.group_id", back_populates="group")

    def __repr__(self) -> str:
        return f"<Group {self.name}>"

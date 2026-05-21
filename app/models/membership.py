from datetime import datetime

from ..extensions import db


DEFAULT_GROUP_NAME = "ALL MEMBERS"


member_groups = db.Table(
    "member_groups",
    db.Column("member_id", db.Integer, db.ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    db.Column("joined_at", db.DateTime, nullable=False, default=datetime.utcnow),
)
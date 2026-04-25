from datetime import datetime, timezone

from ..extensions import db


class Member(db.Model):
    """A church member who can be tracked for attendance."""

    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    attendance_records = db.relationship("Attendance", back_populates="member", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Member {self.name}>"

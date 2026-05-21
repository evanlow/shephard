from datetime import datetime, timezone

from ..extensions import db


class Event(db.Model):
    """A scheduled service or gathering, e.g. 3 May 2026 8AM Service."""

    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_archived = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    group = db.relationship("Group", back_populates="events")
    attendance_records = db.relationship("Attendance", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Event {self.name} on {self.date}>"

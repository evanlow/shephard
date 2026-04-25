from datetime import datetime, timezone

from ..extensions import db


class Attendance(db.Model):
    """Records whether a member was present at an event."""

    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint("event_id", "member_id", name="uq_attendance_event_member"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    present = db.Column(db.Boolean, nullable=False, default=False)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = db.relationship("Event", back_populates="attendance_records")
    member = db.relationship("Member", back_populates="attendance_records")

    def __repr__(self) -> str:
        return f"<Attendance event={self.event_id} member={self.member_id} present={self.present}>"

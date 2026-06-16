from datetime import datetime, timezone

from ..extensions import db


class EventAdmin(db.Model):
    """Assignment of an ordinary admin to a specific event.

    Superusers always have global access and do not need a row here.
    Only users with is_admin=True and is_superuser=False are valid assignees.
    """

    __tablename__ = "event_admins"

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    assigned_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<EventAdmin event={self.event_id} user={self.user_id}>"

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models.attendance import Attendance
from ..models.event import Event
from ..models.member import Member


class AttendanceService:
    @staticmethod
    def get_all(event_id: int | None = None, member_id: int | None = None) -> list[Attendance]:
        stmt = db.select(Attendance)
        if event_id is not None:
            stmt = stmt.where(Attendance.event_id == event_id)
        if member_id is not None:
            stmt = stmt.where(Attendance.member_id == member_id)
        return db.session.execute(stmt).scalars().all()

    @staticmethod
    def record(event_id: int, member_id: int, present: bool) -> tuple[Attendance | None, str | None]:
        if not db.session.get(Event, event_id):
            return None, f"Event {event_id} not found"
        if not db.session.get(Member, member_id):
            return None, f"Member {member_id} not found"

        record = Attendance(event_id=event_id, member_id=member_id, present=present)
        db.session.add(record)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None, "Attendance already recorded for this member and event"
        return record, None

    @staticmethod
    def update(attendance_id: int, present: bool) -> Attendance | None:
        record = db.session.get(Attendance, attendance_id)
        if not record:
            return None
        record.present = present
        db.session.commit()
        return record

    @staticmethod
    def delete(attendance_id: int) -> bool:
        record = db.session.get(Attendance, attendance_id)
        if not record:
            return False
        db.session.delete(record)
        db.session.commit()
        return True

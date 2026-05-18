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
        event = db.session.get(Event, event_id)
        if not event:
            return None, f"Event {event_id} not found"
        member = db.session.get(Member, member_id)
        if not member:
            return None, f"Member {member_id} not found"
        if member.group_id != event.group_id:
            return None, "Member is not assigned to this event's group"

        record = Attendance(event_id=event_id, member_id=member_id, present=present)
        db.session.add(record)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None, "Attendance already recorded for this member and event"
        return record, None

    @staticmethod
    def get_event_status(event_id: int) -> tuple[dict | None, str | None]:
        event = db.session.get(Event, event_id)
        if not event:
            return None, f"Event {event_id} not found"

        expected_members = db.session.execute(
            db.select(Member).where(Member.group_id == event.group_id).order_by(Member.name)
        ).scalars().all()
        expected_member_ids = {m.id for m in expected_members}

        present_member_ids = set(
            db.session.execute(
                db.select(Attendance.member_id).where(
                    Attendance.event_id == event_id,
                    Attendance.present.is_(True),
                    Attendance.member_id.in_(expected_member_ids),
                )
            ).scalars().all()
        )

        present_members = [m for m in expected_members if m.id in present_member_ids]
        absent_members = [m for m in expected_members if m.id not in present_member_ids]

        return {
            "event_id": event.id,
            "event_name": event.name,
            "group_id": event.group_id,
            "expected_count": len(expected_members),
            "present_count": len(present_members),
            "absent_count": len(absent_members),
            "expected_members": [{"id": m.id, "name": m.name} for m in expected_members],
            "present_members": [{"id": m.id, "name": m.name} for m in present_members],
            "absent_members": [{"id": m.id, "name": m.name} for m in absent_members],
        }, None

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

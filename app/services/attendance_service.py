from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models.attendance import Attendance
from ..models.event import Event
from ..models.member import Member
from ..models.membership import member_groups


class AttendanceService:
    @staticmethod
    def get_all(event_id: int | None = None, member_id: int | None = None) -> list[Attendance]:
        """Return all attendance records, optionally filtered by event and/or member."""
        stmt = db.select(Attendance)
        if event_id is not None:
            stmt = stmt.where(Attendance.event_id == event_id)
        if member_id is not None:
            stmt = stmt.where(Attendance.member_id == member_id)
        return db.session.execute(stmt).scalars().all()

    @staticmethod
    def record(event_id: int, member_id: int, present: bool, marked_by: int | None = None) -> tuple[Attendance | None, str | None]:
        """Create a new attendance record.

        Returns (record, None) on success or (None, error_message) on failure.
        Fails if the event or member does not exist, if the member is not in the
        event's group, if the event is archived, or if a record already exists.
        """
        event = db.session.get(Event, event_id)
        if not event:
            return None, f"Event {event_id} not found"
        if event.is_archived:
            return None, "Event is archived"
        member = db.session.get(Member, member_id)
        if not member:
            return None, f"Member {member_id} not found"
        if event.group not in member.groups:
            return None, "Member is not assigned to this event's group"

        record = Attendance(event_id=event_id, member_id=member_id, present=present, marked_by=marked_by)
        db.session.add(record)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None, "Attendance already recorded for this member and event"
        return record, None

    @staticmethod
    def get_event_status(event_id: int) -> tuple[dict | None, str | None]:
        """Return expected/present/absent breakdown for an event.

        Only members who joined the event's group on or before the event date
        and were not deactivated before that date are counted as expected
        attendees. Returns (status_dict, None) on success or
        (None, error_message) if the event does not exist.
        """
        event = db.session.get(Event, event_id)
        if not event:
            return None, f"Event {event_id} not found"

        expected_members = list(event.group.members)
        expected_members.sort(key=lambda member: member.name)
        expected_member_ids = {m.id for m in expected_members}

        # Only include members who were assigned to this group on or before the event date
        # and were not yet deactivated by that date.
        eligible_ids = set(
            db.session.execute(
                db.select(member_groups.c.member_id).where(
                    member_groups.c.group_id == event.group_id,
                    member_groups.c.joined_at <= event.date,
                )
            ).scalars().all()
        )
        expected_members = [
            m for m in expected_members
            if m.id in eligible_ids
            and (m.deactivated_at is None or m.deactivated_at > event.date)
        ]
        expected_member_ids = {m.id for m in expected_members}

        present_records = db.session.execute(
            db.select(Attendance).where(
                Attendance.event_id == event_id,
                Attendance.present.is_(True),
                Attendance.member_id.in_(expected_member_ids),
            )
        ).scalars().all()
        present_attendance_by_member = {r.member_id: r for r in present_records}
        present_member_ids = set(present_attendance_by_member.keys())

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
            "present_members": [
                {"id": m.id, "name": m.name, "attendance_id": present_attendance_by_member[m.id].id}
                for m in present_members
            ],
            "absent_members": [{"id": m.id, "name": m.name} for m in absent_members],
        }, None

    @staticmethod
    def update(attendance_id: int, present: bool) -> tuple[Attendance | None, str | None]:
        """Update the present flag on an existing attendance record.

        Returns (record, None) on success or (None, error_message) on failure.
        Fails if the record does not exist or its event is archived.
        """
        record = db.session.get(Attendance, attendance_id)
        if not record:
            return None, "Attendance record not found"
        event = db.session.get(Event, record.event_id)
        if event and event.is_archived:
            return None, "Event is archived"
        record.present = present
        db.session.commit()
        return record, None

    @staticmethod
    def delete(attendance_id: int) -> tuple[bool, str | None]:
        """Delete an attendance record.

        Returns (True, None) on success or (False, error_message) on failure.
        Fails if the record does not exist or its event is archived.
        """
        record = db.session.get(Attendance, attendance_id)
        if not record:
            return False, "Attendance record not found"
        event = db.session.get(Event, record.event_id)
        if event and event.is_archived:
            return False, "Event is archived"
        db.session.delete(record)
        db.session.commit()
        return True, None

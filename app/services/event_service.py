from __future__ import annotations

from datetime import datetime

from ..extensions import db
from ..models.event import Event
from ..models.group import Group


class EventService:
    ERROR_EVENT_NOT_FOUND = "Event not found"
    ERROR_NO_FIELDS_TO_UPDATE = "provide name and/or date"

    @staticmethod
    def get_all(group_id: int | None = None) -> list[Event]:
        stmt = db.select(Event).order_by(Event.date.desc())
        if group_id is not None:
            stmt = stmt.where(Event.group_id == group_id)
        return db.session.execute(stmt).scalars().all()

    @staticmethod
    def get_by_id(event_id: int) -> Event | None:
        return db.session.get(Event, event_id)

    @staticmethod
    def create(name: str, date: datetime, group_id: int) -> tuple[Event | None, str | None]:
        group = db.session.get(Group, group_id)
        if not group:
            return None, f"Group {group_id} not found"
        event = Event(name=name, date=date, group_id=group_id)
        db.session.add(event)
        db.session.commit()
        return event, None

    @staticmethod
    def update(event_id: int, name: str | None = None, date: datetime | None = None) -> tuple[Event | None, str | None]:
        if name is None and date is None:
            return None, EventService.ERROR_NO_FIELDS_TO_UPDATE

        event = db.session.get(Event, event_id)
        if not event:
            return None, EventService.ERROR_EVENT_NOT_FOUND
        if name is not None:
            event.name = name
        if date is not None:
            event.date = date
        db.session.commit()
        return event, None

    @staticmethod
    def delete(event_id: int) -> bool:
        event = db.session.get(Event, event_id)
        if not event:
            return False
        db.session.delete(event)
        db.session.commit()
        return True

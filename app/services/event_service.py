from __future__ import annotations

from datetime import datetime

from ..extensions import db
from ..models.event import Event
from ..models.group import Group


class EventService:
    ERROR_EVENT_NOT_FOUND = "Event not found"
    ERROR_NO_FIELDS_TO_UPDATE = "provide name and/or date"
    ERROR_EVENT_ARCHIVED = "Event is archived"
    ERROR_EVENT_NOT_ARCHIVED = "Event must be archived before it can be deleted"

    @staticmethod
    def get_all(group_id: int | None = None, archived: bool | None = None) -> list[Event]:
        stmt = db.select(Event).order_by(Event.date.desc())
        if group_id is not None:
            stmt = stmt.where(Event.group_id == group_id)
        if archived is None:
            stmt = stmt.where(Event.is_archived.is_(False))
        else:
            stmt = stmt.where(Event.is_archived.is_(archived))
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
        if event.is_archived:
            return None, EventService.ERROR_EVENT_ARCHIVED
        if name is not None:
            event.name = name
        if date is not None:
            event.date = date
        db.session.commit()
        return event, None

    @staticmethod
    def delete(event_id: int) -> tuple[bool, str | None]:
        event = db.session.get(Event, event_id)
        if not event:
            return False, EventService.ERROR_EVENT_NOT_FOUND
        if not event.is_archived:
            return False, EventService.ERROR_EVENT_NOT_ARCHIVED
        db.session.delete(event)
        db.session.commit()
        return True, None

    @staticmethod
    def archive(event_id: int) -> tuple[Event | None, str | None]:
        event = db.session.get(Event, event_id)
        if not event:
            return None, EventService.ERROR_EVENT_NOT_FOUND
        event.is_archived = True
        db.session.commit()
        return event, None

    @staticmethod
    def unarchive(event_id: int) -> tuple[Event | None, str | None]:
        event = db.session.get(Event, event_id)
        if not event:
            return None, EventService.ERROR_EVENT_NOT_FOUND
        event.is_archived = False
        db.session.commit()
        return event, None

"""Smoke tests for app/services/event_service.py

Tests EventService methods directly (no HTTP layer).
Events require a Group, which is created in setUp.
"""

import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.group import Group
from app.services.event_service import EventService

FUTURE_DATE = datetime(2026, 12, 25, 10, 0)


def _make_app():
    return create_app("testing")


class TestEventService(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.commit()
        self.group_id = group.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_get_all_returns_empty_list(self):
        self.assertEqual(EventService.get_all(), [])

    def test_create_returns_event(self):
        event, error = EventService.create(
            name="Christmas Service", date=FUTURE_DATE, group_id=self.group_id
        )
        self.assertIsNone(error)
        self.assertIsNotNone(event.id)
        self.assertEqual(event.name, "Christmas Service")
        self.assertEqual(event.group_id, self.group_id)

    def test_create_invalid_group_returns_error(self):
        event, error = EventService.create(
            name="Orphan Event", date=FUTURE_DATE, group_id=9999
        )
        self.assertIsNone(event)
        self.assertIsNotNone(error)
        self.assertIn("9999", error)

    def test_create_persists_to_db(self):
        EventService.create(name="Test Event", date=FUTURE_DATE, group_id=self.group_id)
        self.assertEqual(len(EventService.get_all()), 1)

    def test_get_all_filtered_by_group(self):
        # Create a second group
        other_group = Group(name="Other Group")
        db.session.add(other_group)
        db.session.commit()

        EventService.create(name="My Group Event", date=FUTURE_DATE, group_id=self.group_id)
        EventService.create(name="Other Group Event", date=FUTURE_DATE, group_id=other_group.id)

        results = EventService.get_all(group_id=self.group_id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "My Group Event")

    def test_get_by_id_returns_event(self):
        event, _ = EventService.create(name="Fetch Me", date=FUTURE_DATE, group_id=self.group_id)
        fetched = EventService.get_by_id(event.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Fetch Me")

    def test_get_by_id_returns_none_for_missing(self):
        self.assertIsNone(EventService.get_by_id(9999))

    def test_delete_removes_event(self):
        event, _ = EventService.create(name="To Delete", date=FUTURE_DATE, group_id=self.group_id)
        EventService.archive(event.id)
        result, error = EventService.delete(event.id)
        self.assertTrue(result)
        self.assertIsNone(error)
        self.assertIsNone(EventService.get_by_id(event.id))

    def test_delete_returns_false_for_missing(self):
        deleted, error = EventService.delete(9999)
        self.assertFalse(deleted)
        self.assertIsNotNone(error)

    def test_get_all_returns_most_recent_first(self):
        EventService.create(
            name="Earlier", date=datetime(2026, 1, 1), group_id=self.group_id
        )
        EventService.create(
            name="Later", date=datetime(2026, 12, 1), group_id=self.group_id
        )
        events = EventService.get_all()
        self.assertEqual(events[0].name, "Later")
        self.assertEqual(events[1].name, "Earlier")

    def test_update_name(self):
        event, _ = EventService.create(name="Old Name", date=FUTURE_DATE, group_id=self.group_id)
        updated, error = EventService.update(event.id, name="New Name")
        self.assertIsNone(error)
        self.assertEqual(updated.name, "New Name")
        self.assertEqual(updated.date, FUTURE_DATE)

    def test_update_date(self):
        event, _ = EventService.create(name="My Event", date=FUTURE_DATE, group_id=self.group_id)
        new_date = datetime(2027, 3, 15, 9, 30)
        updated, error = EventService.update(event.id, date=new_date)
        self.assertIsNone(error)
        self.assertEqual(updated.date, new_date)
        self.assertEqual(updated.name, "My Event")

    def test_update_name_and_date(self):
        event, _ = EventService.create(name="Original", date=FUTURE_DATE, group_id=self.group_id)
        new_date = datetime(2027, 6, 1, 10, 0)
        updated, error = EventService.update(event.id, name="Updated", date=new_date)
        self.assertIsNone(error)
        self.assertEqual(updated.name, "Updated")
        self.assertEqual(updated.date, new_date)

    def test_update_not_found_returns_error(self):
        result, error = EventService.update(9999, name="Ghost")
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("not found", error.lower())

    def test_update_no_fields_returns_error(self):
        event, _ = EventService.create(name="Noop", date=FUTURE_DATE, group_id=self.group_id)
        result, error = EventService.update(event.id)
        self.assertIsNone(result)
        self.assertEqual(error, EventService.ERROR_NO_FIELDS_TO_UPDATE)

    def test_archive_sets_is_archived(self):
        event, _ = EventService.create(name="Archivable", date=FUTURE_DATE, group_id=self.group_id)
        self.assertFalse(event.is_archived)
        archived, error = EventService.archive(event.id)
        self.assertIsNone(error)
        self.assertTrue(archived.is_archived)

    def test_archive_not_found_returns_error(self):
        result, error = EventService.archive(9999)
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("not found", error.lower())

    def test_unarchive_clears_is_archived(self):
        event, _ = EventService.create(name="Re-open", date=FUTURE_DATE, group_id=self.group_id)
        EventService.archive(event.id)
        unarchived, error = EventService.unarchive(event.id)
        self.assertIsNone(error)
        self.assertFalse(unarchived.is_archived)

    def test_unarchive_not_found_returns_error(self):
        result, error = EventService.unarchive(9999)
        self.assertIsNone(result)
        self.assertIsNotNone(error)

    def test_update_archived_event_returns_error(self):
        event, _ = EventService.create(name="Locked", date=FUTURE_DATE, group_id=self.group_id)
        EventService.archive(event.id)
        result, error = EventService.update(event.id, name="Changed")
        self.assertIsNone(result)
        self.assertEqual(error, EventService.ERROR_EVENT_ARCHIVED)

    def test_delete_non_archived_event_returns_error(self):
        event, _ = EventService.create(name="Live Event", date=FUTURE_DATE, group_id=self.group_id)
        deleted, error = EventService.delete(event.id)
        self.assertFalse(deleted)
        self.assertEqual(error, EventService.ERROR_EVENT_NOT_ARCHIVED)

    def test_get_all_default_excludes_archived(self):
        EventService.create(name="Active", date=FUTURE_DATE, group_id=self.group_id)
        event2, _ = EventService.create(name="Archived", date=FUTURE_DATE, group_id=self.group_id)
        EventService.archive(event2.id)
        results = EventService.get_all()
        names = [e.name for e in results]
        self.assertIn("Active", names)
        self.assertNotIn("Archived", names)

    def test_get_all_archived_true_returns_only_archived(self):
        EventService.create(name="Active", date=FUTURE_DATE, group_id=self.group_id)
        event2, _ = EventService.create(name="Archived", date=FUTURE_DATE, group_id=self.group_id)
        EventService.archive(event2.id)
        results = EventService.get_all(archived=True)
        names = [e.name for e in results]
        self.assertNotIn("Active", names)
        self.assertIn("Archived", names)

    def test_unarchive_allows_update_again(self):
        event, _ = EventService.create(name="Temp Locked", date=FUTURE_DATE, group_id=self.group_id)
        EventService.archive(event.id)
        EventService.unarchive(event.id)
        updated, error = EventService.update(event.id, name="Re-opened")
        self.assertIsNone(error)
        self.assertEqual(updated.name, "Re-opened")


if __name__ == "__main__":
    unittest.main()

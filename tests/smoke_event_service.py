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
        result = EventService.delete(event.id)
        self.assertTrue(result)
        self.assertIsNone(EventService.get_by_id(event.id))

    def test_delete_returns_false_for_missing(self):
        self.assertFalse(EventService.delete(9999))

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


if __name__ == "__main__":
    unittest.main()

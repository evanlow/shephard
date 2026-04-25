"""Smoke tests for app/services/attendance_service.py

Tests AttendanceService methods directly (no HTTP layer).
Requires an Event and a Member, both created in setUp.
"""

import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.group import Group
from app.models.event import Event
from app.models.member import Member
from app.services.attendance_service import AttendanceService


def _make_app():
    return create_app("testing")


class TestAttendanceService(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        group = Group(name="Test Group")
        db.session.add(group)
        db.session.flush()

        event = Event(name="Test Event", date=datetime(2026, 6, 1, 10, 0), group_id=group.id)
        db.session.add(event)

        member = Member(name="Test Member")
        db.session.add(member)

        db.session.commit()
        self.event_id = event.id
        self.member_id = member.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_get_all_returns_empty_list(self):
        self.assertEqual(AttendanceService.get_all(), [])

    def test_record_returns_attendance(self):
        record, error = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        self.assertIsNone(error)
        self.assertIsNotNone(record.id)
        self.assertEqual(record.event_id, self.event_id)
        self.assertEqual(record.member_id, self.member_id)
        self.assertTrue(record.present)

    def test_record_absent(self):
        record, error = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=False
        )
        self.assertIsNone(error)
        self.assertFalse(record.present)

    def test_record_invalid_event_returns_error(self):
        record, error = AttendanceService.record(
            event_id=9999, member_id=self.member_id, present=True
        )
        self.assertIsNone(record)
        self.assertIsNotNone(error)

    def test_record_invalid_member_returns_error(self):
        record, error = AttendanceService.record(
            event_id=self.event_id, member_id=9999, present=True
        )
        self.assertIsNone(record)
        self.assertIsNotNone(error)

    def test_duplicate_record_returns_error(self):
        AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        record, error = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=False
        )
        self.assertIsNone(record)
        self.assertIsNotNone(error)

    def test_get_all_filtered_by_event(self):
        AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        results = AttendanceService.get_all(event_id=self.event_id)
        self.assertEqual(len(results), 1)

    def test_get_all_filtered_by_member(self):
        AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        results = AttendanceService.get_all(member_id=self.member_id)
        self.assertEqual(len(results), 1)

    def test_update_changes_present_flag(self):
        record, _ = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        updated = AttendanceService.update(record.id, present=False)
        self.assertIsNotNone(updated)
        self.assertFalse(updated.present)

    def test_update_returns_none_for_missing(self):
        self.assertIsNone(AttendanceService.update(9999, present=True))

    def test_delete_removes_record(self):
        record, _ = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        result = AttendanceService.delete(record.id)
        self.assertTrue(result)
        self.assertEqual(AttendanceService.get_all(), [])

    def test_delete_returns_false_for_missing(self):
        self.assertFalse(AttendanceService.delete(9999))


if __name__ == "__main__":
    unittest.main()

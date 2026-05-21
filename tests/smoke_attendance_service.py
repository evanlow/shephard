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
from app.services.event_service import EventService


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

        member = Member(name="Test Member", group_id=group.id)
        db.session.add(member)

        db.session.commit()
        self.event_id = event.id
        self.member_id = member.id
        self.group_id = group.id

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
        updated, error = AttendanceService.update(record.id, present=False)
        self.assertIsNone(error)
        self.assertIsNotNone(updated)
        self.assertFalse(updated.present)

    def test_update_returns_none_for_missing(self):
        result, error = AttendanceService.update(9999, present=True)
        self.assertIsNone(result)
        self.assertIsNotNone(error)

    def test_delete_removes_record(self):
        record, _ = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        deleted, error = AttendanceService.delete(record.id)
        self.assertTrue(deleted)
        self.assertIsNone(error)
        self.assertEqual(AttendanceService.get_all(), [])

    def test_delete_returns_false_for_missing(self):
        deleted, error = AttendanceService.delete(9999)
        self.assertFalse(deleted)
        self.assertIsNotNone(error)

    def test_record_member_not_in_event_group_returns_error(self):
        other_group = Group(name="Other Group")
        db.session.add(other_group)
        db.session.flush()
        outsider = Member(name="Outsider", group_id=other_group.id)
        db.session.add(outsider)
        db.session.commit()

        record, error = AttendanceService.record(
            event_id=self.event_id, member_id=outsider.id, present=True
        )
        self.assertIsNone(record)
        self.assertIsNotNone(error)

    def test_get_event_status_expected_present_absent(self):
        second_member = Member(name="Second Member", group_id=self.group_id)
        db.session.add(second_member)
        db.session.commit()
        AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )

        status, error = AttendanceService.get_event_status(self.event_id)
        self.assertIsNone(error)
        self.assertEqual(status["expected_count"], 2)
        self.assertEqual(status["present_count"], 1)
        self.assertEqual(status["absent_count"], 1)

    def test_get_event_status_excludes_member_who_joined_after_event(self):
        """A member added to the group after the event date must not appear in the report."""
        past_event = Event(name="Past Event", date=datetime(2020, 1, 1, 10, 0), group_id=self.group_id)
        db.session.add(past_event)
        db.session.commit()

        # Member created now (2026) — joined_at is after the 2020 event date
        late_member = Member(name="Late Joiner", group_id=self.group_id)
        db.session.add(late_member)
        db.session.commit()

        status, error = AttendanceService.get_event_status(past_event.id)
        self.assertIsNone(error)
        member_ids = [m["id"] for m in status["expected_members"]]
        self.assertNotIn(late_member.id, member_ids)

    def test_get_event_status_includes_member_who_joined_before_event(self):
        """A member added before the event date must appear in the report."""
        status, error = AttendanceService.get_event_status(self.event_id)
        self.assertIsNone(error)
        member_ids = [m["id"] for m in status["expected_members"]]
        self.assertIn(self.member_id, member_ids)

    def test_record_blocked_for_archived_event(self):
        EventService.archive(self.event_id)
        record, error = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        self.assertIsNone(record)
        self.assertIsNotNone(error)
        self.assertIn("archived", error.lower())

    def test_update_blocked_for_archived_event(self):
        record, _ = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        EventService.archive(self.event_id)
        result, error = AttendanceService.update(record.id, present=False)
        self.assertIsNone(result)
        self.assertIn("archived", error.lower())

    def test_delete_blocked_for_archived_event(self):
        record, _ = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        EventService.archive(self.event_id)
        deleted, error = AttendanceService.delete(record.id)
        self.assertFalse(deleted)
        self.assertIn("archived", error.lower())

    def test_unarchive_allows_record_again(self):
        EventService.archive(self.event_id)
        EventService.unarchive(self.event_id)
        record, error = AttendanceService.record(
            event_id=self.event_id, member_id=self.member_id, present=True
        )
        self.assertIsNone(error)
        self.assertIsNotNone(record)


if __name__ == "__main__":
    unittest.main()

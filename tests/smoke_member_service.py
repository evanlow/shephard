"""Smoke tests for app/services/member_service.py

Tests MemberService methods directly (no HTTP layer).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.services.member_service import MemberService


def _make_app():
    return create_app("testing")


class TestMemberService(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_get_all_returns_empty_list(self):
        result = MemberService.get_all()
        self.assertEqual(result, [])

    def test_create_returns_member(self):
        member = MemberService.create(name="Alice")
        self.assertIsNotNone(member.id)
        self.assertEqual(member.name, "Alice")

    def test_create_persists_to_db(self):
        MemberService.create(name="Bob")
        all_members = MemberService.get_all()
        self.assertEqual(len(all_members), 1)
        self.assertEqual(all_members[0].name, "Bob")

    def test_get_by_id_returns_member(self):
        created = MemberService.create(name="Carol")
        fetched = MemberService.get_by_id(created.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Carol")

    def test_get_by_id_returns_none_for_missing(self):
        result = MemberService.get_by_id(9999)
        self.assertIsNone(result)

    def test_update_changes_name(self):
        member = MemberService.create(name="Old Name")
        updated = MemberService.update(member.id, name="New Name")
        self.assertEqual(updated.name, "New Name")

    def test_update_returns_none_for_missing(self):
        result = MemberService.update(9999, name="Nobody")
        self.assertIsNone(result)

    def test_delete_removes_member(self):
        member = MemberService.create(name="Dave")
        result = MemberService.delete(member.id)
        self.assertTrue(result)
        self.assertIsNone(MemberService.get_by_id(member.id))

    def test_delete_returns_false_for_missing(self):
        result = MemberService.delete(9999)
        self.assertFalse(result)

    def test_get_all_returns_members_alphabetically(self):
        MemberService.create(name="Zara")
        MemberService.create(name="Alice")
        MemberService.create(name="Mike")
        names = [m.name for m in MemberService.get_all()]
        self.assertEqual(names, sorted(names))


if __name__ == "__main__":
    unittest.main()

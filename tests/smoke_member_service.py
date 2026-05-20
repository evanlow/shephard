"""Smoke tests for app/services/member_service.py

Tests MemberService methods directly (no HTTP layer).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.group import Group
from app.services.group_service import GroupService
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
        member, error = MemberService.create(name="Alice")
        self.assertIsNone(error)
        self.assertIsNotNone(member.id)
        self.assertEqual(member.name, "Alice")

    def test_create_persists_to_db(self):
        MemberService.create(name="Bob")
        all_members = MemberService.get_all()
        self.assertEqual(len(all_members), 1)
        self.assertEqual(all_members[0].name, "Bob")

    def test_get_by_id_returns_member(self):
        created, _ = MemberService.create(name="Carol")
        fetched = MemberService.get_by_id(created.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Carol")

    def test_get_by_id_returns_none_for_missing(self):
        result = MemberService.get_by_id(9999)
        self.assertIsNone(result)

    def test_update_changes_name(self):
        member, _ = MemberService.create(name="Old Name")
        updated, error = MemberService.update(member.id, name="New Name")
        self.assertIsNone(error)
        self.assertEqual(updated.name, "New Name")

    def test_update_returns_none_for_missing(self):
        result, error = MemberService.update(9999, name="Nobody")
        self.assertIsNone(result)
        self.assertEqual(error, "Member not found")

    def test_delete_removes_member(self):
        member, _ = MemberService.create(name="Dave")
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

    def test_create_with_group_assignment(self):
        group = Group(name="Worship")
        db.session.add(group)
        db.session.commit()
        member, error = MemberService.create(name="Assigned", group_id=group.id)
        self.assertIsNone(error)
        self.assertEqual(member.group_id, group.id)

    def test_create_invalid_group_returns_error(self):
        member, error = MemberService.create(name="Bad Group", group_id=9999)
        self.assertIsNone(member)
        self.assertIsNotNone(error)

    def test_create_with_multiple_groups_dedupes_and_preserves_default(self):
        g1 = Group(name="Music")
        g2 = Group(name="Choir")
        db.session.add_all([g1, g2])
        db.session.commit()

        member, error = MemberService.create(
            name="Multi",
            group_id=g1.id,
            group_ids=[g1.id, None, g2.id, g1.id],
        )
        self.assertIsNone(error)
        self.assertEqual(member.group_id, g1.id)
        names = {group.name for group in member.groups}
        self.assertIn("ALL MEMBERS", names)
        self.assertIn("Music", names)
        self.assertIn("Choir", names)

    def test_create_invalid_secondary_group_returns_error(self):
        g1 = Group(name="Primary")
        db.session.add(g1)
        db.session.commit()

        member, error = MemberService.create(
            name="Bad Secondary",
            group_ids=[g1.id, 999999],
        )
        self.assertIsNone(member)
        self.assertIn("not found", error)

    def test_update_with_invalid_group_returns_error(self):
        member, _ = MemberService.create(name="Updatable")
        updated, error = MemberService.update(
            member.id,
            group_ids=[999999],
            groups_provided=True,
        )
        self.assertIsNone(updated)
        self.assertIn("not found", error)

    def test_create_with_default_group_as_primary(self):
        default_group = GroupService.get_default_group()
        member, error = MemberService.create(name="Default Primary", group_id=default_group.id)
        self.assertIsNone(error)
        self.assertEqual(member.group_id, default_group.id)


if __name__ == "__main__":
    unittest.main()

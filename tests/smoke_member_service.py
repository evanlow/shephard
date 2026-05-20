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

    # ------------------------------------------------------------------
    # Multi-group membership
    # ------------------------------------------------------------------

    def test_create_auto_enrolls_in_all_members_group(self):
        member, error = MemberService.create(name="Auto Enrolled")
        self.assertIsNone(error)
        group_names = [g.name for g in member.groups]
        self.assertIn("ALL MEMBERS", group_names)

    def test_create_with_group_id_enrolls_in_primary_and_all_members(self):
        group = Group(name="Worship")
        db.session.add(group)
        db.session.commit()
        member, error = MemberService.create(name="Dual Member", group_id=group.id)
        self.assertIsNone(error)
        group_names = [g.name for g in member.groups]
        self.assertIn("ALL MEMBERS", group_names)
        self.assertIn("Worship", group_names)

    def test_create_with_group_ids_enrolls_in_all_specified_groups(self):
        group1 = Group(name="Youth")
        group2 = Group(name="Choir")
        db.session.add_all([group1, group2])
        db.session.commit()
        member, error = MemberService.create(
            name="Multi Member", group_ids=[group1.id, group2.id]
        )
        self.assertIsNone(error)
        group_names = [g.name for g in member.groups]
        self.assertIn("ALL MEMBERS", group_names)
        self.assertIn("Youth", group_names)
        self.assertIn("Choir", group_names)

    def test_create_with_invalid_group_ids_returns_error(self):
        member, error = MemberService.create(name="Bad Groups", group_ids=[9999])
        self.assertIsNone(member)
        self.assertIsNotNone(error)

    def test_update_with_group_ids_updates_memberships(self):
        group = Group(name="New Group")
        db.session.add(group)
        db.session.commit()
        member, _ = MemberService.create(name="To Update")
        updated, error = MemberService.update(
            member.id, group_ids=[group.id], groups_provided=True
        )
        self.assertIsNone(error)
        group_names = [g.name for g in updated.groups]
        self.assertIn("ALL MEMBERS", group_names)
        self.assertIn("New Group", group_names)

    def test_update_with_invalid_group_ids_returns_error(self):
        member, _ = MemberService.create(name="To Update Bad")
        result, error = MemberService.update(
            member.id, group_ids=[9999], groups_provided=True
        )
        self.assertIsNone(result)
        self.assertIsNotNone(error)

    def test_member_default_group_property_returns_all_members(self):
        member, _ = MemberService.create(name="Default Prop Test")
        default = member.default_group
        self.assertIsNotNone(default)
        self.assertEqual(default.name, "ALL MEMBERS")


if __name__ == "__main__":
    unittest.main()

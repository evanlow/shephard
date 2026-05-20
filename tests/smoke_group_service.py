"""Smoke tests for app/services/group_service.py

Tests GroupService methods directly (no HTTP layer).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.member import Member
from app.services.group_service import GroupService


def _make_app():
    return create_app("testing")


class TestGroupService(unittest.TestCase):
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
        groups = GroupService.get_all()
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].name, "ALL MEMBERS")

    def test_create_returns_group_with_id(self):
        group = GroupService.create(name="Worship")
        self.assertIsNotNone(group.id)
        self.assertEqual(group.name, "Worship")
        self.assertIsNone(group.description)

    def test_create_with_description(self):
        group = GroupService.create(name="Youth", description="Youth ministry")
        self.assertEqual(group.description, "Youth ministry")

    def test_create_persists_to_db(self):
        GroupService.create(name="Bible Study")
        self.assertEqual(len(GroupService.get_all()), 2)

    def test_get_by_id_returns_group(self):
        created = GroupService.create(name="Choir")
        fetched = GroupService.get_by_id(created.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Choir")

    def test_get_by_id_returns_none_for_missing(self):
        self.assertIsNone(GroupService.get_by_id(9999))

    def test_update_changes_name(self):
        group = GroupService.create(name="Old Name")
        updated = GroupService.update(group.id, name="New Name")
        self.assertEqual(updated.name, "New Name")

    def test_update_changes_description(self):
        group = GroupService.create(name="Test", description="Old desc")
        updated = GroupService.update(group.id, description="New desc")
        self.assertEqual(updated.description, "New desc")

    def test_update_returns_none_for_missing(self):
        self.assertIsNone(GroupService.update(9999, name="Nobody"))

    def test_delete_removes_group(self):
        group = GroupService.create(name="To Delete")
        result = GroupService.delete(group.id)
        self.assertTrue(result)
        self.assertIsNone(GroupService.get_by_id(group.id))

    def test_delete_returns_false_for_missing(self):
        self.assertFalse(GroupService.delete(9999))

    def test_delete_unassigns_members_before_group_removal(self):
        group = GroupService.create(name="Member Group")
        member = Member(name="Alice", group_id=group.id)
        db.session.add(member)
        db.session.commit()

        default_group = GroupService.get_default_group()
        self.assertTrue(GroupService.delete(group.id))
        db.session.refresh(member)
        self.assertEqual(member.group_id, default_group.id)

    def test_get_all_returns_groups_alphabetically(self):
        GroupService.create(name="Zion")
        GroupService.create(name="Alpha")
        GroupService.create(name="Mission")
        names = [g.name for g in GroupService.get_all()]
        self.assertEqual(names, sorted(names))


if __name__ == "__main__":
    unittest.main()

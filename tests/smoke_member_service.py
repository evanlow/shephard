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

    # ------------------------------------------------------------------
    # Deactivate / reactivate
    # ------------------------------------------------------------------

    def test_deactivate_sets_deactivated_at(self):
        from datetime import datetime
        member, _ = MemberService.create(name="Leaver")
        cutoff = datetime(2026, 5, 31, 23, 59, 59)
        updated, error = MemberService.deactivate(member.id, cutoff, deactivation_reason="Moved overseas")
        self.assertIsNone(error)
        self.assertIsNotNone(updated.deactivated_at)
        self.assertEqual(updated.deactivation_reason, "Moved overseas")

    def test_deactivate_requires_reason(self):
        from datetime import datetime
        member, _ = MemberService.create(name="No Reason")
        cutoff = datetime(2026, 5, 31, 23, 59, 59)
        _, error = MemberService.deactivate(member.id, cutoff)
        self.assertEqual(error, "Deactivation reason is required")
        _, error = MemberService.deactivate(member.id, cutoff, deactivation_reason="   ")
        self.assertEqual(error, "Deactivation reason is required")

    def test_deactivate_already_inactive_returns_error(self):
        from datetime import datetime
        member, _ = MemberService.create(name="Gone")
        MemberService.deactivate(member.id, datetime(2026, 5, 31, 23, 59, 59), deactivation_reason="Moved")
        _, error = MemberService.deactivate(member.id, datetime(2026, 6, 30, 23, 59, 59), deactivation_reason="Moved")
        self.assertIsNotNone(error)

    def test_deactivate_unknown_member_returns_error(self):
        from datetime import datetime
        _, error = MemberService.deactivate(9999, datetime(2026, 5, 31, 23, 59, 59), deactivation_reason="Moved")
        self.assertIsNotNone(error)

    def test_reactivate_clears_deactivated_at(self):
        from datetime import datetime
        member, _ = MemberService.create(name="Returning")
        MemberService.deactivate(member.id, datetime(2026, 5, 31, 23, 59, 59), deactivation_reason="Moved")
        updated, error = MemberService.reactivate(member.id, datetime(2026, 9, 1))
        self.assertIsNone(error)
        db.session.expire(updated)
        refreshed = MemberService.get_by_id(member.id)
        self.assertIsNone(refreshed.deactivated_at)
        self.assertIsNone(refreshed.deactivation_reason)

    def test_reactivate_preserves_remarks(self):
        from datetime import datetime
        member, _ = MemberService.create(name="Notes Kept", remarks="Husband of Mary")
        MemberService.deactivate(member.id, datetime(2026, 5, 31, 23, 59, 59), deactivation_reason="Moved")
        MemberService.reactivate(member.id, datetime(2026, 9, 1))
        refreshed = MemberService.get_by_id(member.id)
        self.assertEqual(refreshed.remarks, "Husband of Mary")

    def test_reactivate_updates_joined_at_to_rejoin_date(self):
        from datetime import datetime
        from app.extensions import db as _db
        from app.models.membership import member_groups as mg
        member, _ = MemberService.create(name="Coming Back")
        MemberService.deactivate(member.id, datetime(2026, 5, 31, 23, 59, 59), deactivation_reason="Moved")
        rejoin = datetime(2026, 9, 1)
        MemberService.reactivate(member.id, rejoin)
        rows = _db.session.execute(
            _db.select(mg.c.joined_at).where(mg.c.member_id == member.id)
        ).scalars().all()
        for joined_at in rows:
            self.assertEqual(str(joined_at)[:10], "2026-09-01")

    def test_reactivate_already_active_returns_error(self):
        from datetime import datetime
        member, _ = MemberService.create(name="Active Guy")
        _, error = MemberService.reactivate(member.id, datetime(2026, 9, 1))
        self.assertIsNotNone(error)

    def test_reactivate_unknown_member_returns_error(self):
        from datetime import datetime
        _, error = MemberService.reactivate(9999, datetime(2026, 9, 1))
        self.assertIsNotNone(error)

    # ------------------------------------------------------------------
    # Remarks
    # ------------------------------------------------------------------

    def test_create_with_remarks_persists(self):
        member, error = MemberService.create(name="Noted", remarks="  Long-time member  ")
        self.assertIsNone(error)
        self.assertEqual(member.remarks, "Long-time member")

    def test_create_with_blank_remarks_stores_none(self):
        member, _ = MemberService.create(name="No Remark", remarks="   ")
        self.assertIsNone(member.remarks)

    def test_create_with_too_long_remarks_returns_error(self):
        member, error = MemberService.create(name="Too Long", remarks="x" * 501)
        self.assertIsNone(member)
        self.assertIn("characters", error)

    def test_update_remarks(self):
        member, _ = MemberService.create(name="Edit Me", remarks="initial")
        updated, error = MemberService.update(member.id, remarks="updated", remarks_provided=True)
        self.assertIsNone(error)
        self.assertEqual(updated.remarks, "updated")

    def test_update_can_clear_remarks(self):
        member, _ = MemberService.create(name="Clear Me", remarks="initial")
        updated, _ = MemberService.update(member.id, remarks="", remarks_provided=True)
        self.assertIsNone(updated.remarks)


if __name__ == "__main__":
    unittest.main()

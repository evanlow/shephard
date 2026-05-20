"""Smoke tests for model-level logic branches and repr coverage."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.attendance import Attendance
from app.models.event import Event
from app.models.group import Group
from app.models.member import Member
from app.models.user import User


def _make_app():
    return create_app("testing")


class TestModelBehaviors(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_repr_methods(self):
        group = Group(name="Worship")
        db.session.add(group)
        db.session.flush()

        member = Member(name="Alice", group_id=group.id)
        member.groups.append(group)
        db.session.add(member)
        db.session.flush()

        event = Event(name="Service", date=db.func.now(), group_id=group.id)
        db.session.add(event)
        db.session.flush()

        attendance = Attendance(event_id=event.id, member_id=member.id, present=True)
        db.session.add(attendance)

        user = User(username="admin", email="admin@test.com", is_admin=True, is_superuser=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        self.assertIn("Group", repr(group))
        self.assertIn("Member", repr(member))
        self.assertIn("Event", repr(event))
        self.assertIn("Attendance", repr(attendance))
        self.assertIn("User", repr(user))

    def test_member_default_group_prefers_all_members(self):
        default_group = db.session.execute(
            db.select(Group).where(Group.name == "ALL MEMBERS")
        ).scalar_one()
        choir = Group(name="Choir")
        db.session.add(choir)
        db.session.commit()

        member = Member(name="Default Preferred", group_id=choir.id)
        member.groups.extend([choir, default_group])
        db.session.add(member)
        db.session.commit()

        self.assertEqual(member.default_group.name, "ALL MEMBERS")

    def test_member_default_group_falls_back_to_first_non_default(self):
        team = Group(name="Tech Team")
        db.session.add(team)
        db.session.commit()

        member = Member(name="Fallback", group_id=team.id)
        member.groups.append(team)
        db.session.add(member)
        db.session.commit()

        self.assertEqual(member.default_group.name, "Tech Team")

    def test_after_insert_listener_no_default_group_present(self):
        # Remove all groups so listener path where default group is missing is exercised.
        db.session.execute(db.delete(Group))
        db.session.commit()

        member = Member(name="No Default Group")
        db.session.add(member)
        db.session.commit()
        db.session.refresh(member)

        self.assertEqual(member.groups, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
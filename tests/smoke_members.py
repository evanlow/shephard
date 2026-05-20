"""Smoke tests for app/routes/members.py

Covers: 401 without auth, list/create/get/update/delete with auth.
"""

import json
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.group import Group
from app.models.user import User


def _make_app():
    return create_app("testing")


def _create_and_login(client):
    user = User(username="admin", email="admin@test.com", is_superuser=True)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    client.post("/login", data={"username": "admin", "password": "password123"})


class TestMembersRouteAuth(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/members/")
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertIn("error", data)


class TestMembersCRUD(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_and_login(self.client)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_list_members_returns_empty_list(self):
        resp = self.client.get("/api/members/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data), [])

    def test_create_member_returns_201(self):
        resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Alice Smith"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertEqual(data["name"], "Alice Smith")
        self.assertIsNotNone(data["group_id"])
        self.assertIn("id", data)

    def test_create_member_no_name_returns_400(self):
        resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": ""}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_member_no_body_returns_400(self):
        resp = self.client.post("/api/members/", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_get_member_returns_200(self):
        create_resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Bob Jones"}),
            content_type="application/json",
        )
        member_id = json.loads(create_resp.data)["id"]

        resp = self.client.get(f"/api/members/{member_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)["name"], "Bob Jones")

    def test_create_member_with_group_assignment(self):
        group = Group(name="Worship")
        db.session.add(group)
        db.session.commit()
        resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Assigned Member", "group_id": group.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(json.loads(resp.data)["group_id"], group.id)

    def test_get_member_not_found_returns_404(self):
        resp = self.client.get("/api/members/9999")
        self.assertEqual(resp.status_code, 404)

    def test_update_member_returns_200(self):
        create_resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Carol White"}),
            content_type="application/json",
        )
        member_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/members/{member_id}",
            data=json.dumps({"name": "Carol Black"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)["name"], "Carol Black")

    def test_update_member_group_assignment_only_returns_200(self):
        group = Group(name="Youth")
        db.session.add(group)
        db.session.commit()

        create_resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Member To Assign"}),
            content_type="application/json",
        )
        member_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/members/{member_id}",
            data=json.dumps({"group_id": group.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)["group_id"], group.id)

    def test_update_member_not_found_returns_404(self):
        resp = self.client.put(
            "/api/members/9999",
            data=json.dumps({"name": "Nobody"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_member_returns_204(self):
        create_resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Dave Green"}),
            content_type="application/json",
        )
        member_id = json.loads(create_resp.data)["id"]

        resp = self.client.delete(f"/api/members/{member_id}")
        self.assertEqual(resp.status_code, 204)

        # Confirm gone
        get_resp = self.client.get(f"/api/members/{member_id}")
        self.assertEqual(get_resp.status_code, 404)

    def test_delete_member_not_found_returns_404(self):
        resp = self.client.delete("/api/members/9999")
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------
    # Multi-group response fields
    # ------------------------------------------------------------------

    def test_list_members_response_includes_groups_fields(self):
        self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Test Member"}),
            content_type="application/json",
        )
        resp = self.client.get("/api/members/")
        self.assertEqual(resp.status_code, 200)
        members = json.loads(resp.data)
        self.assertEqual(len(members), 1)
        self.assertIn("group_ids", members[0])
        self.assertIn("groups", members[0])
        self.assertIsInstance(members[0]["group_ids"], list)
        self.assertIsInstance(members[0]["groups"], list)

    def test_get_member_response_includes_groups_fields(self):
        create_resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Checked Member"}),
            content_type="application/json",
        )
        member_id = json.loads(create_resp.data)["id"]
        resp = self.client.get(f"/api/members/{member_id}")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("group_ids", data)
        self.assertIn("groups", data)
        self.assertIsInstance(data["group_ids"], list)
        self.assertIsInstance(data["groups"], list)

    def test_create_member_auto_enrolled_in_all_members(self):
        resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Auto Enrolled"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        group_names = [g["name"] for g in data["groups"]]
        self.assertIn("ALL MEMBERS", group_names)

    def test_create_member_with_group_ids_assigns_multiple_groups(self):
        group_resp = self.client.post(
            "/api/groups/",
            data=json.dumps({"name": "Youth"}),
            content_type="application/json",
        )
        group_id = json.loads(group_resp.data)["id"]

        resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Multi Group Member", "group_ids": [group_id]}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        group_names = [g["name"] for g in data["groups"]]
        self.assertIn("ALL MEMBERS", group_names)
        self.assertIn("Youth", group_names)
        self.assertIn(group_id, data["group_ids"])

    def test_update_member_with_group_ids_assigns_multiple_groups(self):
        group_resp = self.client.post(
            "/api/groups/",
            data=json.dumps({"name": "Choir"}),
            content_type="application/json",
        )
        group_id = json.loads(group_resp.data)["id"]

        create_resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Group Updater"}),
            content_type="application/json",
        )
        member_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/members/{member_id}",
            data=json.dumps({"group_ids": [group_id]}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        group_names = [g["name"] for g in data["groups"]]
        self.assertIn("ALL MEMBERS", group_names)
        self.assertIn("Choir", group_names)

    def test_update_member_with_invalid_group_ids_returns_400(self):
        create_resp = self.client.post(
            "/api/members/",
            data=json.dumps({"name": "Bad Updater"}),
            content_type="application/json",
        )
        member_id = json.loads(create_resp.data)["id"]
        resp = self.client.put(
            f"/api/members/{member_id}",
            data=json.dumps({"group_ids": [9999]}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()

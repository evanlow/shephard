"""Smoke tests for app/routes/groups.py

Covers: 401 without auth, list/create/get/update/delete with auth.
"""

import json
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User


def _make_app():
    return create_app("testing")


def _create_and_login(client):
    user = User(username="admin", email="admin@test.com", is_superuser=True)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    client.post("/login", data={"username": "admin", "password": "password123"})


class TestGroupsRouteAuth(unittest.TestCase):
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
        resp = self.client.get("/api/groups/")
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertIn("error", data)


class TestGroupsCRUD(unittest.TestCase):
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

    def test_list_groups_returns_empty_list(self):
        resp = self.client.get("/api/groups/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data), [])

    def test_create_group_returns_201(self):
        resp = self.client.post(
            "/api/groups/",
            data=json.dumps({"name": "Worship Service", "description": "Sunday worship"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertEqual(data["name"], "Worship Service")
        self.assertEqual(data["description"], "Sunday worship")
        self.assertIn("id", data)

    def test_create_group_no_name_returns_400(self):
        resp = self.client.post(
            "/api/groups/",
            data=json.dumps({"description": "No name given"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_group_without_description(self):
        resp = self.client.post(
            "/api/groups/",
            data=json.dumps({"name": "Youth Group"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertIsNone(data["description"])

    def test_get_group_returns_200(self):
        create_resp = self.client.post(
            "/api/groups/",
            data=json.dumps({"name": "Bible Study"}),
            content_type="application/json",
        )
        group_id = json.loads(create_resp.data)["id"]

        resp = self.client.get(f"/api/groups/{group_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)["name"], "Bible Study")

    def test_get_group_not_found_returns_404(self):
        resp = self.client.get("/api/groups/9999")
        self.assertEqual(resp.status_code, 404)

    def test_update_group_returns_200(self):
        create_resp = self.client.post(
            "/api/groups/",
            data=json.dumps({"name": "Old Name"}),
            content_type="application/json",
        )
        group_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/groups/{group_id}",
            data=json.dumps({"name": "New Name", "description": "Updated"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)["name"], "New Name")

    def test_update_group_not_found_returns_404(self):
        resp = self.client.put(
            "/api/groups/9999",
            data=json.dumps({"name": "Nobody"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_group_returns_204(self):
        create_resp = self.client.post(
            "/api/groups/",
            data=json.dumps({"name": "To Delete"}),
            content_type="application/json",
        )
        group_id = json.loads(create_resp.data)["id"]

        resp = self.client.delete(f"/api/groups/{group_id}")
        self.assertEqual(resp.status_code, 204)

        get_resp = self.client.get(f"/api/groups/{group_id}")
        self.assertEqual(get_resp.status_code, 404)

    def test_delete_group_not_found_returns_404(self):
        resp = self.client.delete("/api/groups/9999")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()

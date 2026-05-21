"""Smoke tests for app/routes/events.py

Covers: 401 without auth, list/create/get/delete with auth.
Events require a valid group_id, so a group is created in setUp.
"""

import json
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.group import Group

VALID_DATE = "2026-06-01T10:00:00"


def _make_app():
    return create_app("testing")


def _create_and_login(client):
    user = User(username="admin", email="admin@test.com", is_superuser=True)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    client.post("/login", data={"username": "admin", "password": "password123"})


class TestEventsRouteAuth(unittest.TestCase):
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
        resp = self.client.get("/api/events/")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("error", json.loads(resp.data))


class TestEventsCRUD(unittest.TestCase):
    def setUp(self):
        self.app = _make_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        _create_and_login(self.client)

        # Create a group for events to belong to
        group = Group(name="Test Group")
        db.session.add(group)
        db.session.commit()
        self.group_id = group.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _create_event(self, name="Sunday Service"):
        return self.client.post(
            "/api/events/",
            data=json.dumps({"name": name, "date": VALID_DATE, "group_id": self.group_id}),
            content_type="application/json",
        )

    def test_list_events_returns_empty_list(self):
        resp = self.client.get("/api/events/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data), [])

    def test_create_event_returns_201(self):
        resp = self._create_event("Sunday Service")
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertEqual(data["name"], "Sunday Service")
        self.assertEqual(data["group_id"], self.group_id)
        self.assertIn("id", data)

    def test_create_event_no_name_returns_400(self):
        resp = self.client.post(
            "/api/events/",
            data=json.dumps({"date": VALID_DATE, "group_id": self.group_id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_event_no_date_returns_400(self):
        resp = self.client.post(
            "/api/events/",
            data=json.dumps({"name": "No Date", "group_id": self.group_id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_event_invalid_date_returns_400(self):
        resp = self.client.post(
            "/api/events/",
            data=json.dumps({"name": "Bad Date", "date": "not-a-date", "group_id": self.group_id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_event_no_group_returns_400(self):
        resp = self.client.post(
            "/api/events/",
            data=json.dumps({"name": "No Group", "date": VALID_DATE}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_event_invalid_group_returns_400(self):
        resp = self.client.post(
            "/api/events/",
            data=json.dumps({"name": "Bad Group", "date": VALID_DATE, "group_id": 9999}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_list_events_filtered_by_group(self):
        self._create_event("Event A")
        resp = self.client.get(f"/api/events/?group_id={self.group_id}")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 1)

    def test_get_event_returns_200(self):
        create_resp = self._create_event()
        event_id = json.loads(create_resp.data)["id"]

        resp = self.client.get(f"/api/events/{event_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)["name"], "Sunday Service")

    def test_get_event_not_found_returns_404(self):
        resp = self.client.get("/api/events/9999")
        self.assertEqual(resp.status_code, 404)

    def test_delete_event_returns_204(self):
        create_resp = self._create_event()
        event_id = json.loads(create_resp.data)["id"]

        resp = self.client.delete(f"/api/events/{event_id}")
        self.assertEqual(resp.status_code, 204)

        get_resp = self.client.get(f"/api/events/{event_id}")
        self.assertEqual(get_resp.status_code, 404)

    def test_delete_event_not_found_returns_404(self):
        resp = self.client.delete("/api/events/9999")
        self.assertEqual(resp.status_code, 404)

    def test_update_event_name_returns_200(self):
        create_resp = self._create_event()
        event_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/events/{event_id}",
            data=json.dumps({"name": "Updated Name"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["name"], "Updated Name")

    def test_update_event_date_returns_200(self):
        create_resp = self._create_event()
        event_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/events/{event_id}",
            data=json.dumps({"date": "2027-01-01T09:00:00"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("2027-01-01", data["date"])

    def test_update_event_invalid_date_returns_400(self):
        create_resp = self._create_event()
        event_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/events/{event_id}",
            data=json.dumps({"date": "not-a-date"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_event_blank_name_returns_400(self):
        create_resp = self._create_event()
        event_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/events/{event_id}",
            data=json.dumps({"name": "   ", "date": "2027-01-01T09:00:00"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.data)["error"], "name cannot be blank")

    def test_update_event_no_fields_returns_400(self):
        create_resp = self._create_event()
        event_id = json.loads(create_resp.data)["id"]

        resp = self.client.put(
            f"/api/events/{event_id}",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_event_not_found_returns_404(self):
        resp = self.client.put(
            "/api/events/9999",
            data=json.dumps({"name": "Ghost"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()

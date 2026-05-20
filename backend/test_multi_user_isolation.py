"""
Multi-user isolation tests - verify that users can only see, access,
and modify their own APIs, and that access to other users' APIs is rejected.
Run from the backend/ directory:
    python -m pytest test_multi_user_isolation.py -v
or:
    python test_multi_user_isolation.py
"""
import unittest

from backend.db import init_db

init_db()

from backend.app import app


class MultiUserIsolationTest(unittest.TestCase):

    def setUp(self):
        # Create separate clients for User A and User B to manage independent sessions
        self.client_a = app.test_client()
        self.client_b = app.test_client()

        self.user_a_email = "usera_test@example.com"
        self.user_b_email = "userb_test@example.com"
        self.password = "StrongPassword123!"

        # Register User A
        self.client_a.post(
            "/api/auth/register",
            json={
                "email": self.user_a_email,
                "password": self.password,
                "confirm_password": self.password,
            },
        )
        # Register User B
        self.client_b.post(
            "/api/auth/register",
            json={
                "email": self.user_b_email,
                "password": self.password,
                "confirm_password": self.password,
            },
        )

        # Login User A
        self.client_a.post(
            "/api/auth/login",
            json={"email": self.user_a_email, "password": self.password},
        )
        # Login User B
        self.client_b.post(
            "/api/auth/login",
            json={"email": self.user_b_email, "password": self.password},
        )

    def test_multi_user_isolation(self):
        # 1. User A adds an API
        res = self.client_a.post(
            "/api/add_api",
            json={
                "name": "User A API",
                "url": "https://httpbin.org/status/200",
                "interval": 60,
                "threshold": 1000,
            },
        )
        self.assertEqual(res.status_code, 201)

        # 2. User B adds an API
        res = self.client_b.post(
            "/api/add_api",
            json={
                "name": "User B API",
                "url": "https://httpbin.org/status/404",
                "interval": 30,
                "threshold": 500,
            },
        )
        self.assertEqual(res.status_code, 201)

        # 3. User A lists their APIs and should only see User A's API
        res = self.client_a.get("/api/apis")
        self.assertEqual(res.status_code, 200)
        apis_a = res.get_json()
        self.assertIsInstance(apis_a, list)
        
        # Verify only User A's API is present
        user_a_api_names = [api["name"] for api in apis_a]
        self.assertIn("User A API", user_a_api_names)
        self.assertNotIn("User B API", user_a_api_names)

        # Extract IDs
        user_a_api_id = next(api["id"] for api in apis_a if api["name"] == "User A API")

        # 4. User B lists their APIs and should only see User B's API
        res = self.client_b.get("/api/apis")
        self.assertEqual(res.status_code, 200)
        apis_b = res.get_json()
        self.assertIsInstance(apis_b, list)
        
        user_b_api_names = [api["name"] for api in apis_b]
        self.assertIn("User B API", user_b_api_names)
        self.assertNotIn("User A API", user_b_api_names)

        user_b_api_id = next(api["id"] for api in apis_b if api["name"] == "User B API")

        # 5. User A checks status; should only contain User A's API
        res = self.client_a.get("/api/get_status")
        self.assertEqual(res.status_code, 200)
        status_a = res.get_json()
        status_a_names = [item["name"] for item in status_a]
        self.assertIn("User A API", status_a_names)
        self.assertNotIn("User B API", status_a_names)

        # 6. User B checks status; should only contain User B's API
        res = self.client_b.get("/api/get_status")
        self.assertEqual(res.status_code, 200)
        status_b = res.get_json()
        status_b_names = [item["name"] for item in status_b]
        self.assertIn("User B API", status_b_names)
        self.assertNotIn("User A API", status_b_names)

        # 7. User A tries to view logs of User B's API; must be rejected (403)
        res = self.client_a.get(f"/api/logs/{user_b_api_id}")
        self.assertEqual(res.status_code, 403)

        # 8. User A tries to delete User B's API; must be rejected (403)
        res = self.client_a.delete(f"/api/delete_api/{user_b_api_id}")
        self.assertEqual(res.status_code, 403)

        # Verify User B's API is still there
        res = self.client_b.get("/api/apis")
        user_b_api_names_after_attack = [api["name"] for api in res.get_json()]
        self.assertIn("User B API", user_b_api_names_after_attack)

        # 9. User B deletes User B's API; must be successful (200)
        res = self.client_b.delete(f"/api/delete_api/{user_b_api_id}")
        self.assertEqual(res.status_code, 200)

        # Verify User B's API is now gone
        res = self.client_b.get("/api/apis")
        user_b_api_names_after_delete = [api["name"] for api in res.get_json()]
        self.assertNotIn("User B API", user_b_api_names_after_delete)


if __name__ == "__main__":
    unittest.main()

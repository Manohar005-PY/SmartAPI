"""
Auth smoke tests — verify login, registration, and protection of API routes.
Run from the backend/ directory:
    python -m pytest test_auth_smoke.py -v
or:
    python test_auth_smoke.py
"""
import unittest

from backend.db import init_db

init_db()

from backend.app import app


class AuthSmokeTest(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    # ------------------------------------------------------------------
    # Protected routes require authentication
    # ------------------------------------------------------------------

    def test_protected_route_requires_authentication(self):
        response = self.client.get("/api/get_status")
        self.assertEqual(response.status_code, 401)

    def test_protected_apis_list_requires_authentication(self):
        response = self.client.get("/api/apis")
        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def test_seeded_user_can_log_in_and_access_dashboard_data(self):
        response = self.client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "Admin@123"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["user"]["email"], "admin@example.com")

        status_response = self.client.get("/api/get_status")
        self.assertEqual(status_response.status_code, 200)
        self.assertIsInstance(status_response.get_json(), list)

    def test_invalid_password_is_rejected(self):
        response = self.client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 401)

    def test_missing_fields_rejected_on_login(self):
        response = self.client.post("/api/auth/login", json={"email": "admin@example.com"})
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def test_new_user_can_register(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "newuser_smoke@example.com",
                "password": "StrongPass1!",
                "confirm_password": "StrongPass1!",
            },
        )
        # 201 on success, or 409 if already seeded from a previous run
        self.assertIn(response.status_code, (201, 409))

    def test_register_duplicate_email_returns_409(self):
        # Register once
        self.client.post(
            "/api/auth/register",
            json={
                "email": "dup_smoke@example.com",
                "password": "StrongPass1!",
                "confirm_password": "StrongPass1!",
            },
        )
        # Try again — must get 409
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "dup_smoke@example.com",
                "password": "StrongPass1!",
                "confirm_password": "StrongPass1!",
            },
        )
        self.assertEqual(response.status_code, 409)

    def test_register_mismatched_passwords_returns_400(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "mismatch_smoke@example.com",
                "password": "StrongPass1!",
                "confirm_password": "Different1!",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_register_short_password_returns_400(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "shortpw_smoke@example.com",
                "password": "abc",
                "confirm_password": "abc",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_register_invalid_email_returns_400(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "StrongPass1!",
                "confirm_password": "StrongPass1!",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_registered_user_can_log_in(self):
        email = "login_after_reg_smoke@example.com"
        password = "ValidPass99!"

        # Register (ignore if already exists)
        self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "confirm_password": password},
        )

        # Now log in with a fresh client (no existing session cookie)
        with app.test_client() as fresh_client:
            response = fresh_client.post(
                "/api/auth/login",
                json={"email": email, "password": password},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["user"]["email"], email)

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def test_logout_clears_session(self):
        # Log in
        self.client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "Admin@123"},
        )
        # Verify authenticated
        self.assertEqual(self.client.get("/api/get_status").status_code, 200)
        # Logout
        self.client.post("/api/auth/logout")
        # Should now be unauthenticated
        self.assertEqual(self.client.get("/api/get_status").status_code, 401)


if __name__ == "__main__":
    unittest.main()

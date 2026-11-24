import os
import secrets
import unittest
from unittest.mock import patch

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.password = secrets.token_hex(24)
        env = patch.dict(os.environ, ADMIN_USERNAME="tester", ADMIN_PASSWORD=self.password,
                         JWT_SECRET_KEY=secrets.token_hex(32))
        env.start()
        self.addCleanup(env.stop)
        import app
        app.app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
        self.client = app.app.test_client()
        database = patch.object(app, "get_db_connection")
        self.db = database.start()
        self.addCleanup(database.stop)

    def test_students_require_login(self):
        self.assertEqual(self.client.get("/students").status_code, 401)

    def test_invalid_login(self):
        response = self.client.post("/auth/login", json={"username": "tester", "password": "incorrect"})
        self.assertEqual(response.status_code, 401)

    def test_login_refresh_and_read(self):
        tokens = self.client.post("/auth/login", json={"username": "tester", "password": self.password}).get_json()
        refreshed = self.client.post("/auth/refresh", headers={"Authorization": "Bearer " + tokens["refresh_token"]})
        self.db.return_value.cursor.return_value.fetchall.return_value = []
        response = self.client.get("/students", headers={"Authorization": "Bearer " + refreshed.get_json()["access_token"]})
        self.assertEqual(response.get_json(), {"students": []})

    def test_unknown_major(self):
        self.assertEqual(self.client.get("/reports/search?major=Unknown").status_code, 400)

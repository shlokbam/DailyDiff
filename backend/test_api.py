import unittest
import os
import json
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.config import DB_PATH, HISTORY_FILE_PATH

class TestDailyDiffAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        
    def setUp(self):
        # Setup clean test environment or check database status
        # We can perform simple tests against the active endpoints
        pass

    def test_status_endpoint(self):
        """Test GET /api/status returns online status."""
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")

    def test_subscribe_success(self):
        """Test POST /api/subscribe with a new email."""
        # Generate a unique email for subscription testing
        import random
        test_email = f"test_{random.randint(1000, 9999)}@example.com"
        
        response = self.client.post("/api/subscribe", json={"email": test_email})
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("Successfully subscribed", data["message"])
        
        # Test subscribing the same email again should fail
        response_dup = self.client.post("/api/subscribe", json={"email": test_email})
        self.assertEqual(response_dup.status_code, 400)
        
        # Clean up by unsubscribing
        response_unsub = self.client.post("/api/unsubscribe", json={"email": test_email})
        self.assertEqual(response_unsub.status_code, 200)

    def test_invalid_email_subscription(self):
        """Test POST /api/subscribe with an invalid email formatting."""
        response = self.client.post("/api/subscribe", json={"email": "not-an-email"})
        self.assertEqual(response.status_code, 422) # Unprocessable Entity (Validation Error)

    def test_get_archive_empty_or_populated(self):
        """Test GET /api/briefs/archive works and returns a list."""
        response = self.client.get("/api/briefs/archive")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

if __name__ == "__main__":
    unittest.main()

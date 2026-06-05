"""Tests for FastAPI endpoints."""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


class TestAPI(unittest.TestCase):
    """Test cases for API endpoints."""

    def setUp(self):
        """Set up the test client."""
        self.client = TestClient(app)

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.json())
        self.assertEqual(response.json()["name"], "Job_Booster API")

    def test_parse_resume_error_no_file(self):
        """Test the resume parsing endpoint with no file."""
        response = self.client.post("/api/parse/resume")
        self.assertEqual(response.status_code, 422)

    def test_parse_job_error_no_data(self):
        """Test the job parsing endpoint with no data."""
        response = self.client.post("/api/parse/job")
        self.assertEqual(response.status_code, 422)

    @patch("app.api.scanner_routes.get_agent")
    def test_scanner_progress(self, mock_get_agent):
        """Test the scanner progress endpoint."""
        mock_get_agent.return_value = MagicMock(
            get_progress=lambda: {
                "total_startups": 1,
                "with_websites": 1,
                "processed": 0,
                "remaining": 1,
                "batch_number": 0,
                "promising_roles": 0,
                "status": "in_progress",
            }
        )
        response = self.client.get("/api/scanner/progress")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()

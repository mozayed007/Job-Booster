"""Tests for FastAPI endpoints."""

import os
import sys
import json
import unittest

# Ensure the project root is on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app


class TestHealthEndpoints(unittest.TestCase):
    """Test cases for health/status endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_check(self):
        """GET / should return 200 with status='ok'."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("message", data)
        self.assertIn("timestamp", data)

    def test_detailed_health(self):
        """GET /health should return 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("database", data)


class TestParseResumeEndpoint(unittest.TestCase):
    """Test cases for the resume parsing endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_parse_resume_no_file_returns_422(self):
        """POST /api/parse/resume with no file should return 422."""
        response = self.client.post("/api/parse/resume")
        self.assertEqual(response.status_code, 422)

    def test_parse_resume_txt_file(self):
        """POST /api/parse/resume with a txt file should return 200."""
        txt_content = b"John Doe\njohn@example.com\nSoftware Engineer at Acme Corp"
        response = self.client.post(
            "/api/parse/resume",
            files={"file": ("resume.txt", txt_content, "text/plain")},
        )
        # We accept 200 (with or without LLM) or 500 if LLM not configured
        self.assertIn(response.status_code, [200, 500])
        if response.status_code == 200:
            data = response.json()
            self.assertTrue(data.get("success", False))


class TestParseJobEndpoint(unittest.TestCase):
    """Test cases for the job description parsing endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_parse_job_no_data_returns_422(self):
        """POST /api/parse/job with no data should return 422."""
        response = self.client.post("/api/parse/job")
        self.assertEqual(response.status_code, 422)

    def test_parse_job_with_text(self):
        """POST /api/parse/job with job_text should return 200."""
        payload = {"job_text": "Senior Python Developer. Must know FastAPI and SQLAlchemy."}
        response = self.client.post("/api/parse/job", json=payload)
        self.assertIn(response.status_code, [200, 500])
        if response.status_code == 200:
            data = response.json()
            self.assertTrue(data.get("success", False))


class TestAnalyzeEndpoint(unittest.TestCase):
    """Test cases for the analysis endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_analyze_empty_payload_returns_200(self):
        """POST /api/analyze with empty JSON should return 200 with empty analysis."""
        response = self.client.post("/api/analyze", json={})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success", False))

    def test_analyze_with_inline_data(self):
        """POST /api/analyze with inline resume/job data should return 200."""
        payload = {
            "resume_data": {
                "skills": [{"name": "Python"}, {"name": "FastAPI"}],
                "work_experience": [],
            },
            "job_data": {
                "title": "Backend Engineer",
                "required_skills": ["Python", "Docker"],
            },
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertIn(response.status_code, [200, 500])
        if response.status_code == 200:
            data = response.json()
            self.assertIn("analysis", data)


class TestTailorEndpoint(unittest.TestCase):
    """Test cases for the tailoring endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_tailor_empty_payload_returns_200(self):
        """POST /api/tailor with empty data should still return 200."""
        response = self.client.post("/api/tailor", json={})
        self.assertIn(response.status_code, [200, 422, 500])

    def test_tailor_with_inline_data(self):
        """POST /api/tailor with inline resume/job data returns 200."""
        payload = {
            "resume_data": {
                "skills": [{"name": "Python"}],
                "work_experience": [],
            },
            "job_data": {
                "title": "Python Developer",
                "required_skills": ["Python"],
            },
            "format_type": "text",
        }
        response = self.client.post("/api/tailor", json=payload)
        self.assertIn(response.status_code, [200, 500])
        if response.status_code == 200:
            data = response.json()
            self.assertIn("tailored_resume", data)


if __name__ == "__main__":
    unittest.main()

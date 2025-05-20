"""Tests for FastAPI endpoints."""

import os
import json
import unittest
from fastapi.testclient import TestClient

# Add the root directory to the path so we can import the app
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.main import app


class TestAPI(unittest.TestCase):
    """Test cases for API endpoints."""
    
    def setUp(self):
        """Set up the test client."""
        self.client = TestClient(app)
    
    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["message"], "Job_Booster API is running (stubbed)")
    
    def test_parse_resume_error_no_file(self):
        """Test the resume parsing endpoint with no file."""
        response = self.client.post("/api/parse/resume")
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity
    
    def test_parse_job_error_no_data(self):
        """Test the job parsing endpoint with no data."""
        response = self.client.post("/api/parse/job")
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity
    
    def test_analyze_error_invalid_data(self):
        """Test the analysis endpoint with invalid data."""
        # Assuming stubbed AnalysisInput model currently accepts empty JSON
        # and the stubbed endpoint returns 200 with a placeholder message.
        response = self.client.post("/api/analyze", json={})
        self.assertEqual(response.status_code, 200) 
        self.assertEqual(response.json()["message"], "To-Do: Implement analysis logic.")
    
    def test_tailor_error_invalid_data(self):
        """Test the tailoring endpoint with invalid data."""
        # Assuming stubbed TailoringInput model currently accepts empty JSON
        # and the stubbed endpoint returns 200 with a placeholder message.
        response = self.client.post("/api/tailor", json={})
        self.assertEqual(response.status_code, 200) 
        self.assertEqual(response.json()["message"], "To-Do: Implement tailoring logic.")


if __name__ == "__main__":
    unittest.main()

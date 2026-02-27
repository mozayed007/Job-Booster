"""Tests for job description models."""

import sys
import os
import unittest

# Ensure the project root is on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.job_model import (
    Benefit,
    CompanyInfo,
    JobPosting,
    Requirement,
    Responsibility,
)


class TestCompanyInfo(unittest.TestCase):
    """Test cases for CompanyInfo model."""

    def test_company_info_creation(self):
        """Full CompanyInfo construction."""
        company = CompanyInfo(
            name="Tech Innovations Inc.",
            industry="Software Development",
            location="San Francisco, CA",
            website="https://techinnovations.example.com",
            description="A leading software development company",
            size="Medium",
        )
        self.assertEqual(company.name, "Tech Innovations Inc.")
        self.assertEqual(company.industry, "Software Development")
        self.assertEqual(company.location, "San Francisco, CA")
        self.assertEqual(company.website, "https://techinnovations.example.com")
        self.assertEqual(company.size, "Medium")

    def test_company_info_minimal(self):
        """CompanyInfo can be created with no fields."""
        company = CompanyInfo()
        self.assertIsNone(company.name)


class TestRequirement(unittest.TestCase):
    """Test cases for Requirement model."""

    def test_requirement_required(self):
        """Required requirement."""
        req = Requirement(
            description="5+ years Python experience",
            is_required=True,
            category="experience",
        )
        self.assertEqual(req.description, "5+ years Python experience")
        self.assertTrue(req.is_required)
        self.assertEqual(req.category, "experience")

    def test_requirement_preferred(self):
        """Optional/preferred requirement."""
        req = Requirement(
            description="Experience with FastAPI is a plus",
            is_required=False,
        )
        self.assertFalse(req.is_required)

    def test_requirement_default_is_required(self):
        """is_required should default to True."""
        req = Requirement(description="Must have X")
        self.assertTrue(req.is_required)


class TestResponsibility(unittest.TestCase):
    """Test cases for Responsibility model."""

    def test_responsibility_creation(self):
        """Basic Responsibility creation."""
        resp = Responsibility(
            description="Design and implement scalable backend services",
            category="engineering",
        )
        self.assertEqual(resp.description, "Design and implement scalable backend services")
        self.assertEqual(resp.category, "engineering")

    def test_responsibility_no_category(self):
        """Category is optional."""
        resp = Responsibility(description="Lead team meetings")
        self.assertIsNone(resp.category)


class TestBenefit(unittest.TestCase):
    """Test cases for Benefit model."""

    def test_benefit_creation(self):
        """Full Benefit construction."""
        benefit = Benefit(description="Comprehensive health insurance", category="health")
        self.assertEqual(benefit.description, "Comprehensive health insurance")
        self.assertEqual(benefit.category, "health")


class TestJobPosting(unittest.TestCase):
    """Test cases for the JobPosting aggregate model."""

    def test_job_posting_full_creation(self):
        """Full JobPosting construction."""
        company = CompanyInfo(name="Acme Inc.", location="NYC", industry="Tech")
        reqs = [
            Requirement(description="5+ years Python", is_required=True),
            Requirement(description="FastAPI nice-to-have", is_required=False),
        ]
        resps = [Responsibility(description="Build APIs")]
        benefits = [Benefit(description="Unlimited PTO", category="lifestyle")]

        job = JobPosting(
            title="Senior Python Developer",
            company=company,
            location="New York, NY",
            remote_type="hybrid",
            employment_type="full-time",
            experience_level="senior",
            description="We need a great Python dev.",
            requirements=reqs,
            responsibilities=resps,
            benefits=benefits,
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker", "Kubernetes"],
            keywords=["python", "backend", "rest"],
        )

        self.assertEqual(job.title, "Senior Python Developer")
        self.assertIsNotNone(job.company)
        self.assertEqual(job.company.name if job.company else None, "Acme Inc.")
        self.assertEqual(job.location, "New York, NY")
        self.assertEqual(job.remote_type, "hybrid")
        self.assertEqual(job.employment_type, "full-time")
        self.assertEqual(len(job.requirements), 2)
        self.assertEqual(len(job.responsibilities), 1)
        self.assertEqual(len(job.benefits), 1)
        self.assertIn("Python", job.required_skills)
        self.assertIn("Docker", job.preferred_skills)
        self.assertIsNotNone(job.id)

    def test_job_posting_defaults(self):
        """Empty JobPosting should have empty lists and None fields."""
        job = JobPosting()
        self.assertEqual(job.requirements, [])
        self.assertEqual(job.responsibilities, [])
        self.assertEqual(job.benefits, [])
        self.assertEqual(job.required_skills, [])
        self.assertEqual(job.preferred_skills, [])
        self.assertIsNone(job.title)

    def test_job_posting_serialisation(self):
        """JobPosting should serialise to dict via model_dump."""
        job = JobPosting(title="Engineer", required_skills=["Python"])
        data = job.model_dump()
        self.assertEqual(data["title"], "Engineer")
        self.assertIn("Python", data["required_skills"])


if __name__ == "__main__":
    unittest.main()

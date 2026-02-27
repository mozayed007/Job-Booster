"""Tests for resume models."""

import sys
import os
import unittest

# Ensure the project root is on the path so `app.*` imports work.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.resume_model import (
    Certification,
    ContactInfo,
    Education,
    Project,
    Resume,
    Skill,
    WorkExperience,
)


class TestContactInfo(unittest.TestCase):
    """Test cases for ContactInfo model."""

    def test_contact_info_creation(self):
        """Test creation of a ContactInfo object."""
        contact = ContactInfo(
            name="Jane Smith",
            email="jane.smith@example.com",
            phone="555-1234",
            linkedin="linkedin.com/in/janesmith",
            location="San Francisco, CA",
        )
        self.assertEqual(contact.name, "Jane Smith")
        self.assertEqual(contact.email, "jane.smith@example.com")
        self.assertEqual(contact.phone, "555-1234")
        self.assertEqual(contact.linkedin, "linkedin.com/in/janesmith")
        self.assertEqual(contact.location, "San Francisco, CA")

    def test_contact_info_minimal(self):
        """ContactInfo can be created with only optional fields."""
        contact = ContactInfo()
        self.assertIsNone(contact.name)
        self.assertIsNone(contact.email)


class TestEducation(unittest.TestCase):
    """Test cases for Education model."""

    def test_education_creation(self):
        """Test creation of an Education object."""
        edu = Education(
            institution="MIT",
            degree="Bachelor of Science",
            field_of_study="Computer Science",
            start_date="2015",
            end_date="2019",
            gpa=3.9,
        )
        self.assertEqual(edu.institution, "MIT")
        self.assertEqual(edu.degree, "Bachelor of Science")
        self.assertEqual(edu.field_of_study, "Computer Science")
        self.assertEqual(edu.gpa, 3.9)
        self.assertIsNotNone(edu.id)

    def test_education_honors(self):
        """Honors list should default to empty."""
        edu = Education(institution="Stanford")
        self.assertIsInstance(edu.honors, list)
        self.assertEqual(len(edu.honors or []), 0)


class TestWorkExperience(unittest.TestCase):
    """Test cases for WorkExperience model."""

    def test_work_experience_creation(self):
        """Test creation of a WorkExperience object."""
        exp = WorkExperience(
            company="Acme Corp",
            title="Software Engineer",
            location="Remote",
            start_date="2020-01",
            end_date=None,
            is_current=True,
            bullet_points=["Built scalable APIs", "Led a team of 4"],
            technologies=["Python", "FastAPI"],
        )
        self.assertEqual(exp.company, "Acme Corp")
        self.assertEqual(exp.title, "Software Engineer")
        self.assertTrue(exp.is_current)
        self.assertIsNone(exp.end_date)
        self.assertIn("Built scalable APIs", exp.bullet_points or [])
        self.assertIn("Python", exp.technologies or [])
        self.assertIsNotNone(exp.id)

    def test_bullet_points_default_empty(self):
        """bullet_points should default to empty list."""
        exp = WorkExperience(company="Foo", title="Bar")
        self.assertEqual(exp.bullet_points, [])


class TestSkill(unittest.TestCase):
    """Test cases for Skill model."""

    def test_skill_creation(self):
        """Test creation of a Skill object."""
        skill = Skill(name="Python", category="Programming", level="expert")
        self.assertEqual(skill.name, "Python")
        self.assertEqual(skill.category, "Programming")
        self.assertEqual(skill.level, "expert")

    def test_skill_minimal(self):
        """Skill requires only name."""
        skill = Skill(name="Docker")
        self.assertEqual(skill.name, "Docker")
        self.assertIsNone(skill.category)


class TestResume(unittest.TestCase):
    """Test cases for the Resume aggregate model."""

    def test_resume_creation_full(self):
        """Test creation of a complete Resume."""
        contact = ContactInfo(name="John Doe", email="john@example.com")
        edu = [Education(institution="Stanford", degree="MS", field_of_study="ML")]
        exp = [WorkExperience(company="Google", title="SWE")]
        skills = [Skill(name="Python"), Skill(name="TensorFlow")]

        resume = Resume(
            contact=contact,
            summary="Senior ML Engineer with 5+ years experience.",
            work_experience=exp,
            education=edu,
            skills=skills,
        )

        self.assertIsNotNone(resume.contact)
        self.assertEqual(resume.contact.name if resume.contact else None, "John Doe")
        self.assertEqual(resume.summary, "Senior ML Engineer with 5+ years experience.")
        self.assertEqual(len(resume.education), 1)
        self.assertEqual(len(resume.work_experience), 1)
        self.assertEqual(len(resume.skills), 2)
        self.assertIsNotNone(resume.id)

    def test_resume_defaults(self):
        """Empty Resume should have empty lists for collection fields."""
        resume = Resume()
        self.assertEqual(resume.work_experience, [])
        self.assertEqual(resume.education, [])
        self.assertEqual(resume.skills, [])
        self.assertEqual(resume.projects, [])
        self.assertIsNone(resume.summary)

    def test_resume_serialisation(self):
        """Resume should serialise to dict via model_dump."""
        resume = Resume(summary="Test")
        data = resume.model_dump()
        self.assertIn("summary", data)
        self.assertEqual(data["summary"], "Test")


if __name__ == "__main__":
    unittest.main()

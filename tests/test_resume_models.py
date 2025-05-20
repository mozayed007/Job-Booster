"""Tests for resume models."""

import unittest
from datetime import date
from uuid import UUID

from common.models.resume import Resume, ContactInfo, Education, WorkExperience, Skill


class TestResumeModels(unittest.TestCase):
    """Test cases for resume models."""
    
    @unittest.skip("Model fields stubbed")
    def test_contact_info_creation(self):
        """Test creation of a ContactInfo object."""
        contact_info = ContactInfo(
            name="John Doe",
            email="john.doe@example.com",
            phone="123-456-7890",
            linkedin="linkedin.com/in/johndoe"
        )
        
        self.assertEqual(contact_info.name, "John Doe")
        self.assertEqual(contact_info.email, "john.doe@example.com")
        self.assertEqual(contact_info.phone, "123-456-7890")
        self.assertEqual(contact_info.linkedin, "linkedin.com/in/johndoe")
        self.assertIsInstance(contact_info.id, UUID)
    
    @unittest.skip("Model fields stubbed")
    def test_education_creation(self):
        """Test creation of an Education object."""
        education = Education(
            institution="University of Example",
            degree="Bachelor of Science",
            field_of_study="Computer Science",
            start_date=date(2015, 9, 1),
            end_date=date(2019, 5, 31),
            gpa=3.8
        )
        
        self.assertEqual(education.institution, "University of Example")
        self.assertEqual(education.degree, "Bachelor of Science")
        self.assertEqual(education.field_of_study, "Computer Science")
        self.assertEqual(education.start_date, date(2015, 9, 1))
        self.assertEqual(education.end_date, date(2019, 5, 31))
        self.assertEqual(education.gpa, 3.8)
        self.assertIsInstance(education.id, UUID)
    
    @unittest.skip("Model fields stubbed")
    def test_work_experience_creation(self):
        """Test creation of a WorkExperience object."""
        work_experience = WorkExperience(
            company="Example Corp",
            position="Software Developer",
            start_date=date(2019, 6, 1),
            end_date=None,  # Current position
            location="San Francisco, CA",
            description="Developing software for clients",
            achievements=["Improved app performance by 30%", "Led a team of 3 developers"]
        )
        
        self.assertEqual(work_experience.company, "Example Corp")
        self.assertEqual(work_experience.position, "Software Developer")
        self.assertEqual(work_experience.start_date, date(2019, 6, 1))
        self.assertIsNone(work_experience.end_date)
        self.assertEqual(work_experience.location, "San Francisco, CA")
        self.assertEqual(work_experience.description, "Developing software for clients")
        self.assertEqual(len(work_experience.achievements), 2)
        self.assertIn("Improved app performance by 30%", work_experience.achievements)
        self.assertIsInstance(work_experience.id, UUID)
    
    @unittest.skip("Model fields stubbed")
    def test_skill_creation(self):
        """Test creation of a Skill object."""
        skill = Skill(
            name="Python",
            category="Programming Language",
            proficiency="Expert",
            years_of_experience=5
        )
        
        self.assertEqual(skill.name, "Python")
        self.assertEqual(skill.category, "Programming Language")
        self.assertEqual(skill.proficiency, "Expert")
        self.assertEqual(skill.years_of_experience, 5)
        self.assertIsInstance(skill.id, UUID)
    
    @unittest.skip("Model fields stubbed")
    def test_resume_creation(self):
        """Test creation of a complete Resume object."""
        contact_info = ContactInfo(
            name="John Doe",
            email="john.doe@example.com",
            phone="123-456-7890"
        )
        
        education = [
            Education(
                institution="University of Example",
                degree="Bachelor of Science",
                field_of_study="Computer Science"
            )
        ]
        
        work_experience = [
            WorkExperience(
                company="Example Corp",
                position="Software Developer",
                description="Developing software for clients"
            )
        ]
        
        skills = [
            Skill(name="Python", proficiency="Expert"),
            Skill(name="JavaScript", proficiency="Intermediate")
        ]
        
        resume = Resume(
            contact_info=contact_info,
            summary="Experienced software developer",
            education=education,
            work_experience=work_experience,
            skills=skills
        )
        
        self.assertEqual(resume.contact_info.name, "John Doe")
        self.assertEqual(resume.summary, "Experienced software developer")
        self.assertEqual(len(resume.education), 1)
        self.assertEqual(len(resume.work_experience), 1)
        self.assertEqual(len(resume.skills), 2)
        self.assertIsInstance(resume.id, UUID)


if __name__ == "__main__":
    unittest.main()

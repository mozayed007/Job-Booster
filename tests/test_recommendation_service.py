"""Tests for RecommendationService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.recommendation_service import RecommendationService


@pytest.fixture
def mock_search_service():
    svc = MagicMock()
    svc.search_jobs = AsyncMock(
        return_value=[
            {
                "id": "job_1",
                "text": "Python developer role",
                "metadata": {"job_id": "1"},
                "distance": 0.2,
                "score": 0.8,
            },
            {
                "id": "job_2",
                "text": "Data engineer role",
                "metadata": {"job_id": "2"},
                "distance": 0.4,
                "score": 0.6,
            },
        ]
    )
    svc.search_resumes = AsyncMock(
        return_value=[
            {
                "id": "resume_1",
                "text": "Python resume",
                "metadata": {"resume_id": "1"},
                "distance": 0.1,
                "score": 0.9,
            },
        ]
    )
    return svc


@pytest.fixture
def mock_db_service():
    svc = MagicMock()
    resume_data = {
        "id": 1,
        "filename": "test_resume.pdf",
        "raw_text": "Python developer with 5 years experience in Django and AWS",
        "content_json": {
            "skills": ["Python", "Django", "AWS", "PostgreSQL"],
            "summary": "Experienced Python developer",
        },
    }
    job_data = {
        "id": 1,
        "title": "Senior Python Developer",
        "company": "TechCo",
        "raw_text": "Looking for Python developer with Django and React experience",
        "content_json": {
            "skills": ["Python", "Django", "React", "TypeScript"],
            "description": "Senior Python role",
        },
    }

    def query_side_effect(table, limit=100, offset=0, filter_conditions=None):
        if filter_conditions and filter_conditions.get("id") == 1:
            if table == "resumes":
                return [resume_data]
            elif table == "job_postings":
                return [job_data]
        return []

    svc.query_records = MagicMock(side_effect=query_side_effect)
    return svc


@pytest.fixture
def service(mock_search_service, mock_db_service):
    return RecommendationService(
        search_service=mock_search_service,
        db_service=mock_db_service,
    )


class TestRecommendJobsForResume:
    @pytest.mark.asyncio
    async def test_returns_jobs_for_valid_resume(self, service, mock_search_service):
        results = await service.recommend_jobs_for_resume(resume_id=1, limit=10)
        assert len(results) == 2
        mock_search_service.search_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_for_missing_resume(self, service, mock_db_service):
        mock_db_service.query_records = MagicMock(return_value=[])
        results = await service.recommend_jobs_for_resume(resume_id=999)
        assert results == []

    @pytest.mark.asyncio
    async def test_uses_raw_text_as_query(self, service, mock_search_service):
        await service.recommend_jobs_for_resume(resume_id=1)
        call_args = mock_search_service.search_jobs.call_args
        query = call_args[0][0]
        assert "Python" in query


class TestRecommendResumesForJob:
    @pytest.mark.asyncio
    async def test_returns_resumes_for_valid_job(self, service, mock_search_service):
        results = await service.recommend_resumes_for_job(job_id=1, limit=5)
        assert len(results) == 1
        mock_search_service.search_resumes.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_for_missing_job(self, service, mock_db_service):
        mock_db_service.query_records = MagicMock(return_value=[])
        results = await service.recommend_resumes_for_job(job_id=999)
        assert results == []


class TestSkillGapAnalysis:
    def test_returns_matches_and_gaps(self, service):
        result = service.get_skill_gap_analysis(resume_id=1, job_id=1)
        assert "matches" in result
        assert "gaps" in result
        assert "extra_skills" in result
        assert "coverage_pct" in result

    def test_identifies_matching_skills(self, service):
        result = service.get_skill_gap_analysis(resume_id=1, job_id=1)
        assert "python" in result["matches"]
        assert "django" in result["matches"]

    def test_identifies_skill_gaps(self, service):
        result = service.get_skill_gap_analysis(resume_id=1, job_id=1)
        assert "react" in result["gaps"]
        assert "typescript" in result["gaps"]

    def test_identifies_extra_skills(self, service):
        result = service.get_skill_gap_analysis(resume_id=1, job_id=1)
        assert "aws" in result["extra_skills"]
        assert "postgresql" in result["extra_skills"]

    def test_coverage_percentage(self, service):
        result = service.get_skill_gap_analysis(resume_id=1, job_id=1)
        assert result["coverage_pct"] == 50.0

    def test_returns_error_for_missing_records(self, service, mock_db_service):
        mock_db_service.query_records = MagicMock(return_value=[])
        result = service.get_skill_gap_analysis(resume_id=999, job_id=999)
        assert "error" in result


class TestCareerSuggestions:
    def test_returns_suggestions_for_valid_resume(self, service):
        result = service.get_career_suggestions(resume_id=1)
        assert "current_skills" in result
        assert "trending_skills" in result
        assert "suggested_skills" in result
        assert "related_suggestions" in result

    def test_returns_error_for_missing_resume(self, service, mock_db_service):
        mock_db_service.query_records = MagicMock(return_value=[])
        result = service.get_career_suggestions(resume_id=999)
        assert "error" in result


class TestExtractSkills:
    def test_extracts_from_list(self, service):
        content = {"skills": ["Python", "Java", "Go"]}
        result = service._extract_skills(content)
        assert "Python" in result
        assert "Java" in result

    def test_extracts_from_string(self, service):
        content = {"skills": "Python, Java, Go"}
        result = service._extract_skills(content)
        assert "Python" in result
        assert "Java" in result

    def test_extracts_from_multiple_keys(self, service):
        content = {
            "skills": ["Python"],
            "technologies": ["Docker"],
            "tools": ["Git"],
        }
        result = service._extract_skills(content)
        assert "Python" in result
        assert "Docker" in result
        assert "Git" in result

    def test_returns_empty_for_none(self, service):
        assert service._extract_skills(None) == []

    def test_returns_empty_for_no_skills(self, service):
        assert service._extract_skills({"name": "test"}) == []


class TestExtractTextFromJson:
    def test_extracts_summary(self, service):
        content = {"summary": "Experienced developer", "skills": ["Python"]}
        result = service._extract_text_from_json(content)
        assert "Experienced developer" in result
        assert "Python" in result

    def test_extracts_experience(self, service):
        content = {
            "experience": [
                {"title": "Developer", "company": "TechCo", "description": "Built stuff"},
            ]
        }
        result = service._extract_text_from_json(content)
        assert "Developer" in result
        assert "TechCo" in result

    def test_returns_empty_for_none(self, service):
        assert service._extract_text_from_json(None) == ""

    def test_returns_empty_for_empty_dict(self, service):
        assert service._extract_text_from_json({}) == ""

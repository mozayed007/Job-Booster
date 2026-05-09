"""Tests for AnalyticsService."""

from unittest.mock import MagicMock

import pytest

from app.services.analytics_service import AnalyticsService


@pytest.fixture
def mock_db_service():
    svc = MagicMock()
    svc.db = MagicMock()
    return svc


@pytest.fixture
def service(mock_db_service):
    return AnalyticsService(db_service=mock_db_service)


class TestGetResumeStats:
    def test_returns_resume_counts(self, service, mock_db_service):
        mock_query = MagicMock()
        mock_query.scalar.return_value = 5
        mock_query.all.return_value = []
        mock_db_service.db.query.return_value = mock_query

        stats = service.get_resume_stats()
        assert "total_resumes" in stats
        assert "total_versions" in stats
        assert "total_tailored" in stats
        assert "parsed_with_skills" in stats

    def test_handles_empty_database(self, service, mock_db_service):
        mock_query = MagicMock()
        mock_query.scalar.return_value = 0
        mock_query.all.return_value = []
        mock_db_service.db.query.return_value = mock_query

        stats = service.get_resume_stats()
        assert stats["total_resumes"] == 0


class TestGetJobStats:
    def test_returns_job_counts(self, service, mock_db_service):
        mock_query = MagicMock()
        mock_query.scalar.return_value = 10
        mock_query.filter.return_value.scalar.return_value = 5
        mock_query.all.return_value = [
            ({"skills": ["Python", "Django"]},),
            ({"skills": ["Python", "React"]},),
        ]
        mock_db_service.db.query.return_value = mock_query

        stats = service.get_job_stats()
        assert "total_jobs" in stats
        assert "total_companies" in stats
        assert "top_skills" in stats
        assert "unique_skills" in stats

    def test_counts_skills_across_postings(self, service, mock_db_service):
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = 2

        mock_all = MagicMock()
        mock_all.all.return_value = [
            ({"skills": ["Python", "Django"]},),
            ({"skills": ["Python", "React"]},),
            ({"skills": ["Django", "Flask"]},),
        ]

        call_count = [0]

        def query_side_effect(model):
            call_count[0] += 1
            if call_count[0] <= 2:
                return mock_scalar
            return mock_all

        mock_db_service.db.query.side_effect = query_side_effect
        stats = service.get_job_stats()
        assert isinstance(stats["top_skills"], list)


class TestGetMatchingStats:
    def test_returns_matching_metrics(self, service, mock_db_service):
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [(85.0,), (90.0,), (75.0,)]
        mock_db_service.db.query.return_value = mock_query

        stats = service.get_matching_stats()
        assert stats["total_matches"] == 3
        assert stats["average_score"] == 83.33
        assert stats["max_score"] == 90.0
        assert stats["min_score"] == 75.0

    def test_handles_no_matches(self, service, mock_db_service):
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = []
        mock_db_service.db.query.return_value = mock_query

        stats = service.get_matching_stats()
        assert stats["total_matches"] == 0
        assert stats["average_score"] == 0


class TestGetApplicationFunnel:
    def test_returns_funnel_data(self, service, mock_db_service):
        mock_query = MagicMock()
        mock_query.filter.return_value.group_by.return_value.all.return_value = [
            ("applied", 10),
            ("interview", 5),
            ("offer", 2),
            ("rejected", 3),
        ]
        mock_db_service.db.query.return_value = mock_query

        funnel = service.get_application_funnel(user_id=1)
        assert funnel["total"] == 20
        assert funnel["applied"] == 10
        assert funnel["interview"] == 5
        assert funnel["offer"] == 2
        assert funnel["interview_rate"] == 25.0

    def test_handles_empty_funnel(self, service, mock_db_service):
        mock_query = MagicMock()
        mock_query.filter.return_value.group_by.return_value.all.return_value = []
        mock_db_service.db.query.return_value = mock_query

        funnel = service.get_application_funnel()
        assert funnel["total"] == 0
        assert funnel["interview_rate"] == 0


class TestGetSkillTrends:
    def test_returns_trending_skills(self, service, mock_db_service):
        mock_query = MagicMock()
        mock_query.all.return_value = [
            ({"skills": ["Python", "Django"]},),
            ({"skills": ["Python", "React"]},),
            ({"skills": ["Go", "Docker"]},),
        ]
        mock_db_service.db.query.return_value = mock_query

        trends = service.get_skill_trends()
        assert "total_skills_tracked" in trends
        assert "top_skills" in trends
        assert isinstance(trends["top_skills"], list)
        if trends["top_skills"]:
            assert "skill" in trends["top_skills"][0]
            assert "count" in trends["top_skills"][0]


class TestGetScannerStats:
    def test_returns_scanner_data(self, service, mock_db_service):
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = 5

        mock_state_result = MagicMock()
        mock_state_result.batch_number = 3
        mock_state_result.status = "in_progress"

        mock_order = MagicMock()
        mock_order.order_by.return_value.first.return_value = mock_state_result

        mock_filter = MagicMock()
        mock_filter.filter.return_value.scalar.return_value = 2

        mock_category_query = MagicMock()
        mock_category_query.group_by.return_value.all.return_value = [("AI", 3), ("Fintech", 2)]

        call_count = [0]

        def query_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                return mock_scalar
            if call_count[0] == 3:
                return mock_order
            if call_count[0] == 4:
                return mock_filter
            return mock_category_query

        mock_db_service.db.query.side_effect = query_side_effect
        stats = service.get_scanner_stats()
        assert "total_startups" in stats
        assert "total_scanned_jobs" in stats
        assert "scanner_status" in stats


class TestGetDashboardData:
    def test_returns_all_sections(self, service, mock_db_service):
        mock_query = MagicMock()
        mock_query.scalar.return_value = 0
        mock_query.all.return_value = []
        mock_query.filter.return_value.all.return_value = []
        mock_query.filter.return_value.scalar.return_value = 0
        mock_query.filter.return_value.group_by.return_value.all.return_value = []
        mock_query.order_by.return_value.first.return_value = None
        mock_query.group_by.return_value.all.return_value = []
        mock_db_service.db.query.return_value = mock_query

        dashboard = service.get_dashboard_data(user_id=1)
        assert "resumes" in dashboard
        assert "jobs" in dashboard
        assert "matching" in dashboard
        assert "applications" in dashboard
        assert "skill_trends" in dashboard
        assert "scanner" in dashboard

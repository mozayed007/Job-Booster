"""Tests for ApplicationTracker."""

from unittest.mock import MagicMock

import pytest

from app.services.tracking_service import VALID_STATUSES, ApplicationTracker


@pytest.fixture
def mock_db_service():
    svc = MagicMock()
    svc.db = MagicMock()
    return svc


@pytest.fixture
def tracker(mock_db_service):
    return ApplicationTracker(db_service=mock_db_service)


class TestTrackApplication:
    def test_tracks_with_valid_data(self, tracker, mock_db_service):
        mock_db_service.insert_record.return_value = 1
        data = {
            "company_name": "TechCo",
            "position_title": "Python Developer",
            "status": "applied",
        }
        result = tracker.track_application(data)
        assert result == 1
        mock_db_service.insert_record.assert_called_once()

    def test_defaults_to_applied_status(self, tracker, mock_db_service):
        mock_db_service.insert_record.return_value = 2
        data = {"company_name": "TechCo", "position_title": "Dev"}
        tracker.track_application(data)
        call_data = mock_db_service.insert_record.call_args[0][1]
        assert call_data["status"] == "applied"

    def test_rejects_invalid_status(self, tracker, mock_db_service):
        mock_db_service.insert_record.return_value = 3
        data = {"company_name": "TechCo", "position_title": "Dev", "status": "invalid"}
        tracker.track_application(data)
        call_data = mock_db_service.insert_record.call_args[0][1]
        assert call_data["status"] == "applied"

    def test_accepts_all_valid_statuses(self, tracker, mock_db_service):
        for status in VALID_STATUSES:
            mock_db_service.insert_record.return_value = 1
            data = {"company_name": "X", "position_title": "Y", "status": status}
            tracker.track_application(data)
            call_data = mock_db_service.insert_record.call_args[0][1]
            assert call_data["status"] == status


class TestUpdateStatus:
    def test_updates_existing_application(self, tracker, mock_db_service):
        mock_app = MagicMock()
        mock_app.status = "applied"
        mock_app.notes = None
        mock_db_service.db.query.return_value.filter.return_value.first.return_value = mock_app

        result = tracker.update_status(1, "interview", notes="Phone screen scheduled")
        assert result is True
        assert mock_app.status == "interview"
        assert mock_app.notes == "Phone screen scheduled"
        mock_db_service.db.commit.assert_called_once()

    def test_returns_false_for_invalid_status(self, tracker):
        result = tracker.update_status(1, "invalid_status")
        assert result is False

    def test_returns_false_for_missing_app(self, tracker, mock_db_service):
        mock_db_service.db.query.return_value.filter.return_value.first.return_value = None
        result = tracker.update_status(999, "interview")
        assert result is False


class TestGetApplications:
    def test_returns_all_applications(self, tracker, mock_db_service):
        mock_app = MagicMock()
        mock_app.id = 1
        mock_app.user_id = 1
        mock_app.job_id = None
        mock_app.resume_id = None
        mock_app.company_name = "TechCo"
        mock_app.position_title = "Dev"
        mock_app.status = "applied"
        mock_app.notes = None
        mock_app.applied_at = None
        mock_app.updated_at = None
        query = mock_db_service.db.query.return_value
        query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [  # noqa: E501
            mock_app
        ]

        results = tracker.get_applications(user_id=1)
        assert len(results) == 1
        assert results[0]["company_name"] == "TechCo"

    def test_filters_by_status(self, tracker, mock_db_service):
        query = mock_db_service.db.query.return_value
        query.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []  # noqa: E501

        results = tracker.get_applications(status="interview")
        assert results == []


class TestGetApplicationStats:
    def test_returns_stats(self, tracker, mock_db_service):
        mock_db_service.db.query.return_value.filter.return_value.count.return_value = 5
        mock_db_service.db.query.return_value.count.return_value = 5

        mock_status_query = MagicMock()
        mock_status_query.filter.return_value.group_by.return_value.all.return_value = [
            ("applied", 3),
            ("interview", 2),
        ]
        mock_db_service.db.query.return_value = mock_status_query

        stats = tracker.get_application_stats(user_id=1)
        assert "total" in stats
        assert "by_status" in stats


class TestDeleteApplication:
    def test_deletes_existing_application(self, tracker, mock_db_service):
        mock_app = MagicMock()
        mock_db_service.db.query.return_value.filter.return_value.first.return_value = mock_app

        result = tracker.delete_application(1)
        assert result is True
        mock_db_service.db.delete.assert_called_once_with(mock_app)
        mock_db_service.db.commit.assert_called()

    def test_returns_false_for_missing_app(self, tracker, mock_db_service):
        mock_db_service.db.query.return_value.filter.return_value.first.return_value = None
        result = tracker.delete_application(999)
        assert result is False


class TestValidStatuses:
    def test_expected_statuses_exist(self):
        assert "applied" in VALID_STATUSES
        assert "interview" in VALID_STATUSES
        assert "offer" in VALID_STATUSES
        assert "rejected" in VALID_STATUSES
        assert "withdrawn" in VALID_STATUSES
        assert len(VALID_STATUSES) == 5


class TestToDict:
    def test_converts_application_to_dict(self):
        mock_app = MagicMock()
        mock_app.id = 1
        mock_app.user_id = 1
        mock_app.job_id = 2
        mock_app.resume_id = 3
        mock_app.company_name = "TechCo"
        mock_app.position_title = "Dev"
        mock_app.status = "applied"
        mock_app.notes = "test note"
        mock_app.applied_at = None
        mock_app.updated_at = None

        result = ApplicationTracker._to_dict(mock_app)
        assert result["id"] == 1
        assert result["company_name"] == "TechCo"
        assert result["position_title"] == "Dev"
        assert result["status"] == "applied"
        assert result["notes"] == "test note"

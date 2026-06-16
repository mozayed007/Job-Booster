"""Tests for job fit scoring."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.db_models import Base, JobPostingDB
from app.models.startup_model import BigSetPreferences, UserProfile
from app.services.bigset_import_service import BIGSET_SOURCE
from app.services.job_fit_service import rank_imported_jobs, score_job_against_profile


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestJobFitService:
    def test_score_job_with_skills(self, db_session):
        job = JobPostingDB(
            title="Backend Engineer",
            company="Acme",
            raw_text="Python FastAPI PostgreSQL remote Berlin",
            content_json={"source": BIGSET_SOURCE},
        )
        profile = UserProfile(skills=["Python", "FastAPI"], preferred_locations=["Berlin"])
        score = score_job_against_profile(job, profile)
        assert score > 0.4

    def test_rank_imported_jobs_filters_source(self, db_session):
        db_session.add(
            JobPostingDB(
                title="ML Role",
                company="Co",
                raw_text="machine learning pytorch",
                content_json={"source": BIGSET_SOURCE},
            )
        )
        db_session.add(
            JobPostingDB(
                title="Other",
                company="X",
                raw_text="unrelated",
                content_json={"source": "manual"},
            )
        )
        db_session.commit()
        profile = UserProfile(
            skills=["machine learning"],
            bigset=BigSetPreferences(min_fit_score=0.0),
        )
        ranked = rank_imported_jobs(db_session, profile, min_score=0.0)
        assert len(ranked) == 1
        assert ranked[0]["company"] == "Co"

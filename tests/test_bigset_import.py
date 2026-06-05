"""Tests for BigSet CSV import."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.db_models import Base, JobPostingDB, StartupDB
from app.services.bigset_import_service import (
    BIGSET_CATEGORY,
    BigSetImportService,
    load_mappings,
    mark_startup_scanned,
    normalize_url,
    parse_tabular_file,
    resolve_mapping_id,
    should_skip_scrape,
)
from app.core.config import settings


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def fixture_csv():
    path = Path(__file__).parent / "fixtures" / "bigset_yc_sample.csv"
    return path.read_bytes()


class TestBigSetHelpers:
    def test_normalize_url_adds_scheme(self):
        assert normalize_url("example.com") == "https://example.com"
        assert normalize_url("https://x.com") == "https://x.com"

    def test_resolve_mapping_from_filename(self):
        mid = resolve_mapping_id("ai-native-hiring-engineers.csv")
        assert mid == "yc-w26-hiring"

    def test_load_mappings_has_profiles(self):
        mappings = load_mappings()
        assert "yc-w26-hiring" in mappings
        assert mappings["yc-w26-hiring"].level == "company"


class TestBigSetImport:
    @pytest.mark.asyncio
    async def test_company_import_upserts_startups_and_jobs(
        self, db_session, fixture_csv
    ):
        svc = BigSetImportService(db_session)
        result = await svc.import_file(
            fixture_csv, "yc-w26-hiring.csv", mapping_id="yc-w26-hiring"
        )
        assert result.success
        assert result.stored == 2
        assert result.startups_upserted == 2

        startups = (
            db_session.query(StartupDB)
            .filter(StartupDB.category == BIGSET_CATEGORY)
            .all()
        )
        assert len(startups) == 2
        assert startups[0].website.startswith("https://")

        jobs = db_session.query(JobPostingDB).all()
        assert len(jobs) == 2
        assert jobs[0].content_json.get("source") == "bigset"

    @pytest.mark.asyncio
    async def test_import_is_idempotent(self, db_session, fixture_csv):
        svc = BigSetImportService(db_session)
        first = await svc.import_file(
            fixture_csv, "yc-w26-hiring.csv", mapping_id="yc-w26-hiring"
        )
        second = await svc.import_file(
            fixture_csv, "yc-w26-hiring.csv", mapping_id="yc-w26-hiring"
        )
        assert first.stored == 2
        assert second.stored == 0
        assert second.skipped_duplicates >= 2

    def test_parse_csv_rows(self, fixture_csv):
        rows = parse_tabular_file(fixture_csv, "sample.csv")
        assert len(rows) == 2
        assert rows[0]["Company"] == "TestCorp Alpha"

    @pytest.mark.asyncio
    async def test_reimport_updates_open_roles_not_duplicates(
        self, db_session, fixture_csv
    ):
        svc = BigSetImportService(db_session)
        await svc.import_file(
            fixture_csv, "yc-w26-hiring.csv", mapping_id="yc-w26-hiring"
        )
        updated_csv = fixture_csv.replace(
            b"TestCorp Alpha,AI widgets,Series A,12,",
            b"TestCorp Alpha,AI widgets,Series A,99,",
        )
        second = await svc.import_file(
            updated_csv, "yc-w26-hiring.csv", mapping_id="yc-w26-hiring"
        )
        assert second.stored == 0
        jobs = db_session.query(JobPostingDB).filter(
            JobPostingDB.company == "TestCorp Alpha"
        ).all()
        assert len(jobs) == 1
        assert "99 listings" in jobs[0].title


class TestBigSetScanHelpers:
    def test_mark_startup_scanned_upserts_missing_row(self, db_session):
        mark_startup_scanned(
            db_session,
            "NewCo",
            website="https://newco.example",
            city="Berlin",
        )
        row = db_session.query(StartupDB).filter(StartupDB.name == "NewCo").one()
        assert row.last_scanned is not None
        assert row.website == "https://newco.example"

    def test_should_skip_scrape_within_window(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "BIGSET_SKIP_SCRAPE_HOURS", 24)
        mark_startup_scanned(db_session, "SkipCo")
        assert should_skip_scrape(db_session, "SkipCo") is True
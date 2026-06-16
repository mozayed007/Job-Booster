"""Tests for BigSet import preview."""

from pathlib import Path

from app.services.bigset_import_service import preview_import

FIXTURE = Path(__file__).parent / "fixtures" / "bigset_yc_sample.csv"


class TestBigSetPreview:
    def test_preview_yc_sample_matches_columns(self):
        content = FIXTURE.read_bytes()
        result = preview_import(content, "bigset_yc_sample.csv", "yc-w26-hiring")
        assert result["success"] is True
        assert result["resolved_mapping"] == "yc-w26-hiring"
        assert result["can_import"] is True
        assert result["row_count"] == 2
        assert "Company" in result["matched"]

    def test_preview_reports_missing_columns(self):
        content = b"Foo,Bar\n1,2\n"
        result = preview_import(content, "bad.csv", "yc-w26-hiring")
        assert result["success"] is True
        assert result["can_import"] is False
        assert len(result["missing"]) > 0
"""Content quality tests for gold-layer outputs.

These tests go beyond existence checks: they validate Pydantic schemas,
measure null rates, and exercise the quality gate itself. They are skipped
when the pipeline has not been run yet (no gold files present).
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GOLD_DIR = DATA_DIR / "gold"

# Generous tolerance for LLM-dependent fields when running against real data.
MAX_LLM_NULL_RATE = 0.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_gold(filename: str) -> list[dict]:
    """Load a gold file and unwrap the run_id envelope injected by main.py."""
    path = GOLD_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not found — run the pipeline first")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "records" in data:
        return data["records"]
    return data


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestLocalizedCatalogSchema:
    """Every record in localized_catalog.json must satisfy GoldLocalizedEntry."""

    @pytest.fixture(autouse=True)
    def records(self):
        from data_foundry.schemas.gold import GoldLocalizedEntry

        self.schema = GoldLocalizedEntry
        self.records = load_gold("localized_catalog.json")

    def test_has_records(self):
        assert len(self.records) > 0

    def test_all_records_valid(self):
        errors = []
        for i, rec in enumerate(self.records):
            try:
                self.schema.model_validate(rec)
            except ValidationError as exc:
                errors.append(f"record[{i}] id={rec.get('id', '?')}: {exc}")
        assert not errors, f"Schema violations:\n" + "\n".join(errors[:5])

    def test_id_is_never_null(self):
        missing = [r for r in self.records if not r.get("id")]
        assert not missing, f"{len(missing)} records have no id"

    def test_title_pt_is_never_null(self):
        missing = [r for r in self.records if not (r.get("title") or {}).get("pt")]
        assert not missing, f"{len(missing)} records have no title.pt"

    def test_description_pt_null_rate_within_threshold(self):
        from data_foundry.quality import check_null_rate

        rate = check_null_rate(self.records, "description.pt")
        assert rate <= MAX_LLM_NULL_RATE, (
            f"description.pt null rate {rate:.0%} exceeds {MAX_LLM_NULL_RATE:.0%}"
        )

    def test_no_duplicate_ids(self):
        ids = [r["id"] for r in self.records if r.get("id")]
        assert len(ids) == len(set(ids)), "Duplicate ids in localized_catalog"


class TestUniversalMetadataSchema:
    """Every record in universal_metadata.json must satisfy GoldUniversalEntry."""

    @pytest.fixture(autouse=True)
    def records(self):
        from data_foundry.schemas.gold import GoldUniversalEntry

        self.schema = GoldUniversalEntry
        self.records = load_gold("universal_metadata.json")

    def test_has_records(self):
        assert len(self.records) > 0

    def test_all_records_valid(self):
        errors = []
        for i, rec in enumerate(self.records):
            try:
                self.schema.model_validate(rec)
            except ValidationError as exc:
                errors.append(f"record[{i}] id={rec.get('id', '?')}: {exc}")
        assert not errors, f"Schema violations:\n" + "\n".join(errors[:5])

    def test_id_is_never_null(self):
        missing = [r for r in self.records if not r.get("id")]
        assert not missing, f"{len(missing)} records have no id"

    def test_download_url_is_never_null(self):
        missing = [r for r in self.records if not r.get("download_url")]
        assert not missing, f"{len(missing)} records have no download_url"

    def test_document_hash_null_rate_within_threshold(self):
        from data_foundry.quality import check_null_rate

        rate = check_null_rate(self.records, "document_hash")
        assert rate <= MAX_LLM_NULL_RATE, (
            f"document_hash null rate {rate:.0%} exceeds {MAX_LLM_NULL_RATE:.0%}"
        )

    def test_no_duplicate_ids(self):
        ids = [r["id"] for r in self.records if r.get("id")]
        assert len(ids) == len(set(ids)), "Duplicate ids in universal_metadata"


# ---------------------------------------------------------------------------
# Unit tests for quality.py itself (no pipeline data needed)
# ---------------------------------------------------------------------------


class TestQualityGateUnit:
    """These run without any pipeline output — pure logic tests."""

    def _universal_record(self, **overrides) -> dict:
        base = {
            "id": "test-1",
            "cover_path": None,
            "cover_hash": None,
            "document_hash": "abc123",
            "accesses": 42,
            "size_bytes": 1024,
            "category": "manual",
            "language": "pt",
            "institution": "TRACTIAN",
            "year": "2023",
            "download_url": "http://example.com/doc.pdf",
        }
        base.update(overrides)
        return base

    def test_gate_passes_clean_records(self):
        from data_foundry.quality import FieldCheck, run_quality_gate
        from data_foundry.schemas.gold import GoldUniversalEntry

        records = [self._universal_record()]
        report = run_quality_gate(
            records,
            GoldUniversalEntry,
            [FieldCheck("document_hash", 0.0)],
            label="unit-pass",
        )
        assert report.passed

    def test_gate_catches_null_rate_violation(self):
        from data_foundry.quality import FieldCheck, run_quality_gate
        from data_foundry.schemas.gold import GoldUniversalEntry

        records = [self._universal_record(document_hash=None)]
        report = run_quality_gate(
            records,
            GoldUniversalEntry,
            [FieldCheck("document_hash", 0.0)],
            label="unit-null-rate",
        )
        assert not report.passed
        assert len(report.null_rate_violations) == 1
        assert "document_hash" in report.null_rate_violations[0]

    def test_gate_catches_schema_error(self):
        from data_foundry.quality import run_quality_gate
        from data_foundry.schemas.gold import GoldUniversalEntry

        # id is required — passing a record without it triggers a schema error.
        records = [{"cover_path": None}]
        report = run_quality_gate(records, GoldUniversalEntry, [], label="unit-schema")
        assert not report.passed
        assert len(report.schema_errors) == 1

    def test_check_null_rate_empty_list(self):
        from data_foundry.quality import check_null_rate

        assert check_null_rate([], "any.field") == 0.0

    def test_check_null_rate_nested_path(self):
        from data_foundry.quality import check_null_rate

        records = [
            {"title": {"pt": "Título", "en": None}},
            {"title": {"pt": "Outro", "en": "Other"}},
        ]
        assert check_null_rate(records, "title.en") == 0.5
        assert check_null_rate(records, "title.pt") == 0.0

    def test_halt_on_failure_exits(self):
        import pytest

        from data_foundry.quality import FieldCheck, run_quality_gate
        from data_foundry.schemas.gold import GoldUniversalEntry

        records = [self._universal_record(document_hash=None)]
        with pytest.raises(SystemExit) as exc_info:
            run_quality_gate(
                records,
                GoldUniversalEntry,
                [FieldCheck("document_hash", 0.0)],
                label="unit-halt",
                halt_on_failure=True,
            )
        assert exc_info.value.code == 1

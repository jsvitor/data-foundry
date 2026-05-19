import json
from pathlib import Path

import pytest

DATA_DIR   = Path(__file__).resolve().parent.parent / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR   = DATA_DIR / "gold"
PDF_DIR    = DATA_DIR / "raw" / "pdfs"

MIN_ENTRIES = 10

EXPECTED_FILES = [
    BRONZE_DIR / "catalog.json",
    BRONZE_DIR / "metadata.json",
    BRONZE_DIR / "hashes.json",
    SILVER_DIR / "descriptions.json",
    SILVER_DIR / "translations.json",
    SILVER_DIR / "description_translations.json",
    SILVER_DIR / "covers.json",
    GOLD_DIR   / "localized_catalog.json",
    GOLD_DIR   / "universal_metadata.json",
]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def unwrap(data):
    """Gold files are wrapped as {"run_id": ..., "records": [...]} by main.py."""
    return data.get("records", data) if isinstance(data, dict) else data


@pytest.mark.parametrize("filepath", EXPECTED_FILES)
def test_output_file_exists(filepath):
    assert filepath.exists() and filepath.stat().st_size > 0, f"{filepath.name} missing or empty"


def test_minimum_pdfs():
    assert len(list(PDF_DIR.glob("*.pdf"))) >= MIN_ENTRIES


def test_localized_catalog():
    data = unwrap(load_json(GOLD_DIR / "localized_catalog.json"))
    assert len(data) >= MIN_ENTRIES
    for entry in data:
        assert entry.get("id") and entry.get("title", {}).get("pt")


def test_universal_metadata():
    data = unwrap(load_json(GOLD_DIR / "universal_metadata.json"))
    assert len(data) >= MIN_ENTRIES
    for entry in data:
        assert entry.get("id") and entry.get("document_hash")


def test_outputs_consistent():
    loc_ids = {e["id"] for e in unwrap(load_json(GOLD_DIR / "localized_catalog.json"))}
    uni_ids = {e["id"] for e in unwrap(load_json(GOLD_DIR / "universal_metadata.json"))}
    cat_ids = {e["code"] for e in load_json(BRONZE_DIR / "catalog.json")}
    assert loc_ids == uni_ids == cat_ids

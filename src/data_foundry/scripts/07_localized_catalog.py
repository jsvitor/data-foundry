import json
from pathlib import Path

from data_foundry.config import BRONZE_DIR, GOLD_DIR, SILVER_DIR
from data_foundry.quality import FieldCheck, run_quality_gate
from data_foundry.schemas.gold import GoldLocalizedEntry


def load_json(path: Path) -> dict | list:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return [] if path.name == "catalog.json" else {}


# Fields that must be present and their acceptable null-rate ceilings.
QUALITY_CHECKS = [
    FieldCheck("title.pt", max_null_rate=0.0),   # always sourced from bronze
    FieldCheck("description.pt", max_null_rate=0.5),  # LLM-generated; 50 % tolerance
]


def main():
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    catalog = load_json(BRONZE_DIR / "catalog.json")
    if not catalog:
        print("catalog.json not found. Run 01_download.py first.")
        return

    translations = load_json(SILVER_DIR / "translations.json")
    descriptions = load_json(SILVER_DIR / "descriptions.json")
    desc_translations = load_json(SILVER_DIR / "description_translations.json")

    localized = []
    for entry in catalog:
        code = entry["code"]

        title_trans = translations.get(code, {})
        desc_data = descriptions.get(code, {})
        desc_trans = desc_translations.get(code, {})

        record = {
            "id": code,
            "title": {
                "pt": entry["title"],
                "en": title_trans.get("en"),
                "es": title_trans.get("es"),
                "fr": title_trans.get("fr"),
            },
            "description": {
                "pt": desc_data.get("description"),
                "en": desc_trans.get("en"),
                "es": desc_trans.get("es"),
                "fr": desc_trans.get("fr"),
            },
            "author": entry.get("author"),
            "source": entry.get("source"),
        }
        localized.append(record)

    # Quality gate — hard stop when structural or null-rate thresholds breach.
    run_quality_gate(
        localized,
        GoldLocalizedEntry,
        QUALITY_CHECKS,
        label="localized_catalog",
        halt_on_failure=True,
    )

    output_path = GOLD_DIR / "localized_catalog.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(localized, f, ensure_ascii=False, indent=2)

    complete = sum(
        1 for r in localized if r["title"].get("en") and r["description"].get("pt")
    )
    print(f"Done. {len(localized)} entries assembled ({complete} fully localized).")
    print(f"Output saved to {output_path}")


if __name__ == "__main__":
    main()

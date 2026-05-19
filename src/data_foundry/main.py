import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"

STEPS = [
    ("01_download.py", "Scrape catalog and download PDFs", True),
    ("02_hash.py", "Calculate document hashes", True),
    ("03_describe.py", "Generate descriptions via vision LLM", False),
    ("04_translate.py", "Translate titles", False),
    ("05_translate_descriptions.py", "Translate descriptions", False),
    ("06_covers.py", "Extract cover pages", False),
    ("07_localized_catalog.py", "Assemble localized catalog", True),
    ("08_universal_metadata.py", "Assemble universal metadata", True),
]


def run_step(script: str, description: str) -> bool:
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"  Running: {script}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)],
        cwd=str(SCRIPTS_DIR.parent),
    )
    return result.returncode == 0


def main():
    print("Domínio Público Data Pipeline")
    print("=" * 60)

    results = {}
    for script, description, critical in STEPS:
        success = run_step(script, description)

        if success:
            results[script] = "ok"
        elif critical:
            results[script] = "failed:halt"
            print(f"\n[CRITICAL] {script} failed. Stopping pipeline.")
            break
        else:
            results[script] = "failed:skipped"
            print(f"\n[WARNING] {script} failed. Continuing with reduced output.")

    print(f"\n{'=' * 60}")
    print("Pipeline Summary")
    print(f"{'=' * 60}")
    icons = {"ok": "+", "failed:halt": "X", "failed:skipped": "~"}
    for script, status in results.items():
        print(f"  [{icons[status]}] {script}: {status}")


if __name__ == "__main__":
    main()

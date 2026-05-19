import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from data_foundry.config import DATA_DIR, LLM_BASE_URL, LLM_MODEL, OUTPUT_DIR

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
META_DIR = DATA_DIR / "meta"
RUNS_LOG = META_DIR / "runs.jsonl"

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

OUTPUT_FILES = [
    OUTPUT_DIR / "localized_catalog.json",
    OUTPUT_DIR / "universal_metadata.json",
]


def generate_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    short_id = uuid.uuid4().hex[:4]
    return f"{ts}_{short_id}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(event: dict) -> None:
    META_DIR.mkdir(parents=True, exist_ok=True)
    with open(RUNS_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")


def run_step(script: str, description: str, run_id: str) -> bool:
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"  Running: {script}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)],
        cwd=str(SCRIPTS_DIR.parent),
        env={**os.environ, "RUN_ID": run_id},
    )
    return result.returncode == 0


def inject_run_id(filepath: Path, run_id: str) -> None:
    if not filepath.exists():
        return
    with open(filepath) as f:
        data = json.load(f)
    output = {"run_id": run_id, "records": data} if isinstance(data, list) else {"run_id": run_id, **data}
    with open(filepath, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def main():
    run_id = generate_run_id()

    print("Domínio Público Data Pipeline")
    print(f"run_id: {run_id}")
    print("=" * 60)

    append_event({
        "event": "run_started",
        "run_id": run_id,
        "ts": now_iso(),
        "llm_model": LLM_MODEL,
        "llm_base_url": LLM_BASE_URL,
    })

    results = {}
    halted = False

    for script, description, critical in STEPS:
        success = run_step(script, description, run_id)

        if success:
            status = "ok"
        elif critical:
            status = "failed:halt"
        else:
            status = "failed:skipped"

        results[script] = status
        append_event({
            "event": "step_completed",
            "run_id": run_id,
            "ts": now_iso(),
            "step": script,
            "status": status,
        })

        if status == "failed:halt":
            print(f"\n[CRITICAL] {script} failed. Stopping pipeline.")
            halted = True
            break
        elif status == "failed:skipped":
            print(f"\n[WARNING] {script} failed. Continuing with reduced output.")

    for filepath in OUTPUT_FILES:
        inject_run_id(filepath, run_id)

    append_event({
        "event": "run_finished",
        "run_id": run_id,
        "ts": now_iso(),
        "halted": halted,
    })

    print(f"\n{'=' * 60}")
    print(f"Pipeline Summary  [run_id: {run_id}]")
    print(f"{'=' * 60}")
    icons = {"ok": "+", "failed:halt": "X", "failed:skipped": "~"}
    for script, status in results.items():
        print(f"  [{icons[status]}] {script}: {status}")


if __name__ == "__main__":
    main()

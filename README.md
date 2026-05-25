# Data Foundry

A data pipeline that ingests documents from Brazil's public domain library,
enriches them with LLM-generated descriptions and translations, and produces
two structured JSON datasets.

## Quick start

```bash
cp .env.example .env   # add LLM credentials
```

**Using a local model (Ollama):**
```bash
make setup-ollama      # starts Ollama and pulls the model defined in .env (first run only)
make run               # builds containers, runs pipeline end-to-end
make test              # validates outputs
```

**Using a cloud LLM (OpenAI, etc.):**
```bash
make run               # builds containers, runs pipeline end-to-end
make test              # validates outputs
```

Docker + Docker Compose required. No local Python needed.

---

## Architecture

```
data/
├── raw/              ← source PDFs as downloaded
├── bronze/           ← structured catalog, metadata, content hashes
├── silver/           ← LLM enrichment: descriptions, translations, cover images
├── gold/             ← consumer-facing output datasets
└── meta/             ← runs.jsonl append-only execution audit log
```

Eight scripts, one linear orchestrator (`main.py`), two output datasets:

- `gold/localized_catalog.json` — titles and descriptions in PT/EN/ES/FR
- `gold/universal_metadata.json` — hashes, cover paths, access counts, provenance

Individual steps are available via `make download`, `make describe`, etc.

---

## Design decisions

### Medallion layers

The given scripts wrote everything to `data/output/`. Layer boundaries were
invisible — no way to tell source data from enriched data from final outputs
without reading every script.

```
raw/     — PDFs as downloaded, untouched
bronze/  — structured catalog, metadata, content hashes
silver/  — LLM enrichment: descriptions, translations, cover images
gold/    — consumer-facing output datasets
```

Layer boundaries are natural quality checkpoints. A silver-to-gold gate
runs before writing gold outputs: Pydantic validates every record's structure,
and null-rate thresholds (e.g. `title.pt` must be 0% null, `description.pt`
below 50%) trigger a hard stop with a structured report when breached.
Cover paths are stored as keys relative to `DATA_DIR` (e.g. `silver/covers/abc.png`),
which map directly to S3 object keys when cloud storage is introduced.

### Pipeline failure contract

`main.py` separates critical steps from non-critical ones:

| Steps | Behaviour on failure | Reason |
|---|---|---|
| `01_download`, `02_hash` | Halt | No raw data = nothing to process |
| `03_describe` → `06_covers` | Log and continue | Enrichment failures produce partial output, not corrupt output |
| `07_localized_catalog`, `08_universal_metadata` | Halt | Assembly failure = no output datasets |

A pipeline that stops on a translation failure wastes the download and hash
work. A pipeline that continues when assembly fails silently produces empty
outputs. The split captures the actual failure semantics of each step.

### Versioning via run_id and runs.jsonl

Every execution generates a `run_id` (UTC timestamp + 4-char hex). It flows into:

- Both gold output files as a top-level field — every record is traceable to its run
- `data/meta/runs.jsonl` — one event per run start, step completion, and run finish

`runs.jsonl` uses an event-log model rather than a single record per run.
If the pipeline is killed mid-execution, events already written survive on disk:

```jsonl
{"event": "run_started",    "run_id": "20260519T143022_a3f1", "llm_model": "gpt-4o", ...}
{"event": "step_completed", "run_id": "20260519T143022_a3f1", "step": "03_describe.py", "status": "ok"}
{"event": "run_finished",   "run_id": "20260519T143022_a3f1", "halted": false}
```

### LLM lineage at the record level

Descriptions and translations carry `llm_metadata` — model name, base URL,
`run_id`, and `generated_at`. Descriptions also carry `vision_used: bool`.

Without this, there is no way to explain a bad description or compare outputs
across model versions. With it, you can answer "which records were generated
with gemma2:2b?" without re-running anything.

### Model choice

`03_describe.py` sends PDF cover pages to a vision LLM — so the model matters.

`gemma4:e2b` is the right choice: native vision support, 128K context window.
Requires significant RAM — not suitable for machines with under 16GB.

`gemma2:2b` runs locally but ignores images entirely since it is text-only.
Descriptions are generated from title and metadata only. The `vision_used` field
in each record makes this explicit.

Set your model in `.env` before running:

```bash
LLM_MODEL=gemma4:e2b  # recommended — full vision pipeline
LLM_MODEL=gemma2:2b   # local fallback — text-only descriptions
```

---

## Known trade-offs

**Resume cache invalidation**
Scripts use document code as the skip key. A re-download of the same document
with different content won't invalidate the description or translation cache.
SHA-256 content-hash keys would fix this; not yet implemented.

**Serial LLM calls**
Steps 03–05 process documents one at a time. The bottleneck is LLM API latency,
not disk or CPU. `ThreadPoolExecutor` with a configurable worker count would
reduce total pipeline time significantly at scale.

**JSON at 10 documents**
At 1000+ documents: slow reads/writes, no schema enforcement, no ACID guarantees.
Parquet + Iceberg on S3 is the production path.

---

## Challenge targets covered

| Target | Implementation |
|---|---|
| Data Architecture | Medallion layers (raw/bronze/silver/gold), explicit layer boundaries, cover paths S3-ready |
| Versioning | `run_id` on every output, `runs.jsonl` event audit log, `llm_metadata` per LLM-generated record |
| Data Quality | Critical vs non-critical failure contract, `vision_used` flag for LLM auditability, Pydantic schemas per medallion layer, silver-to-gold null-rate gate, content quality tests |

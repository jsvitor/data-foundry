# Data Foundry Pipeline

## How to Run

Requires Docker and Docker Compose.

```bash
make setup-ollama   # starts Ollama and pulls the model defined in .env
make run            # run pipeline end-to-end
make test           # validate outputs
```

Individual steps: `make download`, `make hash`, `make describe`, etc.

### Model

`03_describe.py` sends PDF cover pages to a vision LLM — so the model matters.

`gemma4:e2b` is the right choice: native vision support, 128K context window.
Requires significant RAM — not suitable for machines with 8GB.

`gemma2:2b` runs fine locally but ignores the images entirely since it's
text-only. Descriptions will be generated from title and metadata only.

Set your model in `.env` before running:

```bash
LLM_MODEL=gemma4:e2b  # recommended
LLM_MODEL=gemma2:2b   # local fallback — text-only descriptions
```

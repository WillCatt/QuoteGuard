# QuoteGuard

QuoteGuard is a guardrailed retrieval-augmented chatbot for insurance quote support. It is designed around a narrow contract: grounded answers only, no advice, no chatbot-generated prices, mandatory citations, prompt-injection resistance, and human handoff outside the state machine.

## Contract

The six guarantees are defined in [docs/contract.md](/Users/williamcatt/Documents/Projects/PDF%20RAG%20with%20Guardrails/docs/contract.md). The implementation reflects them through:

- deterministic orchestration in `src/quoteguard/orchestration`
- layered guardrails in `src/quoteguard/guardrails`
- retrieval and citation discipline in `src/quoteguard/retrieval`
- a strict pricing boundary in `src/quoteguard/api/pricing.py`

## Repository Layout

The repository is implementation-first:

- `src/quoteguard/`: package code
- `tests/`: unit and integration coverage
- `data/`: local-only corpora, processed artefacts, eval datasets
- `evals/`: evaluation harnesses and report
- `docs/`: contract, design choices, corpus notes, architecture, future work
- `scripts/`: ingestion and local smoke tools

## Local Setup

The intended workflow uses `uv`, `ruff`, and `pytest`:

```bash
uv sync --all-extras
uv run pytest
uv run streamlit run src/quoteguard/ui/app.py
```

If those tools are not yet installed, the codebase still supports basic standard-library validation:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/smoke_chat.py
```

## Current Status

This repo now includes:

- package scaffolding for ingestion, retrieval, orchestration, guardrails, API, UI, and observability
- selectable parser, embedder, and vector-store backends with automatic fallback when optional dependencies are missing
- seed evaluation datasets and harness scripts
- deterministic fallback implementations that work without external ML/runtime libraries
- documentation structure aligned with the original project specification

## Ingestion Workflow

Build the local index with explicit backends when you want to force a parser or storage path:

```bash
python3 scripts/build_index.py \
  --parser-backend text_fallback \
  --embedder-backend hashing \
  --vector-store-backend jsonl
```

Once dependencies are installed, swap `text_fallback` for `pymupdf4llm` or `docling`, `hashing` for `sentence_transformers`, and `jsonl` for `chroma`.

## Next Iteration Points

- fetch and inspect real insurer PDFs, then compare `pymupdf4llm` vs `docling` on the actual corpus
- replace seed eval datasets with manually reviewed corpus-backed examples
- wire the LLM client into real Ollama calls instead of the current stubbed cache-first fallback
- add real Streamlit and FastAPI execution in an environment with dependencies installed

# QuoteGuard

QuoteGuard is being rebuilt from the ground up as a notebook-first project.

The current scope is intentionally narrow:

- compare PDF parsers on the local insurer corpus
- record corpus audit findings
- inspect parser outputs manually
- decide the default parser before building chunking, retrieval, chat, or guardrails

## Current Phase

Phase 1 is a single lab notebook:

- [notebooks/01_parser_lab.ipynb](/Users/williamcatt/Documents/Projects/QuoteGuard/notebooks/01_parser_lab.ipynb)

This notebook is the working surface for:

- corpus audit
- parser comparison
- output inspection
- export of parser-lab artefacts into `data/processed/parser_lab`

## Minimal Repository Shape

- `data/raw_pdfs/`
  Raw insurer PDFs. These should remain immutable.
- `data/processed/parser_lab/`
  Notebook outputs, audit summaries, parser runs.
- `notebooks/01_parser_lab.ipynb`
  The main experiment notebook.
- `docs/full_project_writeup.md`
  The portfolio writeup that will be updated as phases are completed.
- `Project_Specifications.md`
  Original project brief for reference.

## Corpus Note

If `data/raw_pdfs/` still contains the older legacy files, replace them with the actual
target insurer PDFs before making any parser decision.

## Setup

Install dependencies into the local venv:

```bash
python3 -m pip install -e .
```

Open Jupyter Lab:

```bash
.venv/bin/python -m jupyter lab
```

Or open the notebook directly in VS Code using the `.venv` interpreter.

## Working Rule

Do not branch back out into app structure until the parser choice is made from real corpus evidence.

Once the parser is chosen, the next phases are:

1. chunking strategy
2. retrieval sanity checks
3. gold question set
4. retrieval benchmark
5. LLM and guardrails

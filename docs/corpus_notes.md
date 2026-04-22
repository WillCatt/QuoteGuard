# Corpus Notes

This file captures corpus inspection notes before a parser choice is locked in.

## Scope

- Product vertical: `home_contents`
- Target corpus size: 5 to 8 Australian insurer PDS documents
- PDFs should not be committed to the repository

## Current Status

- Date checked: 2026-04-22
- Active repo scope remains `home_contents`
- `data/raw_pdfs/` currently contains legacy Allianz business PDFs that are out of scope for the target corpus
- `data/processed/parsed/` does not yet contain real parsed insurer output
- Local parser dependencies were not installed at inspection time:
  - `pymupdf4llm`
  - `docling`
- Local retrieval/runtime extras also missing at inspection time:
  - `chromadb`
  - `sentence_transformers`
  - `ollama`
  - `uv`

## Target Official Corpus

- AAMI Home Contents Insurance PDS
- Allianz Home Insurance PDS
- Budget Direct Home and Contents Insurance PDS
- Coles Home Insurance PDS
- NRMA Home Insurance PDS
- QBE Contents Insurance PDS
- RACV Home Insurance PDS
- Suncorp Home & Contents Insurance PDS
- Youi Home Insurance PDS

## Readiness Notes

- Real PDF ingestion is blocked until at least one PDF-capable parser backend is installed locally.
- `text_fallback` is adequate for plain-text fixtures and tests, but not for real binary insurer PDFs.
- The next corpus step is to fetch the official PDFs into `data/raw_pdfs/`, archive or exclude the legacy non-home-contents files, then run parser comparison on a 3-document sample.

## Inspection Checklist

- Heading hierarchy quality
- Multi-column layout issues
- Table extraction quality
- Footnotes and cross-references
- Page-number consistency
- OCR/scanned-page quality
- Copyright and usage notices

## Expected Risks

- Insurance tables will likely break naive reading order
- Nested exclusions are easy to flatten incorrectly
- Section path fidelity matters more than paragraph beauty
- A few problematic PDFs should be dropped instead of forcing the parser to accommodate everything

## Pending Manual Notes

Use this document to record concrete findings per insurer once the corpus is fetched.

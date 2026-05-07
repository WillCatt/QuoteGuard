# QuoteGuard Full Project Writeup

## Project Summary

QuoteGuard is being rebuilt from the ground up as a portfolio project for Australian
insurance PDF retrieval. The deliberate approach is:

1. decide the parser on real evidence
2. then design chunking
3. then retrieval
4. then LLM and guardrails

This file should stay lightweight during the parser phase and grow only when the next
phase is justified by results.

## Current Phase

Phase 1: parser lab

Current scope:

- corpus audit
- parser comparison
- manual inspection of extracted structure

Out of scope for now:

- app UI
- orchestration
- pricing engine
- retrieval benchmark suite
- guardrails

## Corpus

Corpus location:

- `data/raw_pdfs/`

Rules:

- raw PDFs are immutable
- all outputs go to `data/processed/parser_lab/`

## Notebook Workflow

Primary working surface:

- `notebooks/01_parser_lab.ipynb`

The notebook should be used to:

- inspect the corpus
- compute audit summaries
- run parser comparisons
- save parsed outputs
- export run summaries

## Phase Log

### Phase 1: Parser Lab

Goal:

- choose the default parser based on actual insurer PDFs

Questions to answer:

- which parser preserves reading order best?
- which parser keeps headings and page boundaries usable?
- how noisy are headers and footers?
- how bad are tables and multi-column pages?
- which parser is good enough to move to chunking?

Evidence to capture:

- corpus audit table
- parse timing table
- extracted character counts
- parser output samples
- manual scoring notes

Decision:

- parser chosen:
- reason:

### Phase 2: Chunking

Not started yet.

### Phase 3: Retrieval

Not started yet.

### Phase 4: LLM + Guardrails

Not started yet.

## Notes and Reflections

Use this section as a running journal for:

- what worked
- what failed
- what was surprising in the PDFs
- why a parser was accepted or rejected

## Portfolio Angle

What this phase already demonstrates:

- disciplined scope control
- willingness to reduce architecture until evidence exists
- empirical parser comparison on a real domain corpus

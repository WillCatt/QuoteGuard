# QuoteGuard Full Project Writeup

## 1. Project Summary

QuoteGuard is a guardrailed retrieval-augmented chatbot for Australian home contents
insurance quote support. The system is grounded in insurer PDS PDFs, avoids advice,
does not generate pricing in chat, cites sources, resists prompt injection, and hands
pricing to a deterministic pricing engine.

## 2. Problem Framing

Describe:

- the business problem
- why insurance quoting support needs retrieval grounding
- why advice boundaries matter
- why deterministic pricing separation matters

## 3. Product Contract

Reference the six guarantees from `docs/contract.md` and explain how they shaped the
architecture.

## 4. Architecture Overview

Cover:

- ingestion
- retrieval
- orchestration
- guardrails
- pricing boundary
- observability

Add diagrams, screenshots, and links to reports as the project matures.

## 5. Phase Log

### Phase 1: Corpus Audit

Goals:

- collect official PDS PDFs
- audit corpus quality and layout difficulty

Evidence:

- corpus summary table
- notes from `docs/corpus_notes.md`

### Phase 2: Parser Comparison

Goals:

- compare PyMuPDF4LLM vs Docling
- choose the default parser based on retrieval plus manual quality

Evidence:

- `reports/parser_comparison.md`
- benchmark charts
- selected parser rationale

### Phase 3: Chunking Iteration

Goals:

- compare fixed-size, section-aware, page-based, and hybrid chunking
- preserve headings and page metadata

Evidence:

- `reports/chunk_inspection.md`
- sample chunks
- benchmark results

### Phase 4: Retrieval Benchmarking

Goals:

- run 20 real sanity questions across configurations
- compare Hit@1, Hit@3, Recall@5, MRR@5, nDCG@5, latency, context precision, and context recall

Evidence:

- `experiments/retrieval_lab/runs/`
- dashboard screenshots

### Phase 5: Guardrailed QA Flow

Goals:

- connect retrieval into the deterministic state machine
- validate prompt injection resistance, advice refusal, citation enforcement, and pricing boundary

Evidence:

- adversarial eval outputs
- audit logs

### Phase 6: Local LLM Integration

Goals:

- wire real Ollama calls
- preserve grounding and handoff constraints

Evidence:

- example sessions
- failure cases and mitigations

## 6. Evaluation Methodology

Describe:

- gold question creation
- parser scoring method
- chunk inspection method
- retrieval metrics
- adversarial testing

## 7. Key Findings

Summarize:

- which parser won and why
- which chunking strategy won and why
- which backend combinations were too slow or brittle
- what guardrail failures were found and fixed

## 8. Tradeoffs and Design Decisions

Discuss:

- why the repo stayed modular but not over-fragmented
- why retrieval quality was prioritized before full chat polish
- why pricing is deterministic and outside the chat model

## 9. Failure Analysis

Document:

- parser failures
- table extraction problems
- chunking failure modes
- retrieval misses
- hallucination or citation issues
- prompt injection attempts

## 10. Demo Guide

Explain how to:

- build the index
- generate the benchmark report
- run the retrieval lab dashboard
- run tests
- reproduce the best configuration

## 11. Portfolio Reflection

Describe:

- what this project demonstrates technically
- what you would improve next
- how you would productionize the system

## 12. Appendix

Include:

- metric tables
- corpus list
- configuration snapshots
- screenshots
- links to experiment runs

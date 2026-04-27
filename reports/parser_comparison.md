# Parser Comparison Report

Date:
Run IDs:
Corpus version:

## Goal

Compare candidate parsers on the real insurer PDF corpus and choose a default parser based
on retrieval outcomes plus manual inspection, not speed alone.

## Parsers Compared

- PyMuPDF4LLM
- Docling
- Optional baseline:

## Corpus Coverage

List PDFs inspected:

## Quantitative Summary

| Parser | Total parse time | Parse time / PDF | Parse time / page | Characters extracted | Sections | Tables | Failed pages | Empty pages | Output size |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PyMuPDF4LLM |  |  |  |  |  |  |  |  |  |
| Docling |  |  |  |  |  |  |  |  |  |

## Manual Quality Scoring

Use a 1 to 5 scale.

| Parser | Reading order | Heading preservation | Paragraph breaks | Bullet lists | Table quality | Cross-page continuity | Header/footer noise | Page metadata preservation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PyMuPDF4LLM |  |  |  |  |  |  |  |  |
| Docling |  |  |  |  |  |  |  |  |

## Page-Level Inspection Notes

Inspect:

- first 3 pages of each PDF
- table-heavy pages
- exclusions pages
- definitions pages
- multi-column pages
- footnote pages
- schedule/limits pages
- failed parser pages

Record:

- repeated boilerplate
- broken words
- missing headings
- table corruption
- page number mismatch
- warnings/errors

## Retrieval Impact

Summarize how each parser affected:

- Hit@1
- Hit@3
- Recall@5
- MRR@5
- nDCG@5
- context precision
- context recall
- latency

## Decision

Chosen parser:

Reasoning:

- retrieval quality
- manual inspection
- failure profile
- speed tradeoff

## Follow-up Actions

- [ ] Update `docs/design_decisions.md`
- [ ] Rebuild default index
- [ ] Re-run retrieval sanity benchmark

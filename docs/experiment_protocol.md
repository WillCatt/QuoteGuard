# Experiment Protocol

This document defines the minimum evidence to collect for corpus audit, parser comparison,
chunking iteration, retrieval benchmarking, and gold question creation.

## 1. Corpus Audit

For every PDF in `data/raw_pdfs`, record:

- file name
- file size
- page count
- source/version/date if available
- native PDF or scanned PDF
- text-heavy, table-heavy, form-heavy, image-heavy
- has multi-column layout
- has repeated headers/footers
- has page numbers
- has tables across page breaks
- expected retrieval difficulty: easy, medium, hard
- checksum/hash

Rules:

- raw PDFs must remain immutable
- parsed outputs must be stored separately

Also record at experiment level:

- total parse time
- total indexing time
- retrieval latency: p50 and p95
- storage size
- retrieval metrics
- failure notes
- example retrieved chunks

## 2. Parser Comparison

Compare at least:

- PyMuPDF4LLM
- Docling

Optional baseline:

- basic PyMuPDF or pypdf extraction

For each parser, record:

- parse time per PDF
- parse time per page
- total extracted characters
- number of sections detected
- number of tables detected
- failed pages
- empty pages
- warnings/errors
- output size

Manual quality score from 1 to 5 for:

- reading order
- heading preservation
- paragraph breaks
- bullet lists
- table quality
- cross-page continuity
- header/footer noise
- page metadata preservation

Decision rule:

- parser choice must be based on retrieval outcomes and manual inspection, not speed alone

## 3. Chunking Iteration

Test:

- fixed-size chunks: 300, 500, 800 tokens
- overlap: 0%, 10%, 20%, 25%
- section-aware chunks
- page-based chunks
- hybrid section-aware chunks with a max token cap

For each run, record:

- number of chunks
- average tokens per chunk
- median tokens per chunk
- min and max tokens
- number of tiny chunks under 50 tokens
- number of oversized chunks
- duplicate chunk rate
- whether headings are retained
- whether page metadata is retained
- whether tables are split badly
- sample chunks

Preferred starting point:

- section-aware chunking
- 500 to 800 token max
- 10% to 20% overlap
- preserve document title, section heading, and page number in metadata
- prepend heading path to chunk text before embedding

## 4. Retrieval Lab Benchmark

Run the same 20 sanity questions against every parser/chunker configuration.

Track:

- Hit@1
- Hit@3
- Recall@5
- MRR@5
- nDCG@5
- context precision
- context recall
- latency_ms

Required run structure:

```text
experiments/
  retrieval_lab/
    runs/
      {run_id}/
        config.json
        metrics.json
        results.csv
        failures.md
        sample_retrievals.md
```

## 5. Parsed and Chunk Inspection

Create:

- `reports/parser_comparison.md`
- `reports/chunk_inspection.md`

Inspect:

- first 3 pages of each PDF
- table-heavy pages
- exclusions pages
- definitions pages
- multi-column pages
- footnote pages
- schedule/limits pages
- failed parser pages
- 10 random chunks
- 10 shortest chunks
- 10 longest chunks

Record:

- repeated boilerplate
- broken words
- missing headings
- table corruption
- page number mismatch
- chunks with no useful meaning
- chunks that mix unrelated sections
- chunks that need parent headings

## 6. Twenty Real Sanity Questions

Create a gold set with 20 questions:

- 6 direct lookup
- 4 definition
- 4 exclusion/condition
- 3 table or limit
- 2 multi-section
- 1 unanswerable

Each question should include:

- question_id
- question
- expected_answer
- answerable
- source_pdf
- supporting_pages
- supporting_section_heading
- required_evidence_text
- difficulty
- category
- ambiguity_notes

Important:

- ground truth must be based on source document page/span evidence
- chunk IDs are not stable enough to be the source of truth

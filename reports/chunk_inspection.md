# Chunk Inspection Report

Date:
Run IDs:
Corpus version:

## Goal

Evaluate chunking strategies for retrieval usefulness and metadata fidelity.

## Strategies Compared

- fixed-size 300
- fixed-size 500
- fixed-size 800
- section-aware
- page-based
- hybrid section-aware with max token cap

## Quantitative Summary

| Strategy | Chunk size | Overlap | Chunks | Avg tokens | Median tokens | Min | Max | Tiny <50 | Oversized | Duplicate rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |  |  |

## Metadata and Structural Checks

For each strategy record:

- headings retained
- page metadata retained
- tables split badly
- heading path prepended before embedding

## Manual Inspection

Inspect:

- 10 random chunks
- 10 shortest chunks
- 10 longest chunks
- chunk samples from exclusions pages
- chunk samples from definitions pages
- chunk samples from table-heavy pages

Record:

- chunks with no useful meaning
- chunks mixing unrelated sections
- chunks needing parent headings
- repeated boilerplate
- broken words
- table corruption

## Retrieval Impact

Summarize:

- Hit@1
- Hit@3
- Recall@5
- MRR@5
- nDCG@5
- latency

## Preferred Strategy

Preferred starting point:

- section-aware chunking
- 500 to 800 token max
- 10% to 20% overlap
- preserve document title, section heading, and page number in metadata
- prepend heading path to chunk text before embedding

Decision:

Reasoning:

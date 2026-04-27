# Retrieval Lab

This directory holds repeatable parser, chunking, and retrieval experiments for the
`home_contents` corpus.

## Purpose

Each experiment run should be self-describing and reproducible. The goal is to compare
parser, chunker, embedder, vector store, and retrieval configurations on the same set of
sanity questions and corpus PDFs.

## Run Layout

Every experiment run should create:

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

## Required `config.json` Fields

- `run_id`
- `date`
- `parser_name`
- `parser_version`
- `chunking_method`
- `chunk_size`
- `overlap`
- `embedding_model`
- `vector_store`
- `retrieval_method`
- `top_k`
- `reranking_used`
- `product_type`
- `corpus_files`

## Required `metrics.json` Sections

- corpus audit summary
- parser comparison summary
- chunking summary
- retrieval benchmark metrics
- latency and storage metrics
- failure notes summary

## Required `results.csv` Columns

- `question_id`
- `question`
- `expected_answer`
- `expected_doc`
- `expected_pages`
- `retrieved_chunk_ids`
- `retrieved_pages`
- `hit_at_1`
- `hit_at_3`
- `recall_at_5`
- `mrr_at_5`
- `ndcg_at_5`
- `latency_ms`
- `notes`

## Ground Truth Rule

Ground truth must be anchored to source document plus page/span evidence, not to chunk IDs.
Chunk IDs may change between experiments when parser or chunking settings change.

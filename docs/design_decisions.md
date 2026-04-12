# Design Decisions

## State Machine Over Open Agent

QuoteGuard is intentionally implemented as a deterministic state machine. The conversation can sound natural, but transitions are code-driven rather than model-driven so the allowed behaviour is auditable.

## Local-First Runtime

The target development environment is local Ollama to demonstrate self-contained infrastructure. Hosted deployment can swap to an API model if needed, but local development remains the primary design point.

## Retrieval Abstraction

Dense retrieval, sparse retrieval, fusion, and reranking are composed through a service boundary so each stage can be measured independently in evaluation.

## Dependency-Tolerant Bootstrapping

The repo includes pure-Python fallbacks where possible so the skeleton remains runnable before optional libraries are installed. These fallbacks are scaffolding, not the final benchmarked implementation.

## Evaluation As A First-Class Artefact

`evals/REPORT.md`, seed datasets, and audit logs are part of the architecture, not supporting documents. The project is meant to prove behaviour, not just demo it.

"""Benchmark helpers for parser, chunking, and retrieval comparison."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
import statistics
import time

from quoteguard.config.settings import settings
from quoteguard.ingestion.chunker import HierarchicalChunker, token_count
from quoteguard.ingestion.embedder import EmbedderBackend
from quoteguard.ingestion.models import Chunk, ParsedDocument
from quoteguard.ingestion.parser import ParserBackend, get_parser
from quoteguard.retrieval.service import RetrievalService
from quoteguard.retrieval.vector_store import VectorStoreBackend


DEFAULT_RETRIEVAL_QUESTIONS = [
    "Does the policy cover theft?",
    "Are jewellery items limited?",
    "What is excluded for flood or storm damage?",
    "Are portable valuables covered away from home?",
    "How are temporary accommodation benefits described?",
]


def load_questions(path: Path | None = None) -> list[str]:
    if path and path.exists():
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        questions = [row["question"] for row in rows if row.get("question")]
        if questions:
            return questions
    return list(DEFAULT_RETRIEVAL_QUESTIONS)


def save_benchmark_report(report: dict, output_path: Path | None = None) -> Path:
    target = output_path or settings.benchmark_report_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return target


def load_benchmark_report(path: Path | None = None) -> dict | None:
    target = path or settings.benchmark_report_path
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def _safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return statistics.fmean(values)


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * quantile))))
    return float(ordered[index])


def _preview(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _document_summary(document: ParsedDocument, chunks: list[Chunk], parse_ms: float) -> dict:
    section_word_counts = [token_count(section.text) for section in document.sections]
    return {
        "source_pdf": document.source_pdf,
        "parser_backend": document.parser_backend,
        "status": "ok",
        "parse_ms": round(parse_ms, 2),
        "sections": len(document.sections),
        "words": sum(section_word_counts),
        "avg_words_per_section": round(_safe_mean([float(value) for value in section_word_counts]), 2),
        "chunks": len(chunks),
        "avg_chunk_tokens": round(_safe_mean([float(chunk.token_count) for chunk in chunks]), 2),
        "max_chunk_tokens": max((chunk.token_count for chunk in chunks), default=0),
        "sample_sections": [
            {
                "heading": section.heading,
                "page_number": section.page_number,
                "section_path": section.section_path,
                "preview": _preview(section.text),
            }
            for section in document.sections[:6]
        ],
    }


def _error_summary(path: Path, parse_ms: float, exc: Exception) -> dict:
    return {
        "source_pdf": path.name,
        "status": "error",
        "parse_ms": round(parse_ms, 2),
        "error": f"{type(exc).__name__}: {exc}",
        "sections": 0,
        "words": 0,
        "chunks": 0,
        "sample_sections": [],
    }


def _reset_store_artifact(store_path: Path, backend: VectorStoreBackend) -> None:
    if backend == VectorStoreBackend.CHROMA:
        target = store_path if store_path.suffix == "" else store_path.parent
        if target.exists():
            shutil.rmtree(target)
        return
    if store_path.exists():
        store_path.unlink()


def benchmark_backend(
    raw_dir: Path,
    *,
    parser_backend: ParserBackend,
    questions: list[str],
    product_type: str = "home_contents",
    embedder_backend: EmbedderBackend = EmbedderBackend.HASHING,
    vector_store_backend: VectorStoreBackend = VectorStoreBackend.JSONL,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    benchmark_dir: Path | None = None,
) -> dict:
    started_at = datetime.now(UTC).isoformat()
    parser = get_parser(parser_backend)
    chunker = HierarchicalChunker(max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    target_dir = benchmark_dir or settings.benchmark_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    documents: list[ParsedDocument] = []
    document_summaries: list[dict] = []
    parse_ms_total = 0.0

    for path in sorted(raw_dir.iterdir()):
        if path.is_dir() or path.name.startswith("."):
            continue
        doc_started = time.perf_counter()
        try:
            document = parser.parse(path, product_type=product_type)
            parse_ms = (time.perf_counter() - doc_started) * 1000
            parse_ms_total += parse_ms
            documents.append(document)
        except Exception as exc:  # noqa: BLE001
            parse_ms = (time.perf_counter() - doc_started) * 1000
            parse_ms_total += parse_ms
            document_summaries.append(_error_summary(path, parse_ms, exc))
            continue

        doc_chunks = chunker.chunk_document(document)
        document_summaries.append(_document_summary(document, doc_chunks, parse_ms))

    chunks_started = time.perf_counter()
    chunks = chunker.chunk_documents(documents)
    chunk_ms_total = (time.perf_counter() - chunks_started) * 1000

    store_path = target_dir / f"{parser_backend.value}_{embedder_backend.value}_{vector_store_backend.value}.jsonl"
    _reset_store_artifact(store_path, vector_store_backend)

    retrieval_error: str | None = None
    query_runs: list[dict] = []
    index_ms_total = 0.0
    retrieval_ms_total = 0.0
    retrieval_latency_values: list[float] = []
    actual_parser_backends = sorted({document.parser_backend for document in documents})

    retrieval_started = time.perf_counter()
    try:
        index_started = time.perf_counter()
        retrieval = RetrievalService(
            chunks,
            store_path=store_path,
            embedder_backend=embedder_backend,
            vector_store_backend=vector_store_backend,
        )
        index_ms_total = (time.perf_counter() - index_started) * 1000

        for question in questions:
            query_started = time.perf_counter()
            results = retrieval.query(question, k=5, filters={"product_type": product_type})
            latency_ms = (time.perf_counter() - query_started) * 1000
            retrieval_latency_values.append(latency_ms)
            query_runs.append(
                {
                    "question": question,
                    "latency_ms": round(latency_ms, 2),
                    "top_hit_source_pdf": results[0]["chunk"]["source_pdf"] if results else None,
                    "top_hit_score": round(results[0]["score"], 4) if results else 0.0,
                    "results": [
                        {
                            "rank": index + 1,
                            "score": round(result["score"], 4),
                            "source_pdf": result["chunk"]["source_pdf"],
                            "page_number": result["chunk"]["page_number"],
                            "section_path": result["chunk"]["section_path"],
                            "preview": _preview(result["chunk"]["text"]),
                        }
                        for index, result in enumerate(results)
                    ],
                }
            )
    except Exception as exc:  # noqa: BLE001
        retrieval_error = f"{type(exc).__name__}: {exc}"
    retrieval_ms_total = (time.perf_counter() - retrieval_started) * 1000

    total_words = sum(token_count(section.text) for document in documents for section in document.sections)
    total_sections = sum(len(document.sections) for document in documents)
    chunk_token_values = [chunk.token_count for chunk in chunks]
    document_parse_latencies = [summary["parse_ms"] for summary in document_summaries if summary["status"] == "ok"]

    return {
        "started_at": started_at,
        "parser_backend_requested": parser_backend.value,
        "parser_backend_used": actual_parser_backends or [parser_backend.value],
        "embedder_backend": embedder_backend.value,
        "vector_store_backend": vector_store_backend.value,
        "chunker": {
            "max_tokens": max_tokens,
            "overlap_tokens": overlap_tokens,
        },
        "status": "error" if retrieval_error else "ok",
        "error": retrieval_error,
        "summary": {
            "documents_total": len(document_summaries),
            "documents_parsed": len(documents),
            "documents_failed": sum(1 for summary in document_summaries if summary["status"] != "ok"),
            "sections_total": total_sections,
            "words_total": total_words,
            "chunks_total": len(chunks),
            "avg_parse_ms_per_document": round(_safe_mean(document_parse_latencies), 2),
            "parse_ms_total": round(parse_ms_total, 2),
            "chunk_ms_total": round(chunk_ms_total, 2),
            "index_ms_total": round(index_ms_total, 2),
            "retrieval_ms_total": round(retrieval_ms_total, 2),
            "avg_retrieval_ms": round(_safe_mean(retrieval_latency_values), 2),
            "p95_retrieval_ms": round(_percentile(retrieval_latency_values, 0.95), 2),
            "avg_words_per_section": round(
                total_words / total_sections if total_sections else 0.0,
                2,
            ),
            "avg_chunk_tokens": round(_safe_mean([float(value) for value in chunk_token_values]), 2),
            "max_chunk_tokens": max(chunk_token_values, default=0),
            "chunk_expansion_ratio": round(
                sum(chunk_token_values) / total_words if total_words else 0.0,
                3,
            ),
            "words_per_second": round((total_words / parse_ms_total) * 1000 if parse_ms_total else 0.0, 2),
        },
        "documents": document_summaries,
        "queries": query_runs,
    }


def build_benchmark_report(
    raw_dir: Path,
    *,
    parser_backends: list[ParserBackend],
    questions: list[str],
    product_type: str = "home_contents",
    embedder_backends: list[EmbedderBackend] | None = None,
    vector_store_backends: list[VectorStoreBackend] | None = None,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    benchmark_dir: Path | None = None,
) -> dict:
    generated_at = datetime.now(UTC).isoformat()
    selected_embedder_backends = embedder_backends or [EmbedderBackend.HASHING]
    selected_vector_store_backends = vector_store_backends or [VectorStoreBackend.JSONL]
    runs = []
    for parser_backend in parser_backends:
        for embedder_backend in selected_embedder_backends:
            for vector_store_backend in selected_vector_store_backends:
                runs.append(
                    benchmark_backend(
                        raw_dir,
                        parser_backend=parser_backend,
                        questions=questions,
                        product_type=product_type,
                        embedder_backend=embedder_backend,
                        vector_store_backend=vector_store_backend,
                        max_tokens=max_tokens,
                        overlap_tokens=overlap_tokens,
                        benchmark_dir=benchmark_dir,
                    )
                )
    return {
        "generated_at": generated_at,
        "raw_dir": str(raw_dir),
        "product_type": product_type,
        "questions": questions,
        "parser_backends": [backend.value for backend in parser_backends],
        "embedder_backends": [backend.value for backend in selected_embedder_backends],
        "vector_store_backends": [backend.value for backend in selected_vector_store_backends],
        "runs": runs,
    }

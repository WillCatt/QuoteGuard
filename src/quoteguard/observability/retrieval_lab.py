"""Experiment runner for corpus audit, parser comparison, chunking, and retrieval."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
from importlib import metadata as importlib_metadata
import json
import math
from pathlib import Path
import shutil
import statistics
import time
import uuid

from quoteguard.config.settings import ROOT_DIR, settings
from quoteguard.ingestion.chunker import HierarchicalChunker, token_count
from quoteguard.ingestion.embedder import EmbedderBackend
from quoteguard.ingestion.models import Chunk, ParsedDocument
from quoteguard.ingestion.parser import ParserBackend, get_parser, persist_parsed_document
from quoteguard.retrieval.service import RetrievalService
from quoteguard.retrieval.vector_store import VectorStoreBackend


def load_gold_questions(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(package_name: str) -> str | None:
    try:
        return importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def _pdf_metadata(path: Path) -> dict:
    try:
        import fitz

        doc = fitz.open(path)
        page_count = doc.page_count
        metadata = doc.metadata or {}
        sample_pages = min(page_count, 5)
        page_texts = [doc.load_page(index).get_text("text") for index in range(sample_pages)]
        total_chars = sum(len(text.strip()) for text in page_texts)
        native_pdf = total_chars > 400

        block_columns = []
        footer_candidates: list[str] = []
        header_candidates: list[str] = []
        for index in range(sample_pages):
            page = doc.load_page(index)
            blocks = page.get_text("blocks")
            text_blocks = [block for block in blocks if len(block) >= 5 and str(block[4]).strip()]
            if text_blocks:
                x_positions = sorted({round(block[0], 1) for block in text_blocks})
                block_columns.append(len(x_positions) >= 2 and max(x_positions) - min(x_positions) > 120)
                ordered = sorted(text_blocks, key=lambda block: (block[1], block[0]))
                header_candidates.append(str(ordered[0][4]).strip())
                footer_candidates.append(str(ordered[-1][4]).strip())

        repeated_header = len(set(value for value in header_candidates if value)) < len(
            [value for value in header_candidates if value]
        ) if header_candidates else False
        repeated_footer = len(set(value for value in footer_candidates if value)) < len(
            [value for value in footer_candidates if value]
        ) if footer_candidates else False
        has_page_numbers = any(str(index + 1) in value for index, value in enumerate(footer_candidates[:sample_pages]))

        return {
            "page_count": page_count,
            "source_version_date": metadata.get("subject")
            or metadata.get("title")
            or metadata.get("creationDate")
            or metadata.get("modDate"),
            "native_pdf": native_pdf,
            "layout_profile": {
                "text_heavy": total_chars > 3000,
                "table_heavy": False,
                "form_heavy": False,
                "image_heavy": total_chars < 200,
            },
            "has_multi_column_layout": any(block_columns),
            "has_repeated_headers_footers": repeated_header or repeated_footer,
            "has_page_numbers": has_page_numbers,
            "has_tables_across_page_breaks": None,
        }
    except Exception:  # noqa: BLE001
        return {
            "page_count": None,
            "source_version_date": None,
            "native_pdf": None,
            "layout_profile": {
                "text_heavy": None,
                "table_heavy": None,
                "form_heavy": None,
                "image_heavy": None,
            },
            "has_multi_column_layout": None,
            "has_repeated_headers_footers": None,
            "has_page_numbers": None,
            "has_tables_across_page_breaks": None,
        }


def audit_corpus(raw_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(raw_dir.iterdir()):
        if path.is_dir() or path.name.startswith("."):
            continue
        metadata = _pdf_metadata(path)
        rows.append(
            {
                "file_name": path.name,
                "file_size_bytes": path.stat().st_size,
                "page_count": metadata["page_count"],
                "source_version_date": metadata["source_version_date"],
                "native_pdf": metadata["native_pdf"],
                "layout_profile": metadata["layout_profile"],
                "has_multi_column_layout": metadata["has_multi_column_layout"],
                "has_repeated_headers_footers": metadata["has_repeated_headers_footers"],
                "has_page_numbers": metadata["has_page_numbers"],
                "has_tables_across_page_breaks": metadata["has_tables_across_page_breaks"],
                "expected_retrieval_difficulty": "manual_review",
                "checksum_sha256": _sha256(path),
            }
        )
    return rows


def _prefixed_text(section_path: list[str], text: str) -> str:
    heading_path = " > ".join(section_path)
    return f"{heading_path}\n\n{text}".strip()


def _chunk_fixed_size(
    document: ParsedDocument,
    *,
    max_tokens: int,
    overlap_ratio: float,
    prefix_headings: bool,
) -> list[Chunk]:
    sections = document.sections
    joined_rows: list[tuple[str, int, list[str]]] = []
    for section in sections:
        base_text = _prefixed_text(section.section_path, section.text) if prefix_headings else section.text
        for word in base_text.split():
            joined_rows.append((word, section.page_number, section.section_path))

    overlap_tokens = int(max_tokens * overlap_ratio)
    step = max(1, max_tokens - overlap_tokens)
    chunks: list[Chunk] = []
    for index, start in enumerate(range(0, len(joined_rows), step)):
        window = joined_rows[start : start + max_tokens]
        if not window:
            break
        text = " ".join(word for word, _, _ in window)
        page_number = window[0][1]
        section_path = list(window[0][2])
        chunks.append(
            Chunk(
                chunk_id=f"{document.source_pdf}:fixed:{index}",
                text=text,
                source_pdf=document.source_pdf,
                product_type=document.product_type,
                section_path=section_path,
                page_number=page_number,
                token_count=len(window),
            )
        )
        if start + max_tokens >= len(joined_rows):
            break
    return chunks


def _chunk_section_aware(
    document: ParsedDocument,
    *,
    prefix_headings: bool,
    capped: bool,
    max_tokens: int,
    overlap_ratio: float,
) -> list[Chunk]:
    overlap_tokens = int(max_tokens * overlap_ratio)
    chunker = HierarchicalChunker(max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    if capped:
        prepared_sections = [
            section.model_copy(
                update={
                    "text": _prefixed_text(section.section_path, section.text)
                    if prefix_headings
                    else section.text
                }
            )
            for section in document.sections
        ]
        prepared_document = document.model_copy(update={"sections": prepared_sections})
        return chunker.chunk_document(prepared_document)

    chunks: list[Chunk] = []
    for index, section in enumerate(document.sections):
        text = _prefixed_text(section.section_path, section.text) if prefix_headings else section.text
        chunks.append(
            Chunk(
                chunk_id=f"{document.source_pdf}:section:{index}",
                text=text,
                source_pdf=document.source_pdf,
                product_type=document.product_type,
                section_path=section.section_path,
                page_number=section.page_number,
                token_count=token_count(text),
            )
        )
    return chunks


def _chunk_page_based(
    document: ParsedDocument,
    *,
    max_tokens: int,
    overlap_ratio: float,
    prefix_headings: bool,
) -> list[Chunk]:
    by_page: dict[int, list[tuple[list[str], str]]] = {}
    for section in document.sections:
        by_page.setdefault(section.page_number, []).append((section.section_path, section.text))

    overlap_tokens = int(max_tokens * overlap_ratio)
    step = max(1, max_tokens - overlap_tokens)
    chunks: list[Chunk] = []
    for page_number, sections in sorted(by_page.items()):
        words: list[tuple[str, list[str]]] = []
        for section_path, text in sections:
            prepared_text = _prefixed_text(section_path, text) if prefix_headings else text
            words.extend((word, section_path) for word in prepared_text.split())
        for index, start in enumerate(range(0, len(words), step)):
            window = words[start : start + max_tokens]
            if not window:
                break
            text = " ".join(word for word, _ in window)
            chunks.append(
                Chunk(
                    chunk_id=f"{document.source_pdf}:page:{page_number}:{index}",
                    text=text,
                    source_pdf=document.source_pdf,
                    product_type=document.product_type,
                    section_path=list(window[0][1]),
                    page_number=page_number,
                    token_count=len(window),
                )
            )
            if start + max_tokens >= len(words):
                break
    return chunks


def build_chunks_for_strategy(
    documents: list[ParsedDocument],
    *,
    chunking_method: str,
    chunk_size: int,
    overlap_ratio: float,
    prefix_headings: bool = True,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        if chunking_method == "fixed":
            chunks.extend(
                _chunk_fixed_size(
                    document,
                    max_tokens=chunk_size,
                    overlap_ratio=overlap_ratio,
                    prefix_headings=prefix_headings,
                )
            )
        elif chunking_method == "section_aware":
            chunks.extend(
                _chunk_section_aware(
                    document,
                    prefix_headings=prefix_headings,
                    capped=False,
                    max_tokens=chunk_size,
                    overlap_ratio=overlap_ratio,
                )
            )
        elif chunking_method == "page_based":
            chunks.extend(
                _chunk_page_based(
                    document,
                    max_tokens=chunk_size,
                    overlap_ratio=overlap_ratio,
                    prefix_headings=prefix_headings,
                )
            )
        else:
            chunks.extend(
                _chunk_section_aware(
                    document,
                    prefix_headings=prefix_headings,
                    capped=True,
                    max_tokens=chunk_size,
                    overlap_ratio=overlap_ratio,
                )
            )
    return chunks


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    return float(statistics.median(values))


def _duplicate_chunk_rate(chunks: list[Chunk]) -> float:
    if not chunks:
        return 0.0
    normalized = [" ".join(chunk.text.lower().split()) for chunk in chunks]
    unique = len(set(normalized))
    return round(1.0 - (unique / len(normalized)), 4)


def summarize_chunks(chunks: list[Chunk], *, chunk_size: int) -> dict:
    token_values = [chunk.token_count for chunk in chunks]
    tiny = sum(1 for value in token_values if value < 50)
    oversized = sum(1 for value in token_values if value > chunk_size)
    return {
        "number_of_chunks": len(chunks),
        "average_tokens_per_chunk": round(statistics.fmean(token_values), 2) if token_values else 0.0,
        "median_tokens_per_chunk": round(_median(token_values), 2),
        "min_tokens": min(token_values, default=0),
        "max_tokens": max(token_values, default=0),
        "tiny_chunks_under_50": tiny,
        "oversized_chunks": oversized,
        "duplicate_chunk_rate": _duplicate_chunk_rate(chunks),
        "headings_retained": True,
        "page_metadata_retained": True,
        "tables_split_badly": "manual_review",
        "sample_chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "source_pdf": chunk.source_pdf,
                "page_number": chunk.page_number,
                "token_count": chunk.token_count,
                "text_preview": " ".join(chunk.text.split())[:240],
            }
            for chunk in chunks[:10]
        ],
    }


def _expected_doc(question: dict) -> str | None:
    return question.get("source_pdf") or question.get("expected_doc")


def _expected_pages(question: dict) -> list[int]:
    pages = question.get("supporting_pages") or question.get("expected_pages") or []
    return [int(page) for page in pages]


def _relevant(result: dict, question: dict) -> bool:
    chunk = result["chunk"]
    expected_doc = _expected_doc(question)
    expected_pages = _expected_pages(question)
    if expected_doc and chunk["source_pdf"] != expected_doc:
        return False
    if expected_pages:
        return int(chunk["page_number"]) in expected_pages
    return bool(expected_doc and chunk["source_pdf"] == expected_doc)


def _ndcg_at_k(relevance_flags: list[bool], k: int) -> float:
    dcg = 0.0
    for index, relevant in enumerate(relevance_flags[:k], start=1):
        if relevant:
            dcg += 1.0 / math.log2(index + 1)
    ideal_hits = sum(1 for relevant in relevance_flags if relevant)
    if ideal_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, min(ideal_hits, k) + 1))
    return round(dcg / idcg if idcg else 0.0, 4)


def score_question(question: dict, results: list[dict], latency_ms: float) -> dict:
    answerable = bool(question.get("answerable", True))
    retrieved_pages = [int(result["chunk"]["page_number"]) for result in results]
    relevance_flags = [_relevant(result, question) for result in results]
    expected_pages = _expected_pages(question)
    relevant_count = sum(1 for relevant in relevance_flags if relevant)
    first_relevant_rank = next((index + 1 for index, relevant in enumerate(relevance_flags[:5]) if relevant), None)

    if answerable:
        hit_at_1 = 1.0 if relevance_flags[:1] and relevance_flags[0] else 0.0
        hit_at_3 = 1.0 if any(relevance_flags[:3]) else 0.0
        if expected_pages:
            found_pages = sorted({retrieved_pages[index] for index, relevant in enumerate(relevance_flags[:5]) if relevant})
            recall_at_5 = round(len(found_pages) / len(set(expected_pages)), 4)
        else:
            recall_at_5 = 1.0 if any(relevance_flags[:5]) else 0.0
        mrr_at_5 = round(1.0 / first_relevant_rank, 4) if first_relevant_rank else 0.0
        ndcg_at_5 = _ndcg_at_k(relevance_flags, 5)
        context_precision = round(relevant_count / len(results), 4) if results else 0.0
        context_recall = recall_at_5
    else:
        hit_at_1 = None
        hit_at_3 = None
        recall_at_5 = None
        mrr_at_5 = None
        ndcg_at_5 = None
        context_precision = None
        context_recall = None

    return {
        "question_id": question.get("question_id", ""),
        "question": question.get("question", ""),
        "expected_answer": question.get("expected_answer", ""),
        "expected_doc": _expected_doc(question) or "",
        "expected_pages": expected_pages,
        "retrieved_chunk_ids": [result["chunk"]["chunk_id"] for result in results],
        "retrieved_pages": retrieved_pages,
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "recall_at_5": recall_at_5,
        "mrr_at_5": mrr_at_5,
        "ndcg_at_5": ndcg_at_5,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "latency_ms": round(latency_ms, 2),
        "notes": "Unanswerable question skipped from rank metrics." if not answerable else "",
        "results": results,
    }


def summarize_retrieval(results: list[dict], storage_path: Path, failures: list[str]) -> dict:
    scored_rows = [row for row in results if row["hit_at_1"] is not None]
    latencies = [row["latency_ms"] for row in results]
    if storage_path.is_file():
        storage_size_bytes = storage_path.stat().st_size
    elif storage_path.exists():
        storage_size_bytes = sum(
            file_path.stat().st_size for file_path in storage_path.rglob("*") if file_path.is_file()
        )
    else:
        storage_size_bytes = 0
    return {
        "hit_at_1": round(statistics.fmean([row["hit_at_1"] for row in scored_rows]), 4) if scored_rows else 0.0,
        "hit_at_3": round(statistics.fmean([row["hit_at_3"] for row in scored_rows]), 4) if scored_rows else 0.0,
        "recall_at_5": round(statistics.fmean([row["recall_at_5"] for row in scored_rows]), 4)
        if scored_rows
        else 0.0,
        "mrr_at_5": round(statistics.fmean([row["mrr_at_5"] for row in scored_rows]), 4) if scored_rows else 0.0,
        "ndcg_at_5": round(statistics.fmean([row["ndcg_at_5"] for row in scored_rows]), 4)
        if scored_rows
        else 0.0,
        "context_precision": round(statistics.fmean([row["context_precision"] for row in scored_rows]), 4)
        if scored_rows
        else 0.0,
        "context_recall": round(statistics.fmean([row["context_recall"] for row in scored_rows]), 4)
        if scored_rows
        else 0.0,
        "latency_ms_p50": round(statistics.median(latencies), 2) if latencies else 0.0,
        "latency_ms_p95": round(sorted(latencies)[int((len(latencies) - 1) * 0.95)], 2) if latencies else 0.0,
        "storage_size_bytes": storage_size_bytes,
        "failure_notes": failures,
        "example_retrieved_chunks": [
            {
                "question_id": row["question_id"],
                "question": row["question"],
                "top_chunk_id": row["retrieved_chunk_ids"][0] if row["retrieved_chunk_ids"] else None,
                "top_page": row["retrieved_pages"][0] if row["retrieved_pages"] else None,
            }
            for row in results[:5]
        ],
    }


def _write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_results_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "question_id",
        "question",
        "expected_answer",
        "expected_doc",
        "expected_pages",
        "retrieved_chunk_ids",
        "retrieved_pages",
        "hit_at_1",
        "hit_at_3",
        "recall_at_5",
        "mrr_at_5",
        "ndcg_at_5",
        "latency_ms",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **{field: row.get(field) for field in fieldnames},
                    "expected_pages": json.dumps(row.get("expected_pages", [])),
                    "retrieved_chunk_ids": json.dumps(row.get("retrieved_chunk_ids", [])),
                    "retrieved_pages": json.dumps(row.get("retrieved_pages", [])),
                }
            )


def _write_failures_md(path: Path, failures: list[str]) -> None:
    lines = ["# Failures", ""]
    if not failures:
        lines.extend(["No failures recorded.", ""])
    else:
        lines.extend([f"- {failure}" for failure in failures])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_sample_retrievals_md(path: Path, rows: list[dict]) -> None:
    lines = ["# Sample Retrievals", ""]
    for row in rows[:5]:
        lines.append(f"## {row['question_id']} {row['question']}")
        lines.append("")
        for index, result in enumerate(row.get("results", [])[:5], start=1):
            chunk = result["chunk"]
            lines.append(
                f"- #{index} `{chunk['source_pdf']}` p.{chunk['page_number']} "
                f"`{' > '.join(chunk['section_path'])}` score={result['score']:.4f}"
            )
            lines.append(f"  - {' '.join(chunk['text'].split())[:260]}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _parser_version_for_backend(backend: ParserBackend) -> str | None:
    package_name = {
        ParserBackend.PYMUPDF4LLM: "pymupdf4llm",
        ParserBackend.DOCLING: "docling",
        ParserBackend.TEXT_FALLBACK: None,
    }[backend]
    return _package_version(package_name) if package_name else None


def _vector_store_root(run_dir: Path, backend: VectorStoreBackend) -> Path:
    if backend == VectorStoreBackend.CHROMA:
        return run_dir / "vector_store"
    return run_dir / "vector_store.jsonl"


def run_retrieval_experiment(
    *,
    raw_dir: Path,
    questions_path: Path,
    parser_backend: ParserBackend,
    chunking_method: str,
    chunk_size: int,
    overlap_ratio: float,
    embedder_backend: EmbedderBackend,
    vector_store_backend: VectorStoreBackend,
    top_k: int = 5,
    reranking_used: bool = True,
    product_type: str = "home_contents",
    run_id: str | None = None,
    runs_root: Path | None = None,
) -> Path:
    run_id_value = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    root = runs_root or ROOT_DIR / "experiments" / "retrieval_lab" / "runs"
    run_dir = root / run_id_value
    if run_dir.exists():
        raise FileExistsError(run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    parsed_dir = run_dir / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)

    corpus_summary = audit_corpus(raw_dir)
    parser = get_parser(parser_backend)
    documents: list[ParsedDocument] = []
    parser_rows: list[dict] = []
    failures: list[str] = []
    total_parse_started = time.perf_counter()

    for path in sorted(raw_dir.iterdir()):
        if path.is_dir() or path.name.startswith("."):
            continue
        started = time.perf_counter()
        try:
            document = parser.parse(path, product_type=product_type)
            duration_ms = (time.perf_counter() - started) * 1000
            documents.append(document)
            persist_parsed_document(document, parsed_dir / f"{document.source_pdf}.json")
            parser_rows.append(
                {
                    "file_name": path.name,
                    "parse_time_ms": round(duration_ms, 2),
                    "parse_time_per_page_ms": round(
                        duration_ms / max(1, next((row["page_count"] for row in corpus_summary if row["file_name"] == path.name), 1) or 1),
                        2,
                    ),
                    "total_extracted_characters": sum(len(section.text) for section in document.sections),
                    "number_of_sections_detected": len(document.sections),
                    "number_of_tables_detected": 0,
                    "failed_pages": 0,
                    "empty_pages": 0,
                    "warnings_or_errors": [],
                    "output_size_bytes": (parsed_dir / f"{document.source_pdf}.json").stat().st_size,
                }
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.perf_counter() - started) * 1000
            failures.append(f"Parser failure for {path.name}: {type(exc).__name__}: {exc}")
            parser_rows.append(
                {
                    "file_name": path.name,
                    "parse_time_ms": round(duration_ms, 2),
                    "parse_time_per_page_ms": None,
                    "total_extracted_characters": 0,
                    "number_of_sections_detected": 0,
                    "number_of_tables_detected": 0,
                    "failed_pages": "unknown",
                    "empty_pages": "unknown",
                    "warnings_or_errors": [f"{type(exc).__name__}: {exc}"],
                    "output_size_bytes": 0,
                }
            )
    total_parse_time_ms = round((time.perf_counter() - total_parse_started) * 1000, 2)

    chunks = build_chunks_for_strategy(
        documents,
        chunking_method=chunking_method,
        chunk_size=chunk_size,
        overlap_ratio=overlap_ratio,
        prefix_headings=True,
    )
    chunks_path = run_dir / "chunks.jsonl"
    chunks_path.write_text(
        "\n".join(json.dumps(chunk.model_dump()) for chunk in chunks) + ("\n" if chunks else ""),
        encoding="utf-8",
    )

    index_started = time.perf_counter()
    retrieval = RetrievalService(
        chunks,
        store_path=_vector_store_root(run_dir, vector_store_backend),
        embedder_backend=embedder_backend,
        vector_store_backend=vector_store_backend,
        use_reranker=reranking_used,
    )
    total_indexing_time_ms = round((time.perf_counter() - index_started) * 1000, 2)

    questions = load_gold_questions(questions_path)
    results_rows: list[dict] = []
    for question in questions:
        query_started = time.perf_counter()
        results = retrieval.query(
            question["question"],
            k=top_k,
            filters={"product_type": product_type},
        )
        latency_ms = (time.perf_counter() - query_started) * 1000
        results_rows.append(score_question(question, results, latency_ms))

    retrieval_summary = summarize_retrieval(results_rows, _vector_store_root(run_dir, vector_store_backend), failures)

    config = {
        "run_id": run_id_value,
        "date": datetime.now(UTC).isoformat(),
        "parser_name": parser_backend.value,
        "parser_version": _parser_version_for_backend(parser_backend),
        "chunking_method": chunking_method,
        "chunk_size": chunk_size,
        "overlap": overlap_ratio,
        "embedding_model": settings.embed_model if embedder_backend == EmbedderBackend.SENTENCE_TRANSFORMERS else "hashing",
        "vector_store": vector_store_backend.value,
        "retrieval_method": "dense_sparse_fusion",
        "top_k": top_k,
        "reranking_used": reranking_used,
        "product_type": product_type,
        "corpus_files": [row["file_name"] for row in corpus_summary],
    }

    metrics = {
        "corpus_audit": corpus_summary,
        "parser_comparison": {
            "parser_name": parser_backend.value,
            "parser_version": _parser_version_for_backend(parser_backend),
            "total_parse_time_ms": total_parse_time_ms,
            "per_pdf": parser_rows,
        },
        "chunking_summary": summarize_chunks(chunks, chunk_size=chunk_size),
        "retrieval_benchmark": retrieval_summary,
        "indexing": {
            "total_indexing_time_ms": total_indexing_time_ms,
            "storage_size_bytes": retrieval_summary["storage_size_bytes"],
        },
    }

    _write_json(run_dir / "config.json", config)
    _write_json(run_dir / "metrics.json", metrics)
    _write_results_csv(run_dir / "results.csv", results_rows)
    _write_failures_md(run_dir / "failures.md", failures)
    _write_sample_retrievals_md(run_dir / "sample_retrievals.md", results_rows)
    return run_dir

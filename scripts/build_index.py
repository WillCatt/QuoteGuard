"""Build parsed chunks and a fallback vector index from local documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from quoteguard.config.settings import settings
from quoteguard.ingestion.chunker import HierarchicalChunker
from quoteguard.ingestion.embedder import EmbedderBackend
from quoteguard.ingestion.parser import ParserBackend, parse_directory, persist_parsed_document
from quoteguard.retrieval.service import RetrievalService
from quoteguard.retrieval.vector_store import VectorStoreBackend


def build_index(
    raw_dir: Path | None = None,
    *,
    parser_backend: ParserBackend | None = None,
    embedder_backend: EmbedderBackend | None = None,
    vector_store_backend: VectorStoreBackend | None = None,
    product_type: str | None = None,
) -> None:
    settings.ensure_directories()
    source_dir = raw_dir or settings.data_dir / "raw_pdfs"
    chunker = HierarchicalChunker()
    selected_product_type = product_type or settings.product_type
    documents = parse_directory(
        source_dir,
        backend=parser_backend,
        product_type=selected_product_type,
    )
    for document in documents:
        persist_parsed_document(document, settings.parsed_dir / f"{document.source_pdf}.json")
    chunks = chunker.chunk_documents(documents)
    settings.chunks_path.write_text(
        "\n".join(json.dumps(chunk.model_dump()) for chunk in chunks) + ("\n" if chunks else ""),
        encoding="utf-8",
    )
    retrieval = RetrievalService(
        chunks,
        store_path=settings.vector_store_dir / "vector_store.jsonl",
        embedder_backend=embedder_backend,
        vector_store_backend=vector_store_backend,
    )
    parser_name = documents[0].parser_backend if documents else "none"
    vector_store_name = retrieval.vector_store.__class__.__name__
    embedder_name = retrieval.embedder.__class__.__name__
    print(
        f"Indexed {len(chunks)} chunks from {len(documents)} documents "
        f"(parser={parser_name}, embedder={embedder_name}, vector_store={vector_store_name})"
    )


def _parse_parser_backend(value: str) -> ParserBackend | None:
    return None if value == "auto" else ParserBackend(value)


def _parse_embedder_backend(value: str) -> EmbedderBackend | None:
    return None if value == "auto" else EmbedderBackend(value)


def _parse_vector_store_backend(value: str) -> VectorStoreBackend | None:
    return None if value == "auto" else VectorStoreBackend(value)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--raw-dir", type=Path, default=None)
    arg_parser.add_argument(
        "--parser-backend",
        choices=["auto", "pymupdf4llm", "docling", "text_fallback"],
        default="auto",
    )
    arg_parser.add_argument(
        "--embedder-backend",
        choices=["auto", "sentence_transformers", "hashing"],
        default="auto",
    )
    arg_parser.add_argument(
        "--vector-store-backend",
        choices=["auto", "chroma", "jsonl"],
        default="auto",
    )
    arg_parser.add_argument("--product-type", default=None)
    args = arg_parser.parse_args()
    build_index(
        raw_dir=args.raw_dir,
        parser_backend=_parse_parser_backend(args.parser_backend),
        embedder_backend=_parse_embedder_backend(args.embedder_backend),
        vector_store_backend=_parse_vector_store_backend(args.vector_store_backend),
        product_type=args.product_type,
    )

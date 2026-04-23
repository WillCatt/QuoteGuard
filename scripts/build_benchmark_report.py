"""Build parser/chunking/retrieval benchmark data for the Streamlit retrieval lab."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from quoteguard.config.settings import settings
from quoteguard.ingestion.embedder import EmbedderBackend
from quoteguard.ingestion.parser import ParserBackend
from quoteguard.observability.benchmarking import (
    build_benchmark_report,
    load_questions,
    save_benchmark_report,
)
from quoteguard.retrieval.vector_store import VectorStoreBackend


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=settings.data_dir / "raw_pdfs")
    parser.add_argument(
        "--parser-backends",
        nargs="+",
        choices=[backend.value for backend in ParserBackend],
        default=[ParserBackend.PYMUPDF4LLM.value, ParserBackend.DOCLING.value],
    )
    parser.add_argument(
        "--embedder-backends",
        nargs="+",
        choices=[backend.value for backend in EmbedderBackend],
        default=[EmbedderBackend.HASHING.value],
    )
    parser.add_argument(
        "--vector-store-backends",
        nargs="+",
        choices=[backend.value for backend in VectorStoreBackend],
        default=[VectorStoreBackend.JSONL.value],
    )
    parser.add_argument("--questions-path", type=Path, default=Path("data/eval/golden.jsonl"))
    parser.add_argument("--product-type", default=settings.product_type)
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument("--overlap-tokens", type=int, default=50)
    parser.add_argument("--output-path", type=Path, default=settings.benchmark_report_path)
    args = parser.parse_args()

    questions = load_questions(args.questions_path)
    report = build_benchmark_report(
        args.raw_dir,
        parser_backends=[ParserBackend(value) for value in args.parser_backends],
        questions=questions,
        product_type=args.product_type,
        embedder_backends=[EmbedderBackend(value) for value in args.embedder_backends],
        vector_store_backends=[VectorStoreBackend(value) for value in args.vector_store_backends],
        max_tokens=args.max_tokens,
        overlap_tokens=args.overlap_tokens,
        benchmark_dir=args.output_path.parent,
    )
    output_path = save_benchmark_report(report, args.output_path)
    print(f"Wrote benchmark report to {output_path}")


if __name__ == "__main__":
    main()

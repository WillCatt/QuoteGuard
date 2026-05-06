"""Run a retrieval-lab experiment and write per-run artefacts."""

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
from quoteguard.observability.retrieval_lab import run_retrieval_experiment
from quoteguard.retrieval.vector_store import VectorStoreBackend


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=settings.data_dir / "raw_pdfs")
    parser.add_argument("--questions-path", type=Path, default=Path("data/eval/golden_v2_template.jsonl"))
    parser.add_argument(
        "--parser-backend",
        choices=[backend.value for backend in ParserBackend],
        default=ParserBackend.PYMUPDF4LLM.value,
    )
    parser.add_argument(
        "--chunking-method",
        choices=["fixed", "section_aware", "page_based", "hybrid_section_aware"],
        default="hybrid_section_aware",
    )
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=float, default=0.1)
    parser.add_argument(
        "--embedder-backend",
        choices=[backend.value for backend in EmbedderBackend],
        default=EmbedderBackend.HASHING.value,
    )
    parser.add_argument(
        "--vector-store-backend",
        choices=[backend.value for backend in VectorStoreBackend],
        default=VectorStoreBackend.JSONL.value,
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--disable-reranking", action="store_true")
    parser.add_argument("--product-type", default=settings.product_type)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=ROOT_DIR / "experiments" / "retrieval_lab" / "runs",
    )
    args = parser.parse_args()

    run_dir = run_retrieval_experiment(
        raw_dir=args.raw_dir,
        questions_path=args.questions_path,
        parser_backend=ParserBackend(args.parser_backend),
        chunking_method=args.chunking_method,
        chunk_size=args.chunk_size,
        overlap_ratio=args.overlap,
        embedder_backend=EmbedderBackend(args.embedder_backend),
        vector_store_backend=VectorStoreBackend(args.vector_store_backend),
        top_k=args.top_k,
        reranking_used=not args.disable_reranking,
        product_type=args.product_type,
        run_id=args.run_id,
        runs_root=args.runs_root,
    )
    print(f"Wrote retrieval experiment to {run_dir}")


if __name__ == "__main__":
    main()

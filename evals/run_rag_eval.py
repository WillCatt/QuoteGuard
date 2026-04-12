"""Seed RAG evaluation harness with bootstrap confidence intervals."""

from __future__ import annotations

import json
import random
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from quoteguard.ingestion.models import Chunk
from quoteguard.retrieval.service import RetrievalService


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def bootstrap_ci(values: list[float], samples: int = 500) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    means = []
    for _ in range(samples):
        sample = [random.choice(values) for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    center = sum(values) / len(values)
    lower = means[int(0.025 * len(means))]
    upper = means[int(0.975 * len(means)) - 1]
    return center, lower, upper


def demo_chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id="golden-1",
            text="The policy covers theft after forcible entry.",
            source_pdf="demo.pdf",
            product_type="home_contents",
            section_path=["Coverage", "Theft"],
            page_number=3,
            token_count=8,
        ),
        Chunk(
            chunk_id="golden-2",
            text="Jewellery cover is subject to item limits shown in the schedule.",
            source_pdf="demo.pdf",
            product_type="home_contents",
            section_path=["Limits", "Jewellery"],
            page_number=8,
            token_count=11,
        ),
    ]


def main() -> None:
    dataset = load_jsonl(Path("data/eval/golden.jsonl"))
    retrieval = RetrievalService(demo_chunks(), store_path=Path("data/processed/chroma/rag_eval_store.jsonl"))
    recalls = []
    for row in dataset:
        results = retrieval.query(row["question"], k=5, filters={"product_type": row["product_type"]})
        retrieved_ids = {result["chunk"]["chunk_id"] for result in results}
        expected = set(row["expected_source_chunks"])
        recalls.append(1.0 if expected.intersection(retrieved_ids) else 0.0)
    mean, lower, upper = bootstrap_ci(recalls)
    print(f"recall@5: {mean:.3f} (95% CI {lower:.3f}, {upper:.3f})")


if __name__ == "__main__":
    main()

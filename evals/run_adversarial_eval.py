"""Seed adversarial evaluation harness."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from quoteguard.ingestion.models import Chunk
from quoteguard.orchestration.handlers import ConversationOrchestrator
from quoteguard.orchestration.state import ConversationState
from quoteguard.retrieval.service import RetrievalService


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def demo_orchestrator() -> ConversationOrchestrator:
    chunks = [
        Chunk(
            chunk_id="adv-1",
            text="The policy covers accidental damage when optional cover is selected.",
            source_pdf="demo.pdf",
            product_type="home_contents",
            section_path=["Optional Cover", "Accidental Damage"],
            page_number=5,
            token_count=10,
        )
    ]
    retrieval = RetrievalService(chunks, store_path=Path("data/processed/chroma/adversarial_store.jsonl"))
    return ConversationOrchestrator(retrieval)


def main() -> None:
    dataset = load_jsonl(Path("data/eval/adversarial.jsonl"))
    orchestrator = demo_orchestrator()
    outcomes = []
    for row in dataset:
        state = ConversationState(phase="coverage_questions", product_type="home_contents")
        _, result = orchestrator.handle_turn(state, row["prompt"])
        if result.handoff_required:
            actual = "handoff"
        elif (
            "I don't have that information." in result.reply
            or "can't help" in result.reply
            or "can't provide advice" in result.reply
        ):
            actual = "refuse"
        else:
            actual = "deflect"
        outcomes.append((row["category"], row["expected_behaviour"], actual))
    for category, expected, actual in outcomes:
        print(f"{category}: expected={expected} actual={actual}")


if __name__ == "__main__":
    main()

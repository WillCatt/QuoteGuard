"""Local smoke chat over a tiny synthetic corpus."""

from __future__ import annotations

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


def demo_chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id="demo-1",
            text="The policy covers theft after forcible entry into the home.",
            source_pdf="demo.pdf",
            product_type="home_contents",
            section_path=["Coverage", "Theft"],
            page_number=4,
            token_count=10,
        ),
        Chunk(
            chunk_id="demo-2",
            text="Portable electronics are covered only when they are listed in the policy schedule.",
            source_pdf="demo.pdf",
            product_type="home_contents",
            section_path=["Coverage", "Portable Items"],
            page_number=6,
            token_count=14,
        ),
    ]


def main() -> None:
    retrieval = RetrievalService(demo_chunks(), store_path=Path("data/processed/chroma/demo_store.jsonl"))
    orchestrator = ConversationOrchestrator(retrieval)
    state = ConversationState()
    turns = [
        "Hi there",
        "I want a home contents quote",
        "It is a house in 3000 with an alarm and I am the owner",
        "Does the policy cover theft?",
        "Give me a summary",
        "Proceed to handoff",
    ]
    for turn in turns:
        state, result = orchestrator.handle_turn(state, turn)
        print(f"USER: {turn}")
        print(f"BOT:  {result.reply}")
        print("---")


if __name__ == "__main__":
    main()

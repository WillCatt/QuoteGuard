"""Simple conversational simulation harness."""

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


def main() -> None:
    chunks = [
        Chunk(
            chunk_id="sim-1",
            text="The policy covers fire, storm, and theft events subject to the listed exclusions.",
            source_pdf="demo.pdf",
            product_type="home_contents",
            section_path=["Coverage", "Insured Events"],
            page_number=2,
            token_count=12,
        )
    ]
    retrieval = RetrievalService(chunks, store_path=Path("data/processed/chroma/sim_store.jsonl"))
    orchestrator = ConversationOrchestrator(retrieval)
    scripts = [
        [
            "Hello",
            "I need a home contents quote",
            "It is an apartment in 3000 with an alarm and I rent",
            "Does it cover theft?",
            "summary please",
            "handoff",
        ]
    ]
    for script in scripts:
        state = ConversationState()
        for turn in script:
            state, result = orchestrator.handle_turn(state, turn)
        print({"final_phase": state.phase, "turn_count": state.turn_count, "final_reply": result.reply})


if __name__ == "__main__":
    main()

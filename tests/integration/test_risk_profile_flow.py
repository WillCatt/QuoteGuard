from __future__ import annotations

import unittest
from pathlib import Path

from quoteguard.ingestion.models import Chunk
from quoteguard.orchestration.handlers import ConversationOrchestrator
from quoteguard.orchestration.state import ConversationState
from quoteguard.retrieval.service import RetrievalService


class RiskProfileFlowTest(unittest.TestCase):
    def test_multi_turn_risk_profile_completion(self) -> None:
        chunks = [
            Chunk(
                chunk_id="risk-1",
                text="The policy covers theft after forcible entry.",
                source_pdf="demo.pdf",
                product_type="home_contents",
                section_path=["Coverage", "Theft"],
                page_number=1,
                token_count=8,
            )
        ]
        orchestrator = ConversationOrchestrator(
            RetrievalService(chunks, store_path=Path("data/processed/chroma/test_risk_store.jsonl"))
        )
        state = ConversationState()
        turns = [
            "Hello",
            "I want a home contents quote",
            "It is a house",
            "The postcode is 3000",
            "There is an alarm and I am the owner",
        ]
        for turn in turns:
            state, result = orchestrator.handle_turn(state, turn)
        self.assertEqual(state.phase, "coverage_questions")
        self.assertIn("risk profile is complete", result.reply.lower())


if __name__ == "__main__":
    unittest.main()

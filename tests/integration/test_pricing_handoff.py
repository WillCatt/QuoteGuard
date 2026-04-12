from __future__ import annotations

import unittest
from pathlib import Path

from quoteguard.ingestion.models import Chunk
from quoteguard.orchestration.handlers import ConversationOrchestrator
from quoteguard.orchestration.state import ConversationState
from quoteguard.retrieval.service import RetrievalService


class PricingHandoffTest(unittest.TestCase):
    def test_handoff_calls_pricing_boundary(self) -> None:
        chunks = [
            Chunk(
                chunk_id="handoff-1",
                text="The policy covers fire.",
                source_pdf="demo.pdf",
                product_type="home_contents",
                section_path=["Coverage"],
                page_number=1,
                token_count=4,
            )
        ]
        orchestrator = ConversationOrchestrator(
            RetrievalService(chunks, store_path=Path("data/processed/chroma/test_handoff_store.jsonl"))
        )
        state = ConversationState(
            phase="handoff",
            product_type="home_contents",
            slots={
                "property_type": "house",
                "postcode": "3000",
                "security_features": "alarm",
                "occupancy": "owner_occupied",
            },
        )
        _, result = orchestrator.handle_turn(state, "Proceed to handoff")
        self.assertTrue(result.handoff_required)
        self.assertIn("pricing engine", result.reply.lower())


if __name__ == "__main__":
    unittest.main()

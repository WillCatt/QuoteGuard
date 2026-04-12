from __future__ import annotations

import unittest

from quoteguard.ingestion.embedder import EmbedderBackend, HashingEmbedder, get_embedder


class EmbedderTest(unittest.TestCase):
    def test_hashing_embedder_returns_deterministic_dimension(self) -> None:
        embedder = HashingEmbedder(dimensions=32)
        vector = embedder.embed_text("the policy covers theft")
        self.assertEqual(len(vector), 32)

    def test_sentence_transformers_request_falls_back_when_unavailable(self) -> None:
        embedder = get_embedder(EmbedderBackend.SENTENCE_TRANSFORMERS)
        self.assertIsInstance(embedder, HashingEmbedder)


if __name__ == "__main__":
    unittest.main()

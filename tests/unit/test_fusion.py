from __future__ import annotations

import unittest

from quoteguard.retrieval.fusion import reciprocal_rank_fusion


class FusionTest(unittest.TestCase):
    def test_reciprocal_rank_fusion_merges_result_sets(self) -> None:
        result = reciprocal_rank_fusion(
            [
                [{"chunk": {"chunk_id": "a"}, "score": 0.9}, {"chunk": {"chunk_id": "b"}, "score": 0.8}],
                [{"chunk": {"chunk_id": "b"}, "score": 0.7}, {"chunk": {"chunk_id": "a"}, "score": 0.6}],
            ]
        )
        self.assertEqual({row["chunk"]["chunk_id"] for row in result}, {"a", "b"})


if __name__ == "__main__":
    unittest.main()

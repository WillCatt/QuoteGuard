"""Rank fusion helpers."""

from __future__ import annotations


def reciprocal_rank_fusion(result_sets: list[list[dict]], k: int = 60) -> list[dict]:
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}
    for result_set in result_sets:
        for rank, result in enumerate(result_set, start=1):
            chunk = result["chunk"]
            chunk_id = chunk["chunk_id"]
            payloads[chunk_id] = chunk
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    fused = [{"chunk": payloads[chunk_id], "score": score} for chunk_id, score in scores.items()]
    fused.sort(key=lambda item: item["score"], reverse=True)
    return fused

"""Lightweight reranking."""

from __future__ import annotations

import re


class LexicalReranker:
    def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        query_tokens = set(re.findall(r"[a-z0-9_]+", query.lower()))
        rescored = []
        for result in results:
            text_tokens = set(re.findall(r"[a-z0-9_]+", result["chunk"]["text"].lower()))
            overlap = len(query_tokens & text_tokens)
            rescored.append({"chunk": result["chunk"], "score": result["score"] + (0.05 * overlap)})
        rescored.sort(key=lambda item: item["score"], reverse=True)
        return rescored[:top_k]

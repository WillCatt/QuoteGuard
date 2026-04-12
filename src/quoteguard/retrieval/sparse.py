"""Sparse retrieval fallback."""

from __future__ import annotations

import math
import re
from collections import Counter

from quoteguard.ingestion.models import Chunk


class SparseRetriever:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self._doc_freq: Counter[str] = Counter()
        self._tokenized: dict[str, list[str]] = {}
        for chunk in chunks:
            tokens = self._tokenize(chunk.text)
            self._tokenized[chunk.chunk_id] = tokens
            for token in set(tokens):
                self._doc_freq[token] += 1

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9_]+", text.lower())

    def query(self, text: str, k: int = 5, filters: dict[str, str] | None = None) -> list[dict]:
        query_tokens = self._tokenize(text)
        results = []
        total_docs = len(self.chunks) or 1
        for chunk in self.chunks:
            if filters and any(getattr(chunk, key) != value for key, value in filters.items()):
                continue
            doc_tokens = self._tokenized[chunk.chunk_id]
            counts = Counter(doc_tokens)
            score = 0.0
            for token in query_tokens:
                tf = counts[token]
                if not tf:
                    continue
                idf = math.log((1 + total_docs) / (1 + self._doc_freq[token])) + 1
                score += tf * idf
            results.append({"chunk": chunk.model_dump(), "score": score})
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:k]

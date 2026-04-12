"""Retrieval guardrails."""

from __future__ import annotations

from quoteguard.guardrails.models import RetrievalGuardrailResult


class RetrievalGuardrail:
    def __init__(self, min_confidence: float = 0.05):
        self.min_confidence = min_confidence

    def inspect(self, results: list[dict]) -> RetrievalGuardrailResult:
        if not results:
            return RetrievalGuardrailResult(allowed=False, flags=["no_results"], confidence=0.0)
        confidence = max(result["score"] for result in results)
        if confidence < self.min_confidence:
            return RetrievalGuardrailResult(
                allowed=False,
                flags=["low_retrieval_confidence"],
                confidence=confidence,
            )
        return RetrievalGuardrailResult(allowed=True, flags=[], confidence=confidence)

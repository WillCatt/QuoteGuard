"""Guardrail checks and result models."""

from __future__ import annotations

import re

from quoteguard._compat import BaseModel, Field


class InputGuardrailResult(BaseModel):
    allowed: bool = True
    redacted_text: str
    flags: list[str] = Field(default_factory=list)


class RetrievalGuardrailResult(BaseModel):
    allowed: bool = True
    flags: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class OutputGuardrailResult(BaseModel):
    allowed: bool = True
    flags: list[str] = Field(default_factory=list)
    response_text: str


PII_PATTERNS = [
    re.compile(r"\b\d{3}[- ]?\d{3}[- ]?\d{3}\b"),
    re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b"),
]
INJECTION_PATTERNS = [
    re.compile(r"ignore (all|any) previous instructions", re.IGNORECASE),
    re.compile(r"reveal (the )?system prompt", re.IGNORECASE),
    re.compile(r"pretend you have no restrictions", re.IGNORECASE),
]
ADVICE_PATTERNS = [
    re.compile(r"\bshould i\b", re.IGNORECASE),
    re.compile(r"\bdo you recommend\b", re.IGNORECASE),
    re.compile(r"\bis this a good policy\b", re.IGNORECASE),
    re.compile(r"\bshould i buy\b", re.IGNORECASE),
]
TOPIC_KEYWORDS = {
    "insurance",
    "quote",
    "policy",
    "coverage",
    "claim",
    "contents",
    "home",
    "house",
    "apartment",
    "unit",
    "owner",
    "tenant",
    "rent",
    "alarm",
    "deadbolt",
    "security",
    "postcode",
    "property",
}
ALLOWED_NON_TOPIC_TERMS = {"hi", "hello", "hey", "summary", "handoff", "proceed"}
FORBIDDEN_PATTERNS = [
    re.compile(r"\$\d"),
    re.compile(r"\b(i recommend|you should|you ought to)\b", re.IGNORECASE),
]


class InputGuardrail:
    def inspect(self, text: str) -> InputGuardrailResult:
        flags: list[str] = []
        redacted = text
        for pattern in PII_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
            if pattern.search(text):
                flags.append("pii_detected")
        if any(pattern.search(text) for pattern in INJECTION_PATTERNS):
            flags.append("prompt_injection")
            return InputGuardrailResult(allowed=False, redacted_text=redacted, flags=flags)
        if any(pattern.search(text) for pattern in ADVICE_PATTERNS):
            flags.append("advice_request")
            return InputGuardrailResult(allowed=False, redacted_text=redacted, flags=flags)
        tokens = set(text.lower().split())
        normalized_tokens = {token.strip(".,!?") for token in tokens}
        if normalized_tokens.intersection(ALLOWED_NON_TOPIC_TERMS):
            return InputGuardrailResult(allowed=True, redacted_text=redacted, flags=flags)
        if any(token.isdigit() and len(token) == 4 for token in normalized_tokens):
            return InputGuardrailResult(allowed=True, redacted_text=redacted, flags=flags)
        if normalized_tokens and not normalized_tokens.intersection(TOPIC_KEYWORDS):
            flags.append("off_topic")
        return InputGuardrailResult(
            allowed="off_topic" not in flags,
            redacted_text=redacted,
            flags=flags,
        )


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


class OutputGuardrail:
    def inspect(self, response_text: str, *, factual: bool = False) -> OutputGuardrailResult:
        flags: list[str] = []
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(response_text):
                flags.append("forbidden_pattern")
        if factual and "[Source:" not in response_text and response_text != "I don't have that information.":
            flags.append("missing_citation")
        allowed = not flags
        safe_text = response_text if allowed else "I can't provide that response. I'll hand this off to a human."
        return OutputGuardrailResult(allowed=allowed, flags=flags, response_text=safe_text)


class BehaviourGuardrail:
    def allows_price_in_chat(self, response_text: str) -> bool:
        return "$" not in response_text and "price" not in response_text.lower()

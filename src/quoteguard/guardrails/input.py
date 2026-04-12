"""Input guardrails."""

from __future__ import annotations

import re

from quoteguard.guardrails.models import InputGuardrailResult


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
        return InputGuardrailResult(allowed="off_topic" not in flags, redacted_text=redacted, flags=flags)

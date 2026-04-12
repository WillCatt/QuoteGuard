"""Output guardrails."""

from __future__ import annotations

import re

from quoteguard.guardrails.models import OutputGuardrailResult


FORBIDDEN_PATTERNS = [
    re.compile(r"\$\d"),
    re.compile(r"\b(i recommend|you should|you ought to)\b", re.IGNORECASE),
]


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

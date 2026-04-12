"""Guardrail decision payloads."""

from __future__ import annotations

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

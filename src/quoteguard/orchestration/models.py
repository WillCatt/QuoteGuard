"""Orchestration support models."""

from __future__ import annotations

from quoteguard._compat import BaseModel, Field


class PhaseRules(BaseModel):
    required_slots: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    retrieval_filters: dict[str, str] = Field(default_factory=dict)


class TurnResult(BaseModel):
    reply: str
    citations: list[str] = Field(default_factory=list)
    handoff_required: bool = False
    guardrail_flags: list[str] = Field(default_factory=list)

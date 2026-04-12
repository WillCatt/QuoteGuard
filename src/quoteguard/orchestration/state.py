"""Conversation state models."""

from __future__ import annotations

from quoteguard._compat import BaseModel, Field


PHASE_GREETING = "greeting"
PHASE_PRODUCT_SELECT = "product_select"
PHASE_RISK_PROFILE = "risk_profile"
PHASE_COVERAGE_QUESTIONS = "coverage_questions"
PHASE_QUOTE_SUMMARY = "quote_summary"
PHASE_HANDOFF = "handoff"


class Message(BaseModel):
    role: str
    content: str


class ConversationState(BaseModel):
    phase: str = PHASE_GREETING
    product_type: str | None = None
    slots: dict[str, str] = Field(default_factory=dict)
    turn_count: int = 0
    history: list[Message] = Field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        self.history.append(Message(role=role, content=content))

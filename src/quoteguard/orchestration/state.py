"""Conversation state, slot extraction, and deterministic phase transitions."""

from __future__ import annotations

import re

from quoteguard._compat import BaseModel, Field


PHASE_GREETING = "greeting"
PHASE_PRODUCT_SELECT = "product_select"
PHASE_RISK_PROFILE = "risk_profile"
PHASE_COVERAGE_QUESTIONS = "coverage_questions"
PHASE_QUOTE_SUMMARY = "quote_summary"
PHASE_HANDOFF = "handoff"

POSTCODE_RE = re.compile(r"\b\d{4}\b")

RISK_PROFILE_SLOT_NAMES = [
    "property_type",
    "postcode",
    "security_features",
    "occupancy",
]


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


class PhaseRules(BaseModel):
    required_slots: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    retrieval_filters: dict[str, str] = Field(default_factory=dict)


class TurnResult(BaseModel):
    reply: str
    citations: list[str] = Field(default_factory=list)
    handoff_required: bool = False
    guardrail_flags: list[str] = Field(default_factory=list)


PHASE_RULES: dict[str, PhaseRules] = {
    PHASE_GREETING: PhaseRules(required_slots=[], allowed_actions=["acknowledge"]),
    PHASE_PRODUCT_SELECT: PhaseRules(required_slots=["product_type"], allowed_actions=["set_product"]),
    PHASE_RISK_PROFILE: PhaseRules(
        required_slots=RISK_PROFILE_SLOT_NAMES,
        allowed_actions=["collect_slot"],
        retrieval_filters={"product_type": "home_contents"},
    ),
    PHASE_COVERAGE_QUESTIONS: PhaseRules(
        required_slots=[],
        allowed_actions=["answer_question"],
        retrieval_filters={"product_type": "home_contents"},
    ),
    PHASE_QUOTE_SUMMARY: PhaseRules(required_slots=[], allowed_actions=["summarize"]),
    PHASE_HANDOFF: PhaseRules(required_slots=[], allowed_actions=["handoff"]),
}


def validate_slot(name: str, value: str) -> bool:
    if name == "postcode":
        return bool(POSTCODE_RE.fullmatch(value))
    return bool(value and value.strip())


def extract_slots(user_message: str, current_slots: dict[str, str] | None = None) -> dict[str, str]:
    slots = dict(current_slots or {})
    lower = user_message.lower()
    if "apartment" in lower or "unit" in lower:
        slots["property_type"] = "apartment"
    elif "house" in lower or "home" in lower:
        slots["property_type"] = "house"

    postcode_match = POSTCODE_RE.search(user_message)
    if postcode_match:
        slots["postcode"] = postcode_match.group(0)

    if "alarm" in lower or "deadbolt" in lower or "security" in lower:
        features = []
        if "alarm" in lower:
            features.append("alarm")
        if "deadbolt" in lower:
            features.append("deadbolt")
        if "security" in lower and "alarm" not in features:
            features.append("security")
        slots["security_features"] = ", ".join(features)

    if "owner" in lower:
        slots["occupancy"] = "owner_occupied"
    elif "rent" in lower or "tenant" in lower:
        slots["occupancy"] = "tenant"

    return {name: value for name, value in slots.items() if validate_slot(name, value)}


def missing_required_slots(state: ConversationState) -> list[str]:
    required = PHASE_RULES[state.phase].required_slots
    return [slot for slot in required if slot not in state.slots]


def next_phase(state: ConversationState) -> str:
    if state.phase == PHASE_GREETING:
        return PHASE_PRODUCT_SELECT
    if state.phase == PHASE_PRODUCT_SELECT:
        return PHASE_RISK_PROFILE if state.product_type else PHASE_PRODUCT_SELECT
    if state.phase == PHASE_RISK_PROFILE:
        return PHASE_COVERAGE_QUESTIONS if not missing_required_slots(state) else PHASE_RISK_PROFILE
    if state.phase == PHASE_COVERAGE_QUESTIONS:
        return PHASE_QUOTE_SUMMARY
    if state.phase == PHASE_QUOTE_SUMMARY:
        return PHASE_HANDOFF
    return PHASE_HANDOFF

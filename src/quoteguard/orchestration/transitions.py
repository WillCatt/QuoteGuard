"""Deterministic phase transitions."""

from __future__ import annotations

from quoteguard.orchestration.models import PhaseRules
from quoteguard.orchestration.slots import RISK_PROFILE_SLOT_NAMES
from quoteguard.orchestration.state import (
    ConversationState,
    PHASE_COVERAGE_QUESTIONS,
    PHASE_GREETING,
    PHASE_HANDOFF,
    PHASE_PRODUCT_SELECT,
    PHASE_QUOTE_SUMMARY,
    PHASE_RISK_PROFILE,
)


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

"""Conversation orchestration."""

from __future__ import annotations

from pathlib import Path

from quoteguard.api.pricing import price_quote
from quoteguard.api.schemas import QuoteRequest
from quoteguard.guardrails.behaviour import BehaviourGuardrail
from quoteguard.guardrails.input import InputGuardrail
from quoteguard.guardrails.output import OutputGuardrail
from quoteguard.guardrails.retrieval import RetrievalGuardrail
from quoteguard.observability.audit import AuditLogger
from quoteguard.orchestration.models import TurnResult
from quoteguard.orchestration.slots import RISK_PROFILE_SLOT_NAMES, extract_slots
from quoteguard.orchestration.state import (
    ConversationState,
    PHASE_COVERAGE_QUESTIONS,
    PHASE_GREETING,
    PHASE_HANDOFF,
    PHASE_PRODUCT_SELECT,
    PHASE_QUOTE_SUMMARY,
    PHASE_RISK_PROFILE,
)
from quoteguard.orchestration.transitions import missing_required_slots, next_phase
from quoteguard.retrieval.service import RetrievalService


class ConversationOrchestrator:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        *,
        audit_logger: AuditLogger | None = None,
        input_guardrail: InputGuardrail | None = None,
        retrieval_guardrail: RetrievalGuardrail | None = None,
        output_guardrail: OutputGuardrail | None = None,
        behaviour_guardrail: BehaviourGuardrail | None = None,
    ):
        self.retrieval_service = retrieval_service
        self.audit_logger = audit_logger or AuditLogger()
        self.input_guardrail = input_guardrail or InputGuardrail()
        self.retrieval_guardrail = retrieval_guardrail or RetrievalGuardrail()
        self.output_guardrail = output_guardrail or OutputGuardrail()
        self.behaviour_guardrail = behaviour_guardrail or BehaviourGuardrail()

    def handle_turn(self, state: ConversationState, user_message: str) -> tuple[ConversationState, TurnResult]:
        state.turn_count += 1
        input_result = self.input_guardrail.inspect(user_message)
        self.audit_logger.log("input_guardrail", input_result.model_dump())
        state.add_message("user", input_result.redacted_text)
        if not input_result.allowed:
            if "advice_request" in input_result.flags:
                return state, TurnResult(
                    reply="I can't provide advice or recommendations. I can explain policy wording or hand this off to a human.",
                    handoff_required=False,
                    guardrail_flags=input_result.flags,
                )
            state.phase = PHASE_HANDOFF
            return state, TurnResult(
                reply="I can't help with that request here. I'll hand this off to a human.",
                handoff_required=True,
                guardrail_flags=input_result.flags,
            )

        handler = {
            PHASE_GREETING: self._handle_greeting,
            PHASE_PRODUCT_SELECT: self._handle_product_select,
            PHASE_RISK_PROFILE: self._handle_risk_profile,
            PHASE_COVERAGE_QUESTIONS: self._handle_coverage_question,
            PHASE_QUOTE_SUMMARY: self._handle_quote_summary,
            PHASE_HANDOFF: self._handle_handoff,
        }[state.phase]
        state, result = handler(state, input_result.redacted_text)
        state.add_message("assistant", result.reply)
        return state, result

    def _handle_greeting(
        self, state: ConversationState, _: str
    ) -> tuple[ConversationState, TurnResult]:
        state.phase = next_phase(state)
        return state, TurnResult(
            reply="Hello. I can help collect information for a home contents quote and answer policy questions from the document set."
        )

    def _handle_product_select(
        self, state: ConversationState, user_message: str
    ) -> tuple[ConversationState, TurnResult]:
        if "contents" in user_message.lower() or "home" in user_message.lower():
            state.product_type = "home_contents"
            state.phase = next_phase(state)
            return state, TurnResult(reply="Home contents selected. Tell me about the property and postcode.")
        return state, TurnResult(reply="Please confirm that you want a home contents quote.")

    def _handle_risk_profile(
        self, state: ConversationState, user_message: str
    ) -> tuple[ConversationState, TurnResult]:
        state.slots.update(extract_slots(user_message, state.slots))
        missing = missing_required_slots(state)
        if missing:
            prompt = ", ".join(missing)
            return state, TurnResult(reply=f"I still need: {prompt}.")
        state.phase = next_phase(state)
        return state, TurnResult(
            reply="Thanks. Your risk profile is complete. You can now ask a coverage question or ask me to summarise the quote request."
        )

    def _handle_coverage_question(
        self, state: ConversationState, user_message: str
    ) -> tuple[ConversationState, TurnResult]:
        if "summary" in user_message.lower():
            state.phase = next_phase(state)
            return self._handle_quote_summary(state, user_message)

        results = self.retrieval_service.query(
            user_message,
            k=3,
            filters={"product_type": state.product_type or "home_contents"},
        )
        retrieval_result = self.retrieval_guardrail.inspect(results)
        self.audit_logger.log("retrieval_guardrail", retrieval_result.model_dump())
        if not retrieval_result.allowed:
            return state, TurnResult(reply="I don't have that information.", guardrail_flags=retrieval_result.flags)

        top = results[0]["chunk"]
        citation = f"{' > '.join(top['section_path'])} p.{top['page_number']}"
        answer = f"{top['text']} [Source: {citation}]"
        output_result = self.output_guardrail.inspect(answer, factual=True)
        self.audit_logger.log("output_guardrail", output_result.model_dump())
        if not self.behaviour_guardrail.allows_price_in_chat(output_result.response_text):
            state.phase = PHASE_HANDOFF
            return state, TurnResult(
                reply="Pricing must be handled through the pricing engine or a human handoff.",
                handoff_required=True,
                guardrail_flags=["pricing_boundary"],
            )
        return state, TurnResult(reply=output_result.response_text, citations=[citation], guardrail_flags=output_result.flags)

    def _handle_quote_summary(
        self, state: ConversationState, _: str
    ) -> tuple[ConversationState, TurnResult]:
        summary = ", ".join(f"{key}={value}" for key, value in sorted(state.slots.items()))
        state.phase = next_phase(state)
        return state, TurnResult(reply=f"Quote request summary: product_type={state.product_type}, {summary}. Next step is pricing handoff.")

    def _handle_handoff(
        self, state: ConversationState, _: str
    ) -> tuple[ConversationState, TurnResult]:
        quote_request = QuoteRequest(
            product_type=state.product_type or "home_contents",
            property_type=state.slots.get("property_type", "house"),
            postcode=state.slots.get("postcode", "3000"),
            security_features=state.slots.get("security_features", ""),
            occupancy=state.slots.get("occupancy", "owner_occupied"),
        )
        quote = price_quote(quote_request)
        return state, TurnResult(
            reply=(
                "Quote request handed off successfully. "
                f"Pricing engine reference={quote.reference_id}, premium={quote.estimated_premium} {quote.currency}."
            ),
            handoff_required=True,
        )


def bootstrap_orchestrator_from_chunks(chunks_path: Path) -> ConversationOrchestrator:
    from quoteguard.ingestion.models import Chunk

    chunks = []
    if chunks_path.exists():
        import json

        for line in chunks_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                chunks.append(Chunk.model_validate(json.loads(line)))
    retrieval = RetrievalService(chunks, store_path=chunks_path.parent / "vector_store.jsonl")
    return ConversationOrchestrator(retrieval)

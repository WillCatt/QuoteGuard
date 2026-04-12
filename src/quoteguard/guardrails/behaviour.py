"""Behavioural boundaries."""

from __future__ import annotations


class BehaviourGuardrail:
    def allows_price_in_chat(self, response_text: str) -> bool:
        return "$" not in response_text and "price" not in response_text.lower()

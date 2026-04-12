"""Slot extraction and validation."""

from __future__ import annotations

import re


POSTCODE_RE = re.compile(r"\b\d{4}\b")

RISK_PROFILE_SLOT_NAMES = [
    "property_type",
    "postcode",
    "security_features",
    "occupancy",
]


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

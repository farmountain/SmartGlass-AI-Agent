"""Permission heuristics for camera and microphone capture."""

from __future__ import annotations
"""Context-aware permissions helper for capture gating."""

from collections.abc import Mapping, Sequence
from typing import Any, Literal

PermissionDecision = Literal["allow", "pause", "deny"]

# Places or detections that should immediately block capture.
_DENY_TAGS = {
    "restroom",
    "bathroom",
    "toilet",
    "locker_room",
    "changing_room",
    "fitting_room",
    "credit_card",
    "debit_card",
    "card_number",
    "payment_card",
    "bank_pin",
    "atm_keypad",
}

# Places that should temporarily pause capture until the user confirms.
_PAUSE_TAGS = {
    "clinic",
    "hospital",
    "urgent_care",
    "pharmacy",
    "medical",
    "triage",
    "children",
    "child",
    "kids",
    "minor",
    "infant",
    "nursery",
    "school",
    "classroom",
    "playground",
    "courthouse",
    "security",
}

_DENY_FLAG_KEYS = {
    "deny_capture",
    "is_restricted_location",
    "payment_card_detected",
    "credit_card_ocr",
    "sensitive_payment",
    "bathroom",
    "restroom",
}

_PAUSE_FLAG_KEYS = {
    "children_present",
    "minors_visible",
    "clinic_mode",
    "medical_mode",
    "privacy_pause",
    "sensitive_place",
    "geo_requires_pause",
}

_NUMERIC_CHILD_KEYS = {
    "children_in_frame",
    "detected_children",
    "minors_detected",
}


def _normalise_token(token: str) -> str:
    """Return a lowercase token with whitespace collapsed to underscores."""

    cleaned = token.strip().lower()
    if not cleaned:
        return ""
    for char in "-/":
        cleaned = cleaned.replace(char, " ")
    parts = [part for part in cleaned.split() if part]
    return "_".join(parts)


def _extract_tokens(ctx: Mapping[str, Any]) -> tuple[set[str], dict[str, bool], dict[str, list[float]]]:
    """Return (tokens, bool_flags, numeric_flags) extracted from ``ctx``."""

    tokens: set[str] = set()
    bool_flags: dict[str, bool] = {}
    numeric_flags: dict[str, list[float]] = {}

    stack: list[Any] = [ctx]
    seen_ids: set[int] = set()
    while stack:
        current = stack.pop()
        identifier = id(current)
        if identifier in seen_ids:
            continue
        seen_ids.add(identifier)

        if isinstance(current, Mapping):
            for key, value in current.items():
                norm_key = _normalise_token(str(key))
                if isinstance(value, str):
                    token = _normalise_token(value)
                    if token:
                        tokens.add(token)
                elif isinstance(value, bool):
                    if value:
                        bool_flags[norm_key] = True
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    numeric_flags.setdefault(norm_key, []).append(float(value))
                elif isinstance(value, Mapping) or (
                    isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
                ):
                    stack.append(value)
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            for item in current:
                if isinstance(item, str):
                    token = _normalise_token(item)
                    if token:
                        tokens.add(token)
                elif isinstance(item, Mapping) or (
                    isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray))
                ):
                    stack.append(item)

    expanded_tokens: set[str] = set()
    for token in tokens:
        expanded_tokens.add(token)
        expanded_tokens.update(part for part in token.split("_") if part)

    return expanded_tokens, bool_flags, numeric_flags


def can_capture(ctx: Mapping[str, Any] | None) -> PermissionDecision:
    """Return whether capture should proceed based on ``ctx`` heuristics."""

    context = ctx or {}
    override = context.get("policy_override")
    if isinstance(override, str):
        decision = override.strip().lower()
        if decision in {"allow", "pause", "deny"}:
            return decision  # Caller explicitly chose the outcome.

    tokens, bool_flags, numeric_flags = _extract_tokens(context)

    if any(bool_flags.get(key) for key in _DENY_FLAG_KEYS):
        return "deny"
    if any(bool_flags.get(key) for key in _PAUSE_FLAG_KEYS):
        return "pause"

    for key in _NUMERIC_CHILD_KEYS:
        values = numeric_flags.get(key)
        if values and any(value > 0 for value in values):
            return "pause"

    if tokens & _DENY_TAGS:
        return "deny"
    if tokens & _PAUSE_TAGS:
        return "pause"

    return "allow"


__all__ = ["PermissionDecision", "can_capture"]


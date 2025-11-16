"""Unit tests for the policy permissions helper."""

from src.policy import can_capture


def test_can_capture_denies_restrooms():
    context = {"geo": {"place_type": "Restroom"}}
    assert can_capture(context) == "deny"


def test_can_capture_denies_credit_cards():
    context = {"signals": {"ocr": {"credit_card_ocr": True}}}
    assert can_capture(context) == "deny"


def test_can_capture_pauses_for_children():
    context = {"scene": {"detections": ["adult", "child"]}}
    assert can_capture(context) == "pause"


def test_can_capture_pauses_for_numeric_child_count():
    context = {"privacy": {"detected_children": 2}}
    assert can_capture(context) == "pause"


def test_can_capture_respects_overrides():
    context = {"policy_override": "Pause"}
    assert can_capture(context) == "pause"


def test_can_capture_allows_default():
    assert can_capture({}) == "allow"

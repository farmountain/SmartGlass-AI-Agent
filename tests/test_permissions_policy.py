"""Policy regression tests for capture permissions heuristics."""

from src.policy import can_capture


def test_clinic_context_is_denied():
    """Clinics marked as restricted should be rejected outright."""

    context = {
        "geo": {"place_type": "Clinic"},
        "privacy": {"is_restricted_location": True},
    }

    assert can_capture(context) == "deny"


def test_restroom_context_is_denied():
    """Restrooms are a hard block because of obvious privacy concerns."""

    context = {
        "geo": {"place_type": "Restroom"},
        "scene": {"detections": ["sink", "stall"]},
    }

    assert can_capture(context) == "deny"


def test_children_context_is_denied_when_policy_requires():
    """Child detections combined with an explicit policy flag should deny."""

    context = {
        "scene": {"detections": ["adult", "child"]},
        "privacy": {"deny_capture": True},
    }

    assert can_capture(context) == "deny"


def test_credit_card_capture_is_denied():
    """Any credit-card OCR signal is an automatic denial."""

    context = {
        "signals": {"ocr": {"credit_card_ocr": True}},
        "scene": {"text": ["Visa", "1234 5678 9012 3456"]},
    }

    assert can_capture(context) == "deny"


def test_ambiguous_gps_forces_pause():
    """GPS ambiguity should pause capture until a user confirms."""

    context = {
        "signals": {
            "gps": {
                "geo_requires_pause": True,
                "note": "Multi-path reflection makes the fix unreliable",
            }
        }
    }

    assert can_capture(context) == "pause"


def test_normal_environment_is_allowed():
    """Regular office environments without sensitive signals should pass."""

    context = {
        "geo": {"place_type": "Open office"},
        "scene": {"detections": ["desk", "adult"]},
    }

    assert can_capture(context) == "allow"

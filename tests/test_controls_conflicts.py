from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controls.grammar import GestureGrammar, load_detection_budgets

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "controls" / "gesture_replays.json"
CONFIG_PATH = Path("config/ux_budgets.yaml")


@pytest.fixture(scope="module")
def grammar() -> GestureGrammar:
    return GestureGrammar.default(CONFIG_PATH)


@pytest.fixture(scope="module")
def replay_fixtures() -> list[dict[str, object]]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_replay_sequences_match_expected_actions(grammar: GestureGrammar, replay_fixtures: list[dict[str, object]]) -> None:
    for fixture in replay_fixtures:
        resolution = grammar.replay(fixture["events"])
        assert resolution.action == fixture["expected_action"], fixture["id"]
        expected_accepted = fixture.get("expected_accepted")
        if expected_accepted is not None:
            assert len(resolution.accepted) == expected_accepted
            assert len(resolution.rejected) == len(fixture["events"]) - expected_accepted


def test_priority_arbitration_favours_emergency_stop(grammar: GestureGrammar) -> None:
    events = [
        {"gesture": "shake", "timestamp": 0.0},
        {"gesture": "circle", "timestamp": 0.3},
    ]
    resolution = grammar.replay(events)
    assert resolution.action == "emergency_stop"
    assert resolution.accepted_gestures == ("shake", "circle")


def test_unknown_gestures_are_rejected(grammar: GestureGrammar) -> None:
    events = [
        {"gesture": "shadow_tap", "timestamp": 1.0},
        {"gesture": "double_tap", "timestamp": 1.2},
    ]
    resolution = grammar.replay(events)
    assert resolution.action == "confirm"
    assert resolution.accepted_gestures == ("double_tap",)
    assert any(event.gesture == "shadow_tap" for event in resolution.rejected)


def test_detection_budget_matches_config(grammar: GestureGrammar) -> None:
    expected = load_detection_budgets(CONFIG_PATH)
    assert grammar.detection_budget == expected

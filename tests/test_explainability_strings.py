from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "short_hud.j2"
HAPTICS_PATH = ROOT / "auditory" / "haptics.json"
SUNLIT_FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "scenes" / "sunlit_contrast.json"


def _count_words(text: str) -> int:
    tokens = re.findall(r"\{\{\s*[\w\.]+\s*\}\}|[A-Za-z0-9_=\.]+", text)
    return len(tokens)


def _render_template(text: str, context: dict[str, object]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise KeyError(f"Missing key '{key}' for template rendering")
        return str(context[key])

    return re.sub(r"\{\{\s*([\w\.]+)\s*\}\}", repl, text)


@pytest.fixture(scope="module")
def template_text() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8").strip()


@pytest.fixture(scope="module")
def sunlit_contrast_fixtures() -> list[dict[str, object]]:
    with SUNLIT_FIXTURES_PATH.open("r", encoding="utf-8") as handle:
        fixtures = json.load(handle)
    assert fixtures, "Expected at least one sunlit contrast fixture"
    return fixtures


@pytest.fixture(scope="module")
def haptic_map() -> dict[str, list[int]]:
    with HAPTICS_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {key: list(value) for key, value in data.items()}


def test_short_hud_template_word_budget_and_slots(template_text: str) -> None:
    assert _count_words(template_text) <= 35
    assert "{{ confidence }}" in template_text
    assert "{{ formula }}" in template_text
    assert "Contrast:" in template_text


def test_sunlit_contrast_fixtures_render_cleanly(
    template_text: str, sunlit_contrast_fixtures: list[dict[str, object]]
) -> None:
    for fixture in sunlit_contrast_fixtures:
        assert "sunlit" in str(fixture["lighting"]).lower()
        assert str(fixture["contrast_label"]).lower().startswith("sunlit")
        assert 0 < float(fixture["contrast_ratio"]) < 1
        rendered = _render_template(template_text, fixture)
        assert _count_words(rendered) <= 35
        assert "sunlit" in rendered.lower()


def test_haptic_sequences_cover_sunlit_cases(
    haptic_map: dict[str, list[int]], sunlit_contrast_fixtures: list[dict[str, object]]
) -> None:
    required_events = {
        "low_confidence",
        "obstacle_warning",
        "goal_reached",
        "ambient_adjust",
        "sunlit_contrast_notice",
    }
    assert required_events.issubset(haptic_map.keys())

    for event, pattern in haptic_map.items():
        assert isinstance(pattern, list) and pattern, f"Missing pattern for {event}"
        assert all(isinstance(step, int) and step > 0 for step in pattern)
        assert len(pattern) % 2 == 1, "Patterns should end with a final hold duration"
        assert len(set(pattern)) > 1, "Patterns should not be monotone pulses"

    assert max(haptic_map["obstacle_warning"]) > max(haptic_map["low_confidence"])
    assert min(haptic_map["ambient_adjust"]) < min(haptic_map["goal_reached"])

    for fixture in sunlit_contrast_fixtures:
        assert fixture["haptic"] in haptic_map

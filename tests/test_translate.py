from pathlib import Path
import importlib.util
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "vision" / "translate_sign.py"
spec = importlib.util.spec_from_file_location("vision.translate_sign", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)
TranslateSignRoute = module.TranslateSignRoute

ROUTE_CONFIG_PATH = ROOT / "config" / "routes" / "translate_sign.yaml"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "signs" / "translate_sign.json"


@pytest.fixture(scope="module")
def fixtures():
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_translation_response_content(fixtures):
    runner = TranslateSignRoute()
    fixture = fixtures[0]
    result = runner.run(fixture)
    assert result.translation == fixture["translation"]
    assert fixture["translation"] in result.response
    assert fixture["original_text"] in result.response
    assert result.language == fixture["expected_language_name"]
    assert result.word_count <= 35
    for keyword in fixture.get("glossary_hits", []):
        assert keyword.lower() in result.response.lower()
    assert "Hazard:" in result.response


def test_low_confidence_triggers_tip(fixtures):
    runner = TranslateSignRoute()
    fixture = next(item for item in fixtures if item["confidence"] < runner._min_conf)
    result = runner.run(fixture)
    assert not result.is_confident
    assert "Tip:" in result.response
    assert runner._low_conf_tip.replace("Tip:", "").strip().split()[0] in result.response


def test_confident_tail_uses_steady_message(fixtures):
    runner = TranslateSignRoute()
    fixture = fixtures[1]
    result = runner.run(fixture)
    assert result.is_confident
    assert runner._steady_message in result.response


def test_latency_budgets_and_totals(fixtures):
    with ROUTE_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        route_config = json.load(handle)
    budgets = {
        stage: route_config[stage]["latency_budget_ms"]
        for stage in ("capture", "perceive", "extract", "respond")
    }
    runner = TranslateSignRoute()
    for fixture in fixtures:
        result = runner.run(fixture)
        for stage, budget in budgets.items():
            assert result.latencies[stage] <= budget
        assert result.latencies["total"] <= sum(budgets.values())


def test_schema_identity_passthrough():
    runner = TranslateSignRoute()
    assert runner._schema.get("postprocess") == "identity"


def test_route_config_includes_latency_budgets():
    with ROUTE_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        route_config = json.load(handle)
    for stage in ("capture", "perceive", "extract", "respond"):
        assert "latency_budget_ms" in route_config[stage]


__all__ = [
    "fixtures",
    "test_translation_response_content",
    "test_low_confidence_triggers_tip",
    "test_confident_tail_uses_steady_message",
    "test_latency_budgets_and_totals",
    "test_schema_identity_passthrough",
    "test_route_config_includes_latency_budgets",
]

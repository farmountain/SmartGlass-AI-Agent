from pathlib import Path
import importlib.util
import sys
import json

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "vision" / "route_runner.py"
spec = importlib.util.spec_from_file_location("vision.route_runner", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)
ExplainThisRoute = module.ExplainThisRoute


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "scenes" / "explain_fixtures.json"


@pytest.fixture(scope="module")
def fixtures():
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_top3_accuracy(fixtures):
    runner = ExplainThisRoute()
    successes = 0
    for fixture in fixtures:
        result = runner.run(fixture)
        if fixture["ground_truth"] in [pred.label for pred in result.predictions]:
            successes += 1
    accuracy = successes / len(fixtures)
    assert accuracy >= 0.9, f"Expected >=0.9 top-3 accuracy, got {accuracy}"


def test_response_word_budget_and_confidence(fixtures):
    runner = ExplainThisRoute()
    for fixture in fixtures:
        result = runner.run(fixture)
        assert result.word_count <= 35, f"Response too long: {result.response}"
        top1 = result.predictions[0]
        if top1.confidence < 0.65:
            assert "Tip:" in result.response, "Low confidence tip missing"
        else:
            assert "Confidence steady." in result.response


def test_latency_logging(fixtures):
    runner = ExplainThisRoute()
    for fixture in fixtures:
        result = runner.run(fixture)
        latencies = result.latencies
        assert {"capture", "perceive", "extract", "respond", "total"}.issubset(latencies.keys())
        assert latencies["capture"] <= 150
        assert latencies["perceive"] <= 800
        assert latencies["extract"] <= 100
        assert latencies["respond"] <= 150
        assert latencies["total"] <= 2200

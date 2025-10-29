from pathlib import Path
import importlib.util
import json

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "vision" / "unit_price.py"
spec = importlib.util.spec_from_file_location("vision.unit_price", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)
UnitPriceRoute = module.UnitPriceRoute

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "shelves" / "unit_price.json"


@pytest.fixture(scope="module")
def fixtures():
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_unit_price_computation(fixtures):
    runner = UnitPriceRoute()
    matched = 0
    for fixture in fixtures:
        result = runner.run(fixture)
        expected = fixture["expected_unit_price"]
        if expected is not None:
            matched += 1
            assert result.matched
            assert result.unit_price == pytest.approx(expected, rel=1e-3)
            assert fixture["expected_result_label"] in result.response
            assert "/100g" in result.response
            if fixture.get("expected_weight_label"):
                assert fixture["expected_weight_label"] in result.response
        else:
            assert not result.matched
            assert "Need price and weight" in result.response
            assert "Tip:" in result.response
    assert matched >= 12


def test_word_budget_and_formula(fixtures):
    runner = UnitPriceRoute()
    for fixture in fixtures:
        result = runner.run(fixture)
        assert result.word_count <= 35
        if result.matched:
            assert "Unit price" in result.response
            assert "÷" in result.response


def test_latency_bounds(fixtures):
    runner = UnitPriceRoute()
    for fixture in fixtures:
        result = runner.run(fixture)
        latencies = result.latencies
        assert latencies["capture"] <= 150
        assert latencies["perceive"] <= 800
        assert latencies["extract"] <= 100
        assert latencies["respond"] <= 150
        assert latencies["total"] <= 2200


def test_imperial_unit_modes(fixtures):
    runners = {}
    for fixture in fixtures:
        expectation = fixture.get("imperial_expectations")
        if not expectation:
            continue
        mode = expectation["mode"]
        if mode not in runners:
            runners[mode] = UnitPriceRoute(unit_mode=mode)
        result = runners[mode].run(fixture)
        assert result.matched
        assert result.unit_price == pytest.approx(expectation["unit_price"], rel=1e-3)
        assert expectation["result_label"] in result.response
        if fixture.get("expected_weight_label"):
            assert fixture["expected_weight_label"] in result.response

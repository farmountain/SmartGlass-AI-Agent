from pathlib import Path
import importlib.util
import json
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "vision" / "price_scan.py"
spec = importlib.util.spec_from_file_location("vision.price_scan", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)
PriceScanRoute = module.PriceScanRoute

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "shelves" / "price_scan.json"


@pytest.fixture(scope="module")
def fixtures():
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_price_pattern_named_groups():
    runner = PriceScanRoute()
    pattern = runner._pattern

    match = pattern.search("Imported tea £2.99 per box")
    assert match and match.group("currency") == "£"

    gbp_match = pattern.search("Local cheddar GBP 4.50")
    assert gbp_match and gbp_match.group("gbp") == "GBP"
    assert gbp_match.group("currency") is None
    assert gbp_match.group("value") == "4.50"

    jpy_match = pattern.search("Sushi rice JPY 540 bag")
    assert jpy_match and jpy_match.group("jpy") == "JPY"
    assert jpy_match.group("value") == "540"


def test_price_detection_and_precision(fixtures):
    runner = PriceScanRoute()
    tp = 0
    fp = 0
    fn = 0
    cer_scores = []
    for fixture in fixtures:
        result = runner.run(fixture)
        expected = fixture["expected"]
        if expected:
            assert result.matched, f"Expected match for {fixture['id']}"
            assert result.formatted == expected, f"Incorrect price for {fixture['id']}"
            numeric = re.sub(r"[^\d.,]", "", expected)
            expected_value = module.PriceScanRoute._to_float(numeric)
            assert result.value == pytest.approx(expected_value)
            assert result.cer is not None and result.cer <= 0.1
            cer_scores.append(result.cer)
            tp += 1
        else:
            if result.matched:
                fp += 1
            else:
                fn += 1
                assert "Tip:" in result.response
    precision = tp / max(1, tp + fp)
    assert precision >= 0.95, f"Precision below target: {precision}"
    assert all(score <= 0.1 for score in cer_scores), "CER exceeded 0.1"
    assert fn == 10, "Negatives should not detect prices"


def test_response_budget_and_confidence(fixtures):
    runner = PriceScanRoute()
    for fixture in fixtures:
        result = runner.run(fixture)
        assert result.word_count <= 35
        if fixture["expected"]:
            assert fixture["expected"] in result.response
            assert "Confidence" in result.response
        else:
            assert "No price" in result.response


def test_latency_budget(fixtures):
    runner = PriceScanRoute()
    for fixture in fixtures:
        result = runner.run(fixture)
        latencies = result.latencies
        assert latencies["capture"] <= 150
        assert latencies["perceive"] <= 800
        assert latencies["extract"] <= 100
        assert latencies["respond"] <= 150
        assert latencies["total"] <= 2200

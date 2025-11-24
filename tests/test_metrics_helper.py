"""Unit tests for the metrics helper utilities."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

src_root = Path(__file__).resolve().parent.parent / "src"
if "src" not in sys.modules:
    stub = types.ModuleType("src")
    stub.__path__ = [str(src_root)]
    sys.modules["src"] = stub

from src.utils.metrics import MetricsRegistry, record_latency, metrics


def test_nested_latency_recording(monkeypatch):
    clock = {"now": 0.0}

    def fake_time():
        return clock["now"]

    registry = MetricsRegistry(time_fn=fake_time)

    with registry.record_latency("ASR"):
        clock["now"] += 0.1
        with registry.record_latency("ASR"):
            clock["now"] += 0.2
        clock["now"] += 0.3

    snapshot = registry.snapshot()
    assert snapshot["latencies"]["ASR"]["count"] == 2
    assert snapshot["latencies"]["ASR"]["total"] == pytest.approx(0.8)
    assert snapshot["latencies"]["all"]["count"] == 2
    assert snapshot["latencies"]["all"]["total"] == pytest.approx(0.8)


def test_decorator_usage(monkeypatch):
    metrics.reset()

    @record_latency("LLM")
    def _fake_llm_call():
        return "ok"

    assert _fake_llm_call() == "ok"

    snapshot = metrics.snapshot()
    assert snapshot["latencies"]["LLM"]["count"] == 1
    assert snapshot["latencies"]["all"]["count"] == 1

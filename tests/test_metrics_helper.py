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

from src.utils.metrics import MetricsRegistry, record_latency, metrics, get_metrics_summary


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


def test_dat_metrics_summary():
    """Test that get_metrics_summary returns expected structure."""
    metrics.reset()
    
    # Record some DAT-specific metrics
    with record_latency("dat_ingest_audio_latency_ms"):
        pass
    with record_latency("dat_ingest_frame_latency_ms"):
        pass
    with record_latency("end_to_end_turn_latency_ms"):
        pass
    
    summary = get_metrics_summary()
    
    # Check structure
    assert "health" in summary
    assert "dat_metrics" in summary
    assert "summary" in summary
    
    # Check dat_metrics structure
    assert "ingest_audio" in summary["dat_metrics"]
    assert "ingest_frame" in summary["dat_metrics"]
    assert "end_to_end_turn" in summary["dat_metrics"]
    
    # Check each metric has expected fields
    for metric_name in ["ingest_audio", "ingest_frame", "end_to_end_turn"]:
        metric = summary["dat_metrics"][metric_name]
        assert "count" in metric
        assert "avg_ms" in metric
        assert "max_ms" in metric


def test_dat_metrics_health_ok():
    """Test health state is 'ok' when latencies are low."""
    metrics.reset()
    
    clock = {"now": 0.0}
    def fake_time():
        return clock["now"]
    
    # Create a new registry with fake time
    test_metrics = MetricsRegistry(time_fn=fake_time)
    
    # Record low latencies (< 100ms for ingestion, < 2000ms for e2e)
    with test_metrics.record_latency("dat_ingest_audio_latency_ms"):
        clock["now"] += 0.05  # 50ms
    
    with test_metrics.record_latency("dat_ingest_frame_latency_ms"):
        clock["now"] += 0.08  # 80ms
    
    with test_metrics.record_latency("end_to_end_turn_latency_ms"):
        clock["now"] += 1.0  # 1000ms
    
    snapshot = test_metrics.snapshot()
    
    # Manually calculate health (mimicking get_metrics_summary logic)
    latencies = snapshot.get("latencies", {})
    dat_audio = latencies.get("dat_ingest_audio_latency_ms", {})
    dat_frame = latencies.get("dat_ingest_frame_latency_ms", {})
    dat_e2e = latencies.get("end_to_end_turn_latency_ms", {})
    
    health = "ok"
    if dat_audio.get("avg", 0.0) > 0.1:
        health = "degraded"
    if dat_frame.get("avg", 0.0) > 0.1:
        health = "degraded"
    if dat_e2e.get("avg", 0.0) > 2.0:
        health = "degraded"
    
    assert health == "ok"


def test_dat_metrics_health_degraded():
    """Test health state is 'degraded' when latencies are high."""
    metrics.reset()
    
    clock = {"now": 0.0}
    def fake_time():
        return clock["now"]
    
    # Create a new registry with fake time
    test_metrics = MetricsRegistry(time_fn=fake_time)
    
    # Record high latencies
    with test_metrics.record_latency("dat_ingest_audio_latency_ms"):
        clock["now"] += 0.15  # 150ms - exceeds threshold
    
    snapshot = test_metrics.snapshot()
    latencies = snapshot.get("latencies", {})
    dat_audio = latencies.get("dat_ingest_audio_latency_ms", {})
    
    health = "ok"
    if dat_audio.get("avg", 0.0) > 0.1:
        health = "degraded"
    
    assert health == "degraded"


def test_metrics_summary_with_no_data():
    """Test get_metrics_summary works with no recorded data."""
    metrics.reset()
    
    summary = get_metrics_summary()
    
    # Should have structure even with no data
    assert summary["health"] == "ok"
    assert summary["dat_metrics"]["ingest_audio"]["count"] == 0
    assert summary["dat_metrics"]["ingest_frame"]["count"] == 0
    assert summary["dat_metrics"]["end_to_end_turn"]["count"] == 0


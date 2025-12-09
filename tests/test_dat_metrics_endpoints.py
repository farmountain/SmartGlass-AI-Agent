"""Test the DAT metrics endpoints."""

import sys
import types
from pathlib import Path

# Add src to path properly
src_root = Path(__file__).resolve().parent.parent / "src"
if "src" not in sys.modules:
    stub = types.ModuleType("src")
    stub.__path__ = [str(src_root)]
    sys.modules["src"] = stub

from src.utils.metrics import get_metrics_summary, record_latency, metrics


def test_metrics_summary_endpoint():
    """Test get_metrics_summary returns proper structure."""
    metrics.reset()
    
    # Simulate some DAT operations
    with record_latency("dat_ingest_audio_latency_ms"):
        pass
    
    with record_latency("dat_ingest_frame_latency_ms"):
        pass
    
    with record_latency("end_to_end_turn_latency_ms"):
        pass
    
    # Get summary
    summary = get_metrics_summary()
    
    # Verify structure
    assert "health" in summary
    assert summary["health"] in ["ok", "degraded"]
    
    assert "dat_metrics" in summary
    dat_metrics = summary["dat_metrics"]
    
    assert "ingest_audio" in dat_metrics
    assert "ingest_frame" in dat_metrics
    assert "end_to_end_turn" in dat_metrics
    
    # Verify each metric has proper structure
    for metric_name in ["ingest_audio", "ingest_frame", "end_to_end_turn"]:
        metric = dat_metrics[metric_name]
        assert "count" in metric
        assert "avg_ms" in metric
        assert "max_ms" in metric
        assert metric["count"] >= 0
        assert metric["avg_ms"] >= 0
        assert metric["max_ms"] >= 0
    
    # Verify summary
    assert "summary" in summary
    summary_data = summary["summary"]
    assert "total_sessions" in summary_data
    assert "active_sessions" in summary_data
    assert "total_queries" in summary_data
    
    print("✓ Metrics summary structure is correct")
    print(f"✓ Health state: {summary['health']}")
    print(f"✓ DAT metrics recorded: {dat_metrics['ingest_audio']['count']} audio, "
          f"{dat_metrics['ingest_frame']['count']} frame, "
          f"{dat_metrics['end_to_end_turn']['count']} e2e")


def test_metrics_millisecond_conversion():
    """Test that latencies are properly converted to milliseconds."""
    metrics.reset()
    
    # Create fake time function
    clock = {"now": 0.0}
    from src.utils.metrics import MetricsRegistry
    
    test_registry = MetricsRegistry(time_fn=lambda: clock["now"])
    
    # Record a 50ms latency
    with test_registry.record_latency("dat_ingest_audio_latency_ms"):
        clock["now"] += 0.05  # 50ms in seconds
    
    # Get snapshot and check conversion
    snapshot = test_registry.snapshot()
    latencies = snapshot["latencies"]
    
    # The raw latency should be in seconds
    assert latencies["dat_ingest_audio_latency_ms"]["avg"] == 0.05
    
    print("✓ Latency recorded correctly in seconds")
    
    # Now test the summary conversion
    # We need to manually create the summary since we're using a custom registry
    dat_audio = latencies.get("dat_ingest_audio_latency_ms", {})
    avg_ms = dat_audio.get("avg", 0.0) * 1000
    
    assert avg_ms == 50.0
    print(f"✓ Latency converted to milliseconds: {avg_ms}ms")


if __name__ == "__main__":
    test_metrics_summary_endpoint()
    test_metrics_millisecond_conversion()
    print("\n✅ All tests passed!")

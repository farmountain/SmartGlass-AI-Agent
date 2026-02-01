"""
Tests for Telemetry Interface
Validates event schema, collector behavior, and integration patterns.
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Direct import to avoid circular dependencies
import importlib.util
spec = importlib.util.spec_from_file_location("telemetry", project_root / "src" / "telemetry.py")
telemetry_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(telemetry_module)

EventType = telemetry_module.EventType
InMemoryCollector = telemetry_module.InMemoryCollector
LatencyTracker = telemetry_module.LatencyTracker
LoggingCollector = telemetry_module.LoggingCollector
Severity = telemetry_module.Severity
TelemetryCollector = telemetry_module.TelemetryCollector
TelemetryEvent = telemetry_module.TelemetryEvent


class TestTelemetryEvent:
    """Test TelemetryEvent data structure."""

    def test_event_creation(self):
        """Test creating a telemetry event."""
        event = TelemetryEvent(
            event_type=EventType.LATENCY,
            timestamp="2026-02-01T12:00:00Z",
            component="ASR",
            severity=Severity.INFO,
            metrics={"duration_ms": 150.5},
            context={"model": "whisper-base"},
            session_id="session_123",
        )
        
        assert event.event_type == EventType.LATENCY
        assert event.timestamp == "2026-02-01T12:00:00Z"
        assert event.component == "ASR"
        assert event.severity == Severity.INFO
        assert event.metrics["duration_ms"] == 150.5
        assert event.context["model"] == "whisper-base"
        assert event.session_id == "session_123"

    def test_event_to_dict(self):
        """Test serializing event to dictionary."""
        event = TelemetryEvent(
            event_type=EventType.ERROR,
            timestamp="2026-02-01T12:00:00Z",
            component="Vision",
            severity=Severity.ERROR,
            metrics={},
            context={"error": "CLIP model failed"},
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "error"
        assert event_dict["timestamp"] == "2026-02-01T12:00:00Z"
        assert event_dict["component"] == "Vision"
        assert event_dict["severity"] == "error"
        assert event_dict["context"]["error"] == "CLIP model failed"

    def test_event_defaults(self):
        """Test event with default values."""
        event = TelemetryEvent(
            event_type=EventType.USAGE,
            timestamp="2026-02-01T12:00:00Z",
            component="LLM",
        )
        
        assert event.severity == Severity.INFO
        assert event.metrics == {}
        assert event.context == {}
        assert event.session_id is None


class TestInMemoryCollector:
    """Test in-memory telemetry collector."""

    def test_collect_event(self):
        """Test collecting events in memory."""
        collector = InMemoryCollector()
        
        event1 = TelemetryEvent(
            event_type=EventType.LATENCY,
            timestamp="2026-02-01T12:00:00Z",
            component="ASR",
        )
        event2 = TelemetryEvent(
            event_type=EventType.ERROR,
            timestamp="2026-02-01T12:00:01Z",
            component="Vision",
        )
        
        collector.collect(event1)
        collector.collect(event2)
        
        assert len(collector.events) == 2
        assert collector.events[0] == event1
        assert collector.events[1] == event2

    def test_clear_events(self):
        """Test clearing collected events."""
        collector = InMemoryCollector()
        
        event = TelemetryEvent(
            event_type=EventType.USAGE,
            timestamp="2026-02-01T12:00:00Z",
            component="LLM",
        )
        collector.collect(event)
        
        assert len(collector.events) == 1
        
        collector.clear()
        
        assert len(collector.events) == 0

    def test_get_events_by_type(self):
        """Test filtering events by type."""
        collector = InMemoryCollector()
        
        collector.collect(
            TelemetryEvent(
                event_type=EventType.LATENCY,
                timestamp="2026-02-01T12:00:00Z",
                component="ASR",
            )
        )
        collector.collect(
            TelemetryEvent(
                event_type=EventType.ERROR,
                timestamp="2026-02-01T12:00:01Z",
                component="Vision",
            )
        )
        collector.collect(
            TelemetryEvent(
                event_type=EventType.LATENCY,
                timestamp="2026-02-01T12:00:02Z",
                component="LLM",
            )
        )
        
        latency_events = collector.get_events_by_type(EventType.LATENCY)
        error_events = collector.get_events_by_type(EventType.ERROR)
        
        assert len(latency_events) == 2
        assert len(error_events) == 1
        assert latency_events[0].component == "ASR"
        assert latency_events[1].component == "LLM"

    def test_get_events_by_component(self):
        """Test filtering events by component."""
        collector = InMemoryCollector()
        
        collector.collect(
            TelemetryEvent(
                event_type=EventType.LATENCY,
                timestamp="2026-02-01T12:00:00Z",
                component="ASR",
            )
        )
        collector.collect(
            TelemetryEvent(
                event_type=EventType.ERROR,
                timestamp="2026-02-01T12:00:01Z",
                component="ASR",
            )
        )
        collector.collect(
            TelemetryEvent(
                event_type=EventType.USAGE,
                timestamp="2026-02-01T12:00:02Z",
                component="Vision",
            )
        )
        
        asr_events = collector.get_events_by_component("ASR")
        vision_events = collector.get_events_by_component("Vision")
        
        assert len(asr_events) == 2
        assert len(vision_events) == 1


class TestLoggingCollector:
    """Test logging-based telemetry collector."""

    def test_collect_with_info_severity(self, caplog):
        """Test collecting INFO level events."""
        collector = LoggingCollector()
        
        with caplog.at_level(logging.INFO):
            event = TelemetryEvent(
                event_type=EventType.LATENCY,
                timestamp="2026-02-01T12:00:00Z",
                component="ASR",
                severity=Severity.INFO,
            )
            collector.collect(event)
        
        assert "[latency] ASR" in caplog.text

    def test_collect_with_error_severity(self, caplog):
        """Test collecting ERROR level events."""
        collector = LoggingCollector()
        
        with caplog.at_level(logging.ERROR):
            event = TelemetryEvent(
                event_type=EventType.ERROR,
                timestamp="2026-02-01T12:00:00Z",
                component="Vision",
                severity=Severity.ERROR,
                context={"error": "Model failed"},
            )
            collector.collect(event)
        
        assert "[error] Vision" in caplog.text


class TestTelemetryCollectorHelpers:
    """Test TelemetryCollector convenience methods."""

    def test_record_latency(self):
        """Test recording latency events."""
        collector = InMemoryCollector()
        
        collector.record_latency(
            "ASR",
            duration_ms=150.5,
            session_id="session_123",
            context={"model": "whisper"},
        )
        
        events = collector.get_events_by_type(EventType.LATENCY)
        assert len(events) == 1
        assert events[0].component == "ASR"
        assert events[0].metrics["duration_ms"] == 150.5
        assert events[0].session_id == "session_123"
        assert events[0].context["model"] == "whisper"

    def test_record_error(self):
        """Test recording error events."""
        collector = InMemoryCollector()
        
        collector.record_error(
            "Vision",
            error_message="CLIP model failed to load",
            severity=Severity.CRITICAL,
            session_id="session_456",
            context={"stack_trace": "..."},
        )
        
        events = collector.get_events_by_type(EventType.ERROR)
        assert len(events) == 1
        assert events[0].component == "Vision"
        assert events[0].severity == Severity.CRITICAL
        assert events[0].context["error_message"] == "CLIP model failed to load"
        assert events[0].context["stack_trace"] == "..."

    def test_record_usage(self):
        """Test recording usage events."""
        collector = InMemoryCollector()
        
        collector.record_usage(
            "LLM",
            metrics={"token_count": 256, "api_calls": 1},
            session_id="session_789",
            context={"model": "gpt-3.5-turbo"},
        )
        
        events = collector.get_events_by_type(EventType.USAGE)
        assert len(events) == 1
        assert events[0].component == "LLM"
        assert events[0].metrics["token_count"] == 256
        assert events[0].metrics["api_calls"] == 1

    def test_record_safety_event(self):
        """Test recording safety moderation events."""
        collector = InMemoryCollector()
        
        collector.record_safety_event(
            "SafetyGuard",
            blocked=True,
            reason="Harmful content detected",
            severity=Severity.WARNING,
            session_id="session_999",
            context={"categories": ["violence", "dangerous_activity"]},
        )
        
        events = collector.get_events_by_type(EventType.SAFETY)
        assert len(events) == 1
        assert events[0].component == "SafetyGuard"
        assert events[0].context["blocked"] is True
        assert events[0].context["reason"] == "Harmful content detected"
        assert events[0].context["categories"] == ["violence", "dangerous_activity"]


class TestLatencyTracker:
    """Test latency tracking context manager."""

    def test_track_latency(self):
        """Test tracking latency with context manager."""
        collector = InMemoryCollector()
        
        with LatencyTracker(collector, "TestComponent", session_id="session_abc"):
            time.sleep(0.01)  # Simulate work
        
        events = collector.get_events_by_type(EventType.LATENCY)
        assert len(events) == 1
        assert events[0].component == "TestComponent"
        assert events[0].metrics["duration_ms"] >= 10  # At least 10ms
        assert events[0].session_id == "session_abc"

    def test_track_latency_with_context(self):
        """Test latency tracking with additional context."""
        collector = InMemoryCollector()
        
        with LatencyTracker(
            collector,
            "ASR",
            session_id="session_xyz",
            context={"model": "whisper-base", "language": "en"},
        ):
            time.sleep(0.005)
        
        events = collector.get_events_by_type(EventType.LATENCY)
        assert len(events) == 1
        assert events[0].context["model"] == "whisper-base"
        assert events[0].context["language"] == "en"

    def test_latency_tracker_with_exception(self):
        """Test that latency is still recorded when exception occurs."""
        collector = InMemoryCollector()
        
        with pytest.raises(ValueError):
            with LatencyTracker(collector, "FailedComponent"):
                raise ValueError("Simulated error")
        
        # Latency should still be recorded despite exception
        events = collector.get_events_by_type(EventType.LATENCY)
        assert len(events) == 1
        assert events[0].component == "FailedComponent"


class TestEndToEndTelemetry:
    """Test end-to-end telemetry integration patterns."""

    def test_multimodal_query_telemetry(self):
        """Test telemetry collection for a multimodal query workflow."""
        collector = InMemoryCollector()
        session_id = "session_e2e_001"
        
        # Simulate multimodal query processing
        with LatencyTracker(collector, "E2E", session_id):
            # ASR phase
            with LatencyTracker(collector, "ASR", session_id):
                time.sleep(0.005)
            
            # Vision phase
            with LatencyTracker(collector, "Vision", session_id):
                time.sleep(0.003)
            
            # LLM phase
            with LatencyTracker(collector, "LLM", session_id):
                time.sleep(0.007)
            
            # Safety check
            collector.record_safety_event(
                "SafetyGuard",
                blocked=False,
                reason="Content passed all checks",
                session_id=session_id,
            )
            
            # Usage metrics
            collector.record_usage(
                "SmartGlassAgent",
                metrics={"actions_count": 2, "safety_blocked": 0},
                session_id=session_id,
            )
        
        # Verify all events collected
        assert len(collector.events) == 6
        
        # Verify latency events
        latency_events = collector.get_events_by_type(EventType.LATENCY)
        assert len(latency_events) == 4
        assert {e.component for e in latency_events} == {"E2E", "ASR", "Vision", "LLM"}
        
        # Verify safety event
        safety_events = collector.get_events_by_type(EventType.SAFETY)
        assert len(safety_events) == 1
        assert not safety_events[0].context["blocked"]
        
        # Verify usage event
        usage_events = collector.get_events_by_type(EventType.USAGE)
        assert len(usage_events) == 1
        assert usage_events[0].metrics["actions_count"] == 2

    def test_error_handling_with_telemetry(self):
        """Test telemetry during error scenarios."""
        collector = InMemoryCollector()
        session_id = "session_error_001"
        
        # Simulate error during vision processing
        try:
            with LatencyTracker(collector, "Vision", session_id):
                collector.record_error(
                    "Vision",
                    error_message="CLIP model out of memory",
                    severity=Severity.ERROR,
                    session_id=session_id,
                    context={"gpu_memory_mb": 0},
                )
                raise RuntimeError("CLIP model out of memory")
        except RuntimeError:
            pass
        
        # Verify events
        latency_events = collector.get_events_by_type(EventType.LATENCY)
        error_events = collector.get_events_by_type(EventType.ERROR)
        
        assert len(latency_events) == 1
        assert len(error_events) == 1
        assert error_events[0].context["error_message"] == "CLIP model out of memory"
        assert error_events[0].severity == Severity.ERROR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

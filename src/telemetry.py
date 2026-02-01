"""
Telemetry Interface for SmartGlass AI Agent
Provides structured event logging for latency tracking, error reporting, and usage metrics.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of telemetry events."""
    LATENCY = "latency"
    ERROR = "error"
    USAGE = "usage"
    SAFETY = "safety"
    ACTION = "action"


class Severity(Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TelemetryEvent:
    """
    Structured telemetry event.
    
    Attributes:
        event_type: Type of event (latency, error, usage, etc.)
        timestamp: Event timestamp (ISO 8601)
        component: Component that generated the event (e.g., "ASR", "Vision", "LLM")
        severity: Event severity level
        metrics: Numeric metrics (e.g., latency_ms, token_count)
        context: Additional context (e.g., error details, query text)
        session_id: Optional session identifier for correlation
    """
    event_type: EventType
    timestamp: str
    component: str
    severity: Severity = Severity.INFO
    metrics: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "component": self.component,
            "severity": self.severity.value,
            "metrics": self.metrics,
            "context": self.context,
            "session_id": self.session_id,
        }


class TelemetryCollector(ABC):
    """
    Abstract base class for telemetry collection.
    
    Implementations can send events to:
    - Local log files
    - Cloud telemetry services (Application Insights, CloudWatch, etc.)
    - In-memory buffers for testing
    """

    @abstractmethod
    def collect(self, event: TelemetryEvent) -> None:
        """
        Collect a telemetry event.
        
        Args:
            event: TelemetryEvent to collect
        """
        pass

    def record_latency(
        self,
        component: str,
        duration_ms: float,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a latency measurement.
        
        Args:
            component: Component name (e.g., "ASR", "Vision", "LLM")
            duration_ms: Latency in milliseconds
            session_id: Optional session ID
            context: Additional context
        """
        event = TelemetryEvent(
            event_type=EventType.LATENCY,
            timestamp=datetime.utcnow().isoformat() + "Z",
            component=component,
            severity=Severity.INFO,
            metrics={"duration_ms": duration_ms},
            context=context or {},
            session_id=session_id,
        )
        self.collect(event)

    def record_error(
        self,
        component: str,
        error_message: str,
        severity: Severity = Severity.ERROR,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record an error event.
        
        Args:
            component: Component name
            error_message: Error message
            severity: Error severity
            session_id: Optional session ID
            context: Additional context (e.g., stack trace, input data)
        """
        event = TelemetryEvent(
            event_type=EventType.ERROR,
            timestamp=datetime.utcnow().isoformat() + "Z",
            component=component,
            severity=severity,
            context={"error_message": error_message, **(context or {})},
            session_id=session_id,
        )
        self.collect(event)

    def record_usage(
        self,
        component: str,
        metrics: Dict[str, float],
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record usage metrics (e.g., token count, API calls).
        
        Args:
            component: Component name
            metrics: Usage metrics dict
            session_id: Optional session ID
            context: Additional context
        """
        event = TelemetryEvent(
            event_type=EventType.USAGE,
            timestamp=datetime.utcnow().isoformat() + "Z",
            component=component,
            severity=Severity.INFO,
            metrics=metrics,
            context=context or {},
            session_id=session_id,
        )
        self.collect(event)

    def record_safety_event(
        self,
        component: str,
        blocked: bool,
        reason: str,
        severity: Severity = Severity.WARNING,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a safety moderation event.
        
        Args:
            component: Component name
            blocked: Whether content was blocked
            reason: Moderation reason
            severity: Event severity
            session_id: Optional session ID
            context: Additional context
        """
        event = TelemetryEvent(
            event_type=EventType.SAFETY,
            timestamp=datetime.utcnow().isoformat() + "Z",
            component=component,
            severity=severity,
            context={
                "blocked": blocked,
                "reason": reason,
                **(context or {}),
            },
            session_id=session_id,
        )
        self.collect(event)


class LoggingCollector(TelemetryCollector):
    """
    Simple telemetry collector that logs events to Python logger.
    
    Suitable for development and debugging. For production, use a cloud-based collector.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize logging collector.
        
        Args:
            logger: Optional logger instance (defaults to module logger)
        """
        self.logger = logger or logging.getLogger(__name__)

    def collect(self, event: TelemetryEvent) -> None:
        """Log event to Python logger with appropriate severity."""
        log_level = {
            Severity.DEBUG: logging.DEBUG,
            Severity.INFO: logging.INFO,
            Severity.WARNING: logging.WARNING,
            Severity.ERROR: logging.ERROR,
            Severity.CRITICAL: logging.CRITICAL,
        }[event.severity]

        self.logger.log(
            log_level,
            f"[{event.event_type.value}] {event.component}",
            extra=event.to_dict(),
        )


class InMemoryCollector(TelemetryCollector):
    """
    In-memory telemetry collector for testing.
    
    Stores events in a list for inspection in tests.
    """

    def __init__(self):
        """Initialize in-memory collector."""
        self.events: list[TelemetryEvent] = []

    def collect(self, event: TelemetryEvent) -> None:
        """Store event in memory."""
        self.events.append(event)

    def clear(self) -> None:
        """Clear all collected events."""
        self.events.clear()

    def get_events_by_type(self, event_type: EventType) -> list[TelemetryEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_component(self, component: str) -> list[TelemetryEvent]:
        """Get all events from a specific component."""
        return [e for e in self.events if e.component == component]


class LatencyTracker:
    """
    Context manager for tracking operation latency.
    
    Usage:
        with LatencyTracker(collector, "ASR"):
            # ... operation ...
            pass
    """

    def __init__(
        self,
        collector: TelemetryCollector,
        component: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize latency tracker.
        
        Args:
            collector: TelemetryCollector instance
            component: Component name
            session_id: Optional session ID
            context: Additional context
        """
        self.collector = collector
        self.component = component
        self.session_id = session_id
        self.context = context or {}
        self.start_time: Optional[float] = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record event."""
        if self.start_time is not None:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            self.collector.record_latency(
                self.component,
                duration_ms,
                self.session_id,
                self.context,
            )
        return False  # Don't suppress exceptions

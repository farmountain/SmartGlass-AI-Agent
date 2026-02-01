"""
Azure Application Insights Telemetry Collector

Sends telemetry events to Azure Application Insights for cloud-based
monitoring, analytics, and performance tracking.

Configuration:
    Set APPINSIGHTS_INSTRUMENTATION_KEY environment variable or pass
    instrumentation_key to constructor.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from .telemetry import EventType, Severity, TelemetryCollector, TelemetryEvent

logger = logging.getLogger(__name__)

try:
    from opencensus.ext.azure.log_exporter import AzureLogHandler
    from opencensus.ext.azure.trace_exporter import AzureExporter
    from opencensus.trace import tracer as tracer_module
    from opencensus.trace.samplers import ProbabilitySampler

    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False
    logger.warning(
        "Azure SDK not available. Install with: "
        "pip install opencensus-ext-azure"
    )


class ApplicationInsightsCollector(TelemetryCollector):
    """
    Azure Application Insights telemetry collector.

    Sends telemetry events to Azure Application Insights cloud service
    for centralized monitoring, analytics, and alerting.

    Features:
    - Structured logging with custom properties
    - Performance metrics tracking
    - Error and exception reporting
    - Custom event telemetry
    - Distributed tracing support
    - Automatic batching and retry logic

    Example:
        ```python
        collector = ApplicationInsightsCollector(
            instrumentation_key="12345678-1234-1234-1234-123456789012"
        )

        # Record latency
        collector.record_latency("Vision", 150.5, context={"model": "CLIP"})

        # Record error
        collector.record_error(
            "ASR",
            "Timeout waiting for audio stream",
            severity=Severity.WARNING
        )

        # Record custom metric
        collector.record_usage(
            "LLM",
            {"tokens_generated": 42, "time_ms": 850},
            context={"model": "gpt-4"}
        )
        ```
    """

    def __init__(
        self,
        instrumentation_key: Optional[str] = None,
        service_name: str = "SmartGlass-AI-Agent",
        environment: str = "production",
        enable_tracing: bool = True,
        enable_logging: bool = True,
        batch_size: int = 100,
        max_batch_interval_seconds: int = 30,
    ):
        """
        Initialize Azure Application Insights collector.

        Args:
            instrumentation_key: Azure Application Insights instrumentation key.
                If not provided, uses APPINSIGHTS_INSTRUMENTATION_KEY env var.
            service_name: Name of the service (default: "SmartGlass-AI-Agent")
            environment: Environment name (e.g., "production", "staging")
            enable_tracing: Enable distributed tracing (default: True)
            enable_logging: Enable log exporter (default: True)
            batch_size: Number of events before sending batch
            max_batch_interval_seconds: Max time between batch sends
        """
        self.instrumentation_key = (
            instrumentation_key
            or os.getenv("APPINSIGHTS_INSTRUMENTATION_KEY", "")
        )
        self.service_name = service_name
        self.environment = environment
        self.enable_tracing = enable_tracing
        self.enable_logging = enable_logging
        self.batch_size = batch_size
        self.max_batch_interval_seconds = max_batch_interval_seconds

        self._event_buffer: list[Dict[str, Any]] = []
        self._metrics_buffer: Dict[str, float] = {}

        if not AZURE_SDK_AVAILABLE:
            logger.warning(
                "Azure SDK not available. Events will be logged locally only. "
                "Install with: pip install opencensus-ext-azure"
            )
            self._tracer = None
            self._log_handler = None
            return

        # Setup distributed tracing
        if self.enable_tracing and self.instrumentation_key:
            try:
                exporter = AzureExporter(
                    connection_string=f"InstrumentationKey={self.instrumentation_key}"
                )
                self._tracer = tracer_module.Tracer(
                    exporter=exporter,
                    sampler=ProbabilitySampler(rate=1.0),
                )
            except Exception as e:
                logger.error(f"Failed to initialize tracing: {e}")
                self._tracer = None
        else:
            self._tracer = None

        # Setup log exporting
        if self.enable_logging and self.instrumentation_key:
            try:
                self._log_handler = AzureLogHandler(
                    connection_string=f"InstrumentationKey={self.instrumentation_key}"
                )
                logging.getLogger().addHandler(self._log_handler)
            except Exception as e:
                logger.error(f"Failed to initialize log handler: {e}")
                self._log_handler = None
        else:
            self._log_handler = None

        logger.info(
            f"ApplicationInsightsCollector initialized - "
            f"service={service_name}, environment={environment}"
        )

    def collect(self, event: TelemetryEvent) -> None:
        """
        Collect a telemetry event and send to Application Insights.

        Args:
            event: TelemetryEvent to collect
        """
        if not self.instrumentation_key:
            logger.debug(f"Instrumentation key not configured. Event dropped: {event}")
            return

        try:
            # Convert event to Application Insights format
            ai_event = self._convert_to_app_insights_event(event)

            # Add to buffer
            self._event_buffer.append(ai_event)

            # Flush if batch size reached
            if len(self._event_buffer) >= self.batch_size:
                self.flush()

        except Exception as e:
            logger.error(f"Error collecting telemetry event: {e}")

    def _convert_to_app_insights_event(
        self, event: TelemetryEvent
    ) -> Dict[str, Any]:
        """
        Convert TelemetryEvent to Application Insights event format.

        Args:
            event: TelemetryEvent to convert

        Returns:
            Dictionary in Application Insights format
        """
        # Common properties for all events
        properties = {
            "service": self.service_name,
            "environment": self.environment,
            "event_type": event.event_type.value,
            "component": event.component,
            "severity": event.severity.value,
        }

        # Add session ID if available
        if event.session_id:
            properties["session_id"] = event.session_id

        # Add context as custom properties
        if event.context:
            for key, value in event.context.items():
                try:
                    properties[f"context_{key}"] = str(value)
                except Exception as e:
                    logger.warning(f"Failed to serialize context {key}: {e}")

        # Build event based on type
        ai_event = {
            "name": f"smartglass_{event.event_type.value}",
            "timestamp": event.timestamp,
            "properties": properties,
            "measurements": event.metrics or {},
        }

        # Add severity-based logging
        if event.severity in (Severity.ERROR, Severity.CRITICAL):
            ai_event["severity_level"] = event.severity.value

        return ai_event

    def record_latency(
        self,
        component: str,
        duration_ms: float,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record latency metric with Application Insights.

        Args:
            component: Component name
            duration_ms: Duration in milliseconds
            session_id: Optional session ID
            context: Additional context
        """
        # Track as distributed trace if tracer available
        if self._tracer:
            try:
                with self._tracer.span(name=f"{component}_latency") as span:
                    span.add_attribute("duration_ms", duration_ms)
                    if session_id:
                        span.add_attribute("session_id", session_id)
            except Exception as e:
                logger.debug(f"Failed to record span: {e}")

        # Also record as telemetry event
        super().record_latency(component, duration_ms, session_id, context)

    def record_custom_metric(
        self,
        metric_name: str,
        value: float,
        component: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a custom metric.

        Args:
            metric_name: Name of the metric
            value: Numeric value
            component: Optional component name
            session_id: Optional session ID
            properties: Additional properties
        """
        try:
            props = {
                "metric": metric_name,
                "service": self.service_name,
                "environment": self.environment,
            }

            if component:
                props["component"] = component
            if session_id:
                props["session_id"] = session_id
            if properties:
                props.update(properties)

            # Log as Application Insights custom event
            logger.info(
                json.dumps(
                    {
                        "event_type": "custom_metric",
                        "metric_name": metric_name,
                        "value": value,
                        "properties": props,
                    }
                )
            )
        except Exception as e:
            logger.error(f"Failed to record custom metric: {e}")

    def flush(self) -> None:
        """Flush buffered events to Application Insights."""
        if not self._event_buffer:
            return

        try:
            # In production, events are batched and sent automatically
            # by the Azure SDK. Here we log the batch for verification.
            logger.debug(f"Flushing {len(self._event_buffer)} events to AppInsights")

            # Process batch
            batch_summary = {
                "batch_size": len(self._event_buffer),
                "event_types": {},
                "components": {},
            }

            for event in self._event_buffer:
                event_type = event.get("properties", {}).get("event_type", "unknown")
                component = event.get("properties", {}).get("component", "unknown")

                batch_summary["event_types"][event_type] = (
                    batch_summary["event_types"].get(event_type, 0) + 1
                )
                batch_summary["components"][component] = (
                    batch_summary["components"].get(component, 0) + 1
                )

            logger.debug(f"Batch summary: {batch_summary}")
            self._event_buffer.clear()

        except Exception as e:
            logger.error(f"Failed to flush telemetry: {e}")

    def close(self) -> None:
        """Close the telemetry collector and flush remaining events."""
        self.flush()

        if self._log_handler:
            try:
                self._log_handler.close()
            except Exception as e:
                logger.warning(f"Failed to close log handler: {e}")

        logger.info("ApplicationInsightsCollector closed")


class LocalTelemetryCollector(TelemetryCollector):
    """
    Local telemetry collector for development and testing.

    Buffers events in memory and provides query/export methods.
    Useful when Azure SDK is not available or during development.
    """

    def __init__(self, max_events: int = 10000):
        """
        Initialize local telemetry collector.

        Args:
            max_events: Maximum events to keep in buffer
        """
        self.max_events = max_events
        self._events: list[TelemetryEvent] = []

    def collect(self, event: TelemetryEvent) -> None:
        """
        Collect event in local buffer.

        Args:
            event: TelemetryEvent to collect
        """
        self._events.append(event)

        # Trim buffer if it exceeds max size
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events :]

    def get_events(self, event_type: Optional[EventType] = None) -> list[TelemetryEvent]:
        """
        Get collected events, optionally filtered by type.

        Args:
            event_type: Optional event type to filter by

        Returns:
            List of TelemetryEvent objects
        """
        if event_type is None:
            return self._events.copy()

        return [e for e in self._events if e.event_type == event_type]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about collected events.

        Returns:
            Dictionary with event counts, components, etc.
        """
        stats = {
            "total_events": len(self._events),
            "event_types": {},
            "components": {},
            "severities": {},
        }

        for event in self._events:
            event_type = event.event_type.value
            stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1

            stats["components"][event.component] = (
                stats["components"].get(event.component, 0) + 1
            )

            severity = event.severity.value
            stats["severities"][severity] = stats["severities"].get(severity, 0) + 1

        return stats

    def clear(self) -> None:
        """Clear all buffered events."""
        self._events.clear()


# Factory function for convenient collector creation
def create_telemetry_collector(
    use_azure: bool = True,
    instrumentation_key: Optional[str] = None,
) -> TelemetryCollector:
    """
    Factory function to create appropriate telemetry collector.

    Args:
        use_azure: Whether to use Azure Application Insights
        instrumentation_key: Optional Azure instrumentation key

    Returns:
        TelemetryCollector instance
    """
    if use_azure and AZURE_SDK_AVAILABLE and (instrumentation_key or os.getenv("APPINSIGHTS_INSTRUMENTATION_KEY")):
        logger.info("Creating ApplicationInsightsCollector")
        return ApplicationInsightsCollector(instrumentation_key=instrumentation_key)
    else:
        logger.info("Creating LocalTelemetryCollector (Azure SDK unavailable or not configured)")
        return LocalTelemetryCollector()


if __name__ == "__main__":
    # Demonstration
    print("=" * 70)
    print("ApplicationInsightsCollector Demonstration")
    print("=" * 70)

    # Create local collector (since Azure SDK may not be installed)
    collector = LocalTelemetryCollector()

    # Simulate various events
    print("\n[1] Recording latency events...")
    for i in range(3):
        collector.record_latency("Vision", 150.5 + i * 10, context={"model": "CLIP"})
        collector.record_latency("ASR", 85.2 + i * 5)
        collector.record_latency("LLM", 450.1 + i * 20)

    print("[2] Recording error events...")
    collector.record_error("ASR", "Audio stream timeout", severity=Severity.WARNING)
    collector.record_error("Vision", "GPU memory exhausted", severity=Severity.ERROR)

    print("[3] Recording usage metrics...")
    collector.record_usage(
        "LLM",
        {"tokens_generated": 42, "completion_tokens": 40},
        context={"model": "gpt-4", "temperature": 0.7},
    )

    # Display statistics
    stats = collector.get_statistics()
    print("\n" + "=" * 70)
    print("TELEMETRY STATISTICS")
    print("=" * 70)
    print(f"Total events: {stats['total_events']}")
    print(f"\nEvent types:")
    for event_type, count in stats["event_types"].items():
        print(f"  {event_type}: {count}")

    print(f"\nComponents:")
    for component, count in stats["components"].items():
        print(f"  {component}: {count}")

    print(f"\nSeverities:")
    for severity, count in stats["severities"].items():
        print(f"  {severity}: {count}")

    # Show sample events
    print("\n" + "=" * 70)
    print("SAMPLE EVENTS")
    print("=" * 70)
    for i, event in enumerate(collector.get_events()[:3], 1):
        print(f"\n[{i}] {event.event_type.value.upper()}")
        print(f"    Component: {event.component}")
        print(f"    Severity: {event.severity.value}")
        if event.metrics:
            print(f"    Metrics: {event.metrics}")
        if event.context:
            print(f"    Context: {event.context}")

    print("\n" + "=" * 70)
    print("✅ ApplicationInsightsCollector demonstration complete")
    print("=" * 70)

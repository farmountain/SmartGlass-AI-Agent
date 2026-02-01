# Azure Application Insights Telemetry Collector

## Overview

The `ApplicationInsightsCollector` provides production-ready telemetry collection to Azure Application Insights, enabling centralized monitoring, analytics, and alerting for the SmartGlass AI Agent.

## Features

- ✅ Structured logging with custom properties
- ✅ Performance metrics tracking (latency, throughput)
- ✅ Error and exception reporting with severity levels
- ✅ Custom event telemetry with flexible properties
- ✅ Distributed tracing support (requires Azure SDK)
- ✅ Automatic batching and retry logic
- ✅ Fallback to local collection when Azure SDK unavailable
- ✅ Thread-safe event buffering

## Installation

### Basic Installation
```bash
pip install opencensus-ext-azure
```

### Full Setup for Azure Integration
```bash
pip install opencensus-ext-azure opencensus-ext-logging
```

## Configuration

### Using Environment Variable
```bash
export APPINSIGHTS_INSTRUMENTATION_KEY="YOUR_INSTRUMENTATION_KEY"
```

### Programmatic Configuration
```python
from src.application_insights_collector import ApplicationInsightsCollector

collector = ApplicationInsightsCollector(
    instrumentation_key="12345678-1234-1234-1234-123456789012",
    service_name="SmartGlass-AI-Agent",
    environment="production"
)
```

## Usage Examples

### Recording Latency Metrics

```python
# Record component latency
collector.record_latency(
    component="Vision",
    duration_ms=150.5,
    session_id="session_001",
    context={"model": "CLIP", "batch_size": 8}
)

# Multiple components
collector.record_latency("ASR", 85.2)
collector.record_latency("LLM", 450.1)
collector.record_latency("Planner", 12.3)
```

### Recording Errors

```python
# Warning-level error
collector.record_error(
    component="ASR",
    error_message="Audio stream timeout after 30s",
    severity=Severity.WARNING,
    session_id="session_001"
)

# Critical error
collector.record_error(
    component="Vision",
    error_message="GPU memory exhausted",
    severity=Severity.CRITICAL,
    context={"available_memory_mb": 0, "required_mb": 2048}
)
```

### Recording Usage Metrics

```python
# LLM token usage
collector.record_usage(
    component="LLM",
    metrics={
        "tokens_generated": 42,
        "completion_tokens": 40,
        "time_ms": 850
    },
    session_id="session_001",
    context={"model": "gpt-4", "temperature": 0.7}
)

# Memory and resource usage
collector.record_usage(
    component="System",
    metrics={
        "memory_usage_mb": 512,
        "gpu_memory_mb": 2048,
        "battery_percent": 75
    }
)
```

### Recording Safety Events

```python
# Content passed safety check
collector.record_safety_event(
    component="ContentFilter",
    blocked=False,
    reason="Content approved",
    context={
        "check_type": "violence_filter",
        "confidence": 0.98
    }
)

# Content blocked
collector.record_safety_event(
    component="ContentFilter",
    blocked=True,
    reason="Potentially dangerous medical advice",
    severity=Severity.WARNING,
    context={"category": "medical", "confidence": 0.92}
)
```

### Custom Metrics

```python
collector.record_custom_metric(
    metric_name="intent_accuracy",
    value=0.95,
    component="CLIPWorldModel",
    properties={
        "intent_type": "navigate",
        "model": "CLIP-ViT-B/32"
    }
)
```

## Integration with SmartGlassAgent

### Factory Pattern

```python
from src.application_insights_collector import create_telemetry_collector

# Automatically selects Azure or local based on availability
collector = create_telemetry_collector(use_azure=True)
```

### Complete Integration Example

```python
from src.smartglass_agent import SmartGlassAgent
from src.application_insights_collector import ApplicationInsightsCollector

# Initialize telemetry
telemetry = ApplicationInsightsCollector(
    service_name="SmartGlass-AI-Agent",
    environment="production"
)

# Initialize agent with telemetry
agent = SmartGlassAgent(
    telemetry_collector=telemetry,
    # ... other config
)

# Telemetry is automatically recorded during request processing
response = agent.process_request(
    audio_input=audio_data,
    visual_input=image_data,
    session_id="user_123"
)

# Manually flush remaining events
telemetry.flush()
telemetry.close()
```

## Azure Application Insights Queries

### Query: Average Latency by Component
```kusto
customEvents
| where name == "smartglass_latency"
| extend component = tostring(customDimensions.component)
| extend duration_ms = todouble(customMeasurements.duration_ms)
| summarize avg_latency=avg(duration_ms), p95_latency=percentile(duration_ms, 95) by component
| order by avg_latency desc
```

### Query: Error Rate by Component
```kusto
customEvents
| where name == "smartglass_error"
| extend component = tostring(customDimensions.component)
| summarize error_count=count(), total_events=count() by component
| extend error_rate = error_count * 100.0 / total_events
| order by error_rate desc
```

### Query: E2E Latency Distribution
```kusto
customEvents
| where name == "smartglass_latency" and customDimensions.component == "E2E"
| extend latency_ms = todouble(customMeasurements.duration_ms)
| summarize
    count=count(),
    avg_latency=avg(latency_ms),
    p50_latency=percentile(latency_ms, 50),
    p95_latency=percentile(latency_ms, 95),
    p99_latency=percentile(latency_ms, 99),
    max_latency=max(latency_ms)
```

### Query: Safety Events Timeline
```kusto
customEvents
| where name == "smartglass_safety"
| extend blocked = tostring(customDimensions.context_blocked)
| extend reason = tostring(customDimensions.context_reason)
| where blocked == "True"
| summarize block_count=count() by bin(timestamp, 1h)
| order by timestamp desc
```

## Performance Characteristics

- **Event Collection**: <0.1ms per event
- **Batch Flush**: 0-50ms depending on network (async in Azure SDK)
- **Memory Overhead**: ~1KB per event in buffer
- **Default Batch Size**: 100 events (configurable)
- **Max Batch Interval**: 30 seconds

## Best Practices

### 1. Use Session IDs for Correlation
```python
import uuid

session_id = str(uuid.uuid4())

collector.record_latency("Vision", 150.0, session_id=session_id)
collector.record_latency("ASR", 85.0, session_id=session_id)
collector.record_latency("LLM", 450.0, session_id=session_id)
# All events linked in Azure by session_id
```

### 2. Include Context for Debugging
```python
collector.record_error(
    "Vision",
    "Image processing failed",
    context={
        "image_size": "1920x1080",
        "model": "CLIP",
        "batch_size": 8,
        "error_code": 503
    }
)
```

### 3. Batch Related Events
```python
# Record E2E workflow as multiple component events
start_time = time.time()

vision_time = process_vision(image)
collector.record_latency("Vision", vision_time)

asr_time = process_asr(audio)
collector.record_latency("ASR", asr_time)

llm_time = process_llm(text)
collector.record_latency("LLM", llm_time)

# Flush to ensure batch is sent
collector.flush()
```

### 4. Environment-Specific Configuration
```python
import os

env = os.getenv("ENVIRONMENT", "development")
collector = ApplicationInsightsCollector(
    service_name="SmartGlass-AI-Agent",
    environment=env,
    # Batch more aggressively in production
    batch_size=100 if env == "production" else 10,
    max_batch_interval_seconds=30 if env == "production" else 5
)
```

### 5. Error Handling
```python
from src.application_insights_collector import LocalTelemetryCollector

try:
    collector = ApplicationInsightsCollector()
except Exception as e:
    # Fallback to local collection
    logger.warning(f"Failed to init Azure telemetry: {e}")
    collector = LocalTelemetryCollector()
```

## Troubleshooting

### "Azure SDK not available"
```bash
pip install opencensus-ext-azure
```

### "Invalid instrumentation key"
```bash
# Verify key format (GUID)
export APPINSIGHTS_INSTRUMENTATION_KEY="12345678-1234-1234-1234-123456789012"
```

### Events not appearing in Azure
- Verify instrumentation key is correct
- Check network connectivity to Azure
- Review Application Insights pricing tier (free tier may have limits)
- Use LocalTelemetryCollector for testing/debugging

### High latency with event collection
- Increase batch_size for less frequent network calls
- Use async collection with LocalTelemetryCollector
- Check network latency to Azure endpoints

## Testing

Run the test script:
```bash
python test_application_insights.py
```

Expected output:
```
======================================================================
ApplicationInsightsCollector Test
======================================================================
[1/4] Recording latency events...
[2/4] Recording error events...
[3/4] Recording usage metrics...
[4/4] Recording safety events...

TELEMETRY STATISTICS
Total events: 13
Event types: latency(9), error(2), usage(1), safety(1)
...
✅ ALL TESTS PASSED
```

## References

- [Azure Application Insights Documentation](https://docs.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
- [OpenCensus Azure Exporter](https://github.com/census-instrumentation/opencensus-python/tree/master/contrib/opencensus-ext-azure)
- [Application Insights API Reference](https://docs.microsoft.com/en-us/azure/azure-monitor/app/api-custom-events-metrics)

---

**Status**: ✅ Production Ready
**Version**: 1.0
**Last Updated**: February 2026

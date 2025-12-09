# DAT-Aware Metrics & Observability

This document describes the metrics system for monitoring DAT (Device Access Toolkit) deployments of SmartGlass-AI-Agent, including Ray-Ban Meta glasses integrations.

## Overview

The SmartGlass backend exposes two metrics endpoints:
1. **`/metrics`** - Full Prometheus-compatible metrics with all latency data
2. **`/metrics/summary`** - Compact JSON summary optimized for mobile clients

## Metrics Endpoints

### `/metrics` - Full Metrics

Returns comprehensive metrics including all latency measurements, session counts, and system state.

**Example Response:**
```json
{
  "latencies": {
    "dat_ingest_audio_latency_ms": {
      "count": 42,
      "total": 0.645,
      "avg": 0.0154,
      "min": 0.008,
      "max": 0.032
    },
    "dat_ingest_frame_latency_ms": {
      "count": 38,
      "total": 0.862,
      "avg": 0.0227,
      "min": 0.015,
      "max": 0.045
    },
    "end_to_end_turn_latency_ms": {
      "count": 12,
      "total": 10.205,
      "avg": 0.8504,
      "min": 0.720,
      "max": 1.204
    },
    "all": {
      "count": 92,
      "total": 11.712,
      "avg": 0.127,
      "min": 0.008,
      "max": 1.204
    }
  },
  "sessions": {
    "created": 12,
    "active": 3
  },
  "queries": {
    "total": 45
  }
}
```

### `/metrics/summary` - Compact Summary

Returns a lightweight JSON response designed for Android/iOS apps and operator dashboards.

**Example Response:**
```json
{
  "health": "ok",
  "dat_metrics": {
    "ingest_audio": {
      "count": 42,
      "avg_ms": 15.4,
      "max_ms": 32.1
    },
    "ingest_frame": {
      "count": 38,
      "avg_ms": 22.7,
      "max_ms": 45.2
    },
    "end_to_end_turn": {
      "count": 12,
      "avg_ms": 850.4,
      "max_ms": 1203.5
    }
  },
  "summary": {
    "total_sessions": 12,
    "active_sessions": 3,
    "total_queries": 45
  }
}
```

## DAT-Specific Metrics

### `dat_ingest_audio_latency_ms`

Tracks the time to ingest and process audio chunks from the DAT stream endpoint.

**What it measures:**
- Base64 decoding of audio payload
- Audio format conversion (PCM, Opus, etc.)
- Buffering in the DAT registry

**Typical values:**
- Good: < 50ms
- Acceptable: 50-100ms
- Degraded: > 100ms

### `dat_ingest_frame_latency_ms`

Tracks the time to ingest and process video frames from the DAT stream endpoint.

**What it measures:**
- Base64 decoding of image payload
- JPEG/PNG decoding
- Image array conversion
- Buffering in the DAT registry

**Typical values:**
- Good: < 50ms
- Acceptable: 50-100ms
- Degraded: > 100ms

### `end_to_end_turn_latency_ms`

Tracks the complete turn processing latency from request to response.

**What it measures:**
- Retrieving buffered audio/frames from DAT registry
- Speech-to-text transcription (Whisper)
- Image analysis (CLIP/DeepSeek-Vision)
- LLM inference (Llama/Qwen)
- Action parsing and response formatting

**Typical values:**
- Good: < 1000ms (1 second)
- Acceptable: 1000-2000ms
- Degraded: > 2000ms

## Health States

The `/metrics/summary` endpoint includes a `health` field with the following states:

| State | Description | Conditions |
|-------|-------------|------------|
| `ok` | All systems operating normally | All latencies within acceptable thresholds |
| `degraded` | System functional but slow | One or more latencies exceed thresholds |

**Health Thresholds:**
- Audio/Frame ingestion: 100ms average
- End-to-end turn: 2000ms average

## Android SDK Usage

The Android SDK provides convenient methods to retrieve and log metrics:

### Get Metrics Summary

```kotlin
import com.smartglass.sdk.SmartGlassClient
import com.smartglass.sdk.MetricsSummary

val client = SmartGlassClient(baseUrl = "http://10.0.2.2:8000")

// Fetch metrics
val metrics = client.getMetricsSummary()

// Check health
when (metrics.health) {
    "ok" -> println("System healthy")
    "degraded" -> println("System degraded: ${metrics.datMetrics}")
}

// Display specific metrics
println("Audio ingestion: ${metrics.datMetrics.ingestAudio.avgMs}ms avg")
println("Frame ingestion: ${metrics.datMetrics.ingestFrame.avgMs}ms avg")
println("E2E turn: ${metrics.datMetrics.endToEndTurn.avgMs}ms avg")
```

### Log Metrics Summary

For debugging, use the built-in logging helper:

```kotlin
// Logs a one-line summary via Log.d()
client.logMetricsSummary()

// Output:
// D/SmartGlassMetrics: Health: ok | Sessions: 3/12 | Audio: 15.4ms | Frame: 22.7ms | E2E: 850.4ms
```

### Custom Log Tag

```kotlin
client.logMetricsSummary(tag = "MyApp")
```

## Operator Guidelines

### Monitoring Dashboard

Recommended polling intervals:
- **Production**: 30-60 seconds
- **Development**: 5-10 seconds
- **Load Testing**: 1-5 seconds

### Alert Thresholds

Configure alerts based on your deployment requirements:

**Critical Alerts:**
- `health == "degraded"` for > 5 minutes
- `end_to_end_turn.avg_ms > 3000` (3 seconds)
- `active_sessions > capacity_limit`

**Warning Alerts:**
- `ingest_audio.avg_ms > 100`
- `ingest_frame.avg_ms > 100`
- `end_to_end_turn.avg_ms > 2000`

### Performance Optimization

If you observe degraded performance:

1. **High audio ingestion latency:**
   - Check CPU usage on the backend
   - Verify audio format is PCM (avoids extra decoding)
   - Consider increasing backend worker threads

2. **High frame ingestion latency:**
   - Reduce frame resolution from Android app
   - Increase keyframe interval (send fewer frames)
   - Check network bandwidth

3. **High end-to-end turn latency:**
   - Profile the agent pipeline (Whisper, CLIP, LLM)
   - Consider GPU acceleration for models
   - Optimize prompt templates for faster LLM responses
   - Enable model caching/quantization

## Integration with Existing Monitoring

### Prometheus

The full `/metrics` endpoint can be scraped by Prometheus:

```yaml
scrape_configs:
  - job_name: 'smartglass'
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana

Example queries for Grafana dashboards:

- **Audio Ingestion Avg:** `smartglass_dat_ingest_audio_latency_ms_avg`
- **Frame Ingestion Avg:** `smartglass_dat_ingest_frame_latency_ms_avg`
- **E2E Turn Avg:** `smartglass_end_to_end_turn_latency_ms_avg`

## Benchmark Scripts

The repository includes benchmark scripts that write latency CSVs:

- `bench/audio_bench.py` - Audio processing benchmarks
- `bench/image_bench.py` - Image processing benchmarks

These scripts use the metrics system internally and can be used for performance regression testing.

## Best Practices

1. **Baseline Metrics:** Establish baseline metrics during initial deployment
2. **Regular Monitoring:** Poll `/metrics/summary` regularly from your Android app during development
3. **Load Testing:** Use benchmark scripts to simulate production load
4. **Alerting:** Set up alerts for degraded health state
5. **Optimization:** Use per-phase latencies to identify bottlenecks

## Future Enhancements

Planned improvements to the metrics system:

- [ ] Percentile metrics (p50, p95, p99)
- [ ] Per-model latency tracking (Whisper, CLIP, LLM separately)
- [ ] Network latency vs. processing latency breakdown
- [ ] Memory usage metrics
- [ ] GPU utilization metrics (if GPU available)
- [ ] Per-session metrics (track individual session performance)

## Support

For issues or questions about metrics:
- File an issue at: https://github.com/farmountain/SmartGlass-AI-Agent/issues
- Include example metrics output
- Specify deployment environment (edge device, cloud, etc.)

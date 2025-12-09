"""Thread-safe metrics helpers for runtime instrumentation."""

from __future__ import annotations

import threading
import time
from contextlib import ContextDecorator
from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class RollingStats:
    """Rolling statistics for latency measurements."""

    count: int = 0
    total: float = 0.0
    minimum: float = float("inf")
    maximum: float = 0.0

    def add(self, duration: float) -> None:
        self.count += 1
        self.total += duration
        self.minimum = min(self.minimum, duration)
        self.maximum = max(self.maximum, duration)

    def snapshot(self) -> Dict[str, float]:
        if self.count == 0:
            return {"count": 0, "total": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}

        return {
            "count": self.count,
            "total": self.total,
            "avg": self.total / self.count,
            "min": self.minimum,
            "max": self.maximum,
        }


class _LatencyRecorder(ContextDecorator):
    def __init__(self, registry: "MetricsRegistry", tag: str):
        self._registry = registry
        self._tag = tag
        self._start: Optional[float] = None

    def __enter__(self):  # type: ignore[override]
        self._start = self._registry._time_fn()  # pylint: disable=protected-access
        return self

    def __exit__(self, exc_type, exc, exc_tb):  # type: ignore[override]
        end = self._registry._time_fn()  # pylint: disable=protected-access
        if self._start is not None:
            self._registry._add_duration(self._tag, end - self._start)  # pylint: disable=protected-access
        return False


class MetricsRegistry:
    """Tracks latency measurements and lifecycle counters."""

    def __init__(self, *, time_fn: Callable[[], float] | None = None):
        self._time_fn = time_fn or time.perf_counter
        self._lock = threading.RLock()
        self._latencies: Dict[str, RollingStats] = {}
        self._sessions_created = 0
        self._sessions_active = 0
        self._queries = 0

    def record_latency(self, tag: str) -> _LatencyRecorder:
        """Return a context manager/decorator recording latency under ``tag``."""

        return _LatencyRecorder(self, tag)

    def _add_duration(self, tag: str, duration: float) -> None:
        with self._lock:
            stage_stats = self._latencies.setdefault(tag, RollingStats())
            stage_stats.add(duration)
            aggregate = self._latencies.setdefault("all", RollingStats())
            aggregate.add(duration)

    def increment_sessions(self) -> None:
        with self._lock:
            self._sessions_created += 1
            self._sessions_active += 1

    def decrement_sessions(self) -> None:
        with self._lock:
            self._sessions_active = max(0, self._sessions_active - 1)

    def increment_queries(self) -> None:
        with self._lock:
            self._queries += 1

    def snapshot(self, *, display_available: bool | None = None) -> Dict[str, object]:
        with self._lock:
            latencies = {tag: stats.snapshot() for tag, stats in self._latencies.items()}
            data: Dict[str, object] = {
                "latencies": latencies,
                "sessions": {
                    "created": self._sessions_created,
                    "active": self._sessions_active,
                },
                "queries": {"total": self._queries},
            }
            if display_available is not None:
                data["display_available"] = bool(display_available)
            return data

    def reset(self) -> None:
        """Reset all collected statistics (primarily for tests)."""

        with self._lock:
            self._latencies.clear()
            self._sessions_created = 0
            self._sessions_active = 0
            self._queries = 0


def record_latency(tag: str) -> _LatencyRecorder:
    return metrics.record_latency(tag)


def get_metrics_snapshot(*, display_available: bool | None = None) -> Dict[str, object]:
    return metrics.snapshot(display_available=display_available)


def get_metrics_summary() -> Dict[str, object]:
    """Return a compact metrics summary with health state for mobile clients.
    
    This endpoint provides a simplified view of system health suitable for
    Android/iOS applications and operator dashboards. It includes:
    - DAT-specific latency metrics (audio/frame ingestion, end-to-end turns)
    - Overall health state based on latency thresholds
    - Key statistics (avg, max latency)
    
    Health states:
    - "ok": All latencies within acceptable thresholds
    - "degraded": Some latencies exceed thresholds but system is functional
    
    Returns:
        Dict with keys: health, dat_metrics, summary
    """
    snapshot = metrics.snapshot()
    latencies = snapshot.get("latencies", {})
    
    # Extract DAT-specific metrics
    dat_audio = latencies.get("dat_ingest_audio_latency_ms", {})
    dat_frame = latencies.get("dat_ingest_frame_latency_ms", {})
    dat_e2e = latencies.get("end_to_end_turn_latency_ms", {})
    
    # Convert seconds to milliseconds for display
    def _to_ms(stats: Dict[str, float]) -> Dict[str, float]:
        return {
            "count": stats.get("count", 0),
            "avg_ms": stats.get("avg", 0.0) * 1000,
            "max_ms": stats.get("max", 0.0) * 1000,
        }
    
    # Determine health state based on thresholds
    # Thresholds: audio/frame <100ms, e2e turn <2000ms
    health = "ok"
    
    if dat_audio.get("avg", 0.0) > 0.1:  # 100ms
        health = "degraded"
    if dat_frame.get("avg", 0.0) > 0.1:  # 100ms
        health = "degraded"
    if dat_e2e.get("avg", 0.0) > 2.0:  # 2000ms
        health = "degraded"
    
    return {
        "health": health,
        "dat_metrics": {
            "ingest_audio": _to_ms(dat_audio),
            "ingest_frame": _to_ms(dat_frame),
            "end_to_end_turn": _to_ms(dat_e2e),
        },
        "summary": {
            "total_sessions": snapshot.get("sessions", {}).get("created", 0),
            "active_sessions": snapshot.get("sessions", {}).get("active", 0),
            "total_queries": snapshot.get("queries", {}).get("total", 0),
        },
    }


metrics = MetricsRegistry()

__all__ = [
    "metrics",
    "record_latency",
    "get_metrics_snapshot",
    "get_metrics_summary",
    "MetricsRegistry",
    "RollingStats",
]

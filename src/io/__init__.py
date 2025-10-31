"""I/O utilities for SmartGlass AI."""

from .telemetry import MetricTimer, log_metric, metric_timer
from .tts import CHARS_PER_SECOND, TTSResult, speak

__all__ = [
    "MetricTimer",
    "log_metric",
    "metric_timer",
    "CHARS_PER_SECOND",
    "TTSResult",
    "speak",
]

"""Stub text-to-speech utilities for deterministic testing."""

from __future__ import annotations

from dataclasses import dataclass

from .telemetry import log_metric

__all__ = ["CHARS_PER_SECOND", "TTSResult", "speak"]

CHARS_PER_SECOND = 14.0


@dataclass(frozen=True)
class TTSResult:
    """Container describing the synthetic speech output."""

    char_count: int
    duration: float
    sample_rate: int
    sample_count: int


def speak(text: str, *, sample_rate: int = 22050) -> TTSResult:
    """Synthesize speech deterministically without producing audio samples."""

    char_count = len(text)
    if char_count == 0:
        duration = 0.0
    else:
        duration = char_count / CHARS_PER_SECOND

    sample_count = int(round(duration * sample_rate))

    log_metric("tts.char_count", char_count, unit="chars")
    log_metric("tts.ms", duration * 1000.0, unit="ms")

    return TTSResult(
        char_count=char_count,
        duration=duration,
        sample_rate=sample_rate,
        sample_count=sample_count,
    )

"""Deterministic mock implementations of the driver interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
from typing import Iterable, List, Sequence, Tuple

from ..interfaces import (
    AudioOut,
    CameraIn,
    DisplayOverlay,
    Frame,
    Haptics,
    MicIn,
    Permissions,
)


_BASE_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)


class MockCameraIn(CameraIn):
    """Return synthetic greyscale frames that step through a simple gradient."""

    def __init__(self) -> None:
        self._frame_index = 0

    def get_frame(self) -> Tuple[datetime, Frame]:
        timestamp = _BASE_TIME + timedelta(milliseconds=100 * self._frame_index)
        size = 4
        frame: Frame = [
            [((row * size) + col + self._frame_index) % 256 for col in range(size)]
            for row in range(size)
        ]
        self._frame_index += 1
        return timestamp, frame


class MockMicIn(MicIn):
    """Produce a repeatable single-channel audio waveform."""

    def __init__(self, sample_rate_hz: int = 16000, chunk_size: int = 160) -> None:
        self._sample_rate_hz = sample_rate_hz
        self._chunk_size = chunk_size
        self._chunk_index = 0

    def get_audio_chunk(self) -> Tuple[datetime, List[float]]:
        offset_seconds = (self._chunk_size * self._chunk_index) / float(self._sample_rate_hz)
        timestamp = _BASE_TIME + timedelta(seconds=offset_seconds)
        phase_offset = self._chunk_index * self._chunk_size
        samples = [
            round(math.sin((phase_offset + i) / 40.0), 6)
            for i in range(self._chunk_size)
        ]
        self._chunk_index += 1
        return timestamp, samples


class MockAudioOut(AudioOut):
    """Record the playback history and report deterministic durations."""

    def __init__(self) -> None:
        self.history: List[Tuple[Sequence[float], int, float]] = []

    def play_audio(self, samples: Sequence[float], sample_rate_hz: int) -> float:
        duration = len(samples) / float(sample_rate_hz) if sample_rate_hz else 0.0
        self.history.append((tuple(samples), sample_rate_hz, duration))
        return duration


class MockDisplayOverlay(DisplayOverlay):
    """Keep a log of overlay text that would be shown."""

    def __init__(self) -> None:
        self.history: List[Tuple[str, timedelta, datetime]] = []

    def show_text(self, text: str, duration: timedelta) -> datetime:
        start_time = _BASE_TIME + timedelta(milliseconds=50 * len(self.history))
        end_time = start_time + duration
        self.history.append((text, duration, end_time))
        return end_time


class MockHaptics(Haptics):
    """Capture haptic pulse patterns for inspection."""

    def __init__(self) -> None:
        self.patterns: List[Tuple[Sequence[float], float]] = []

    def pulse(self, pattern: Sequence[float]) -> float:
        total = float(sum(pattern))
        self.patterns.append((tuple(pattern), total))
        return total


class MockPermissions(Permissions):
    """Simple permission gate with a configurable allow-list."""

    def __init__(self, allowed: Iterable[str] | None = None) -> None:
        self.allowed = set(allowed or {"camera", "microphone", "overlay"})
        self.requests: List[str] = []

    def has_permission(self, capability: str) -> bool:
        return capability in self.allowed

    def require(self, capability: str) -> None:
        self.requests.append(capability)
        if capability not in self.allowed:
            raise PermissionError(f"Capability '{capability}' is not granted")


@dataclass
class MockProvider:
    """Aggregate of the mock driver implementations."""

    camera: MockCameraIn = field(default_factory=MockCameraIn)
    microphone: MockMicIn = field(default_factory=MockMicIn)
    audio_out: MockAudioOut = field(default_factory=MockAudioOut)
    overlay: MockDisplayOverlay = field(default_factory=MockDisplayOverlay)
    haptics: MockHaptics = field(default_factory=MockHaptics)
    permissions: MockPermissions = field(default_factory=MockPermissions)


__all__ = [
    "MockAudioOut",
    "MockCameraIn",
    "MockDisplayOverlay",
    "MockHaptics",
    "MockMicIn",
    "MockPermissions",
    "MockProvider",
]

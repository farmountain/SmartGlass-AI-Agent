"""Deterministic mock implementations of the driver provider interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterator, List, Sequence, Set

import numpy as np

from ..interfaces import AudioOut, CameraIn, DisplayOverlay, Haptics, MicIn, Permissions
from src.io.telemetry import log_metric


_BASE_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _isoformat(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


class MockCameraIn(CameraIn):
    """Yield small synthetic frames with a diagonal gradient."""

    def __init__(self, size: int = 4) -> None:
        self._size = size

    def get_frames(self) -> Iterator[np.ndarray]:
        size = self._size
        base = np.arange(size, dtype=np.uint8)
        while True:
            for offset in range(size):
                frame = (np.add.outer(base, base) + offset).astype(np.uint8)
                yield frame


class MockMicIn(MicIn):
    """Yield deterministic sine wave audio frames."""

    def __init__(self, sample_rate_hz: int = 16000, frame_size: int = 400) -> None:
        self._sample_rate_hz = sample_rate_hz
        self._frame_size = frame_size

    def get_frames(self) -> Iterator[np.ndarray]:
        t = np.arange(self._frame_size, dtype=np.float32)
        base_wave = np.sin(2 * np.pi * 440 * t / self._sample_rate_hz).astype(np.float32)
        index = 0
        while True:
            phase = (index % self._sample_rate_hz) / self._sample_rate_hz
            frame = np.roll(base_wave, index) * np.float32(np.cos(2 * np.pi * phase))
            yield frame.astype(np.float32)
            index += 1


class MockAudioOut(AudioOut):
    """Record utterances and provide deterministic metadata."""

    def __init__(self) -> None:
        self.history: List[Dict[str, object]] = []
        self._utterance_index = 0

    def speak(self, text: str) -> dict:
        timestamp = _BASE_TIME + timedelta(milliseconds=750 * self._utterance_index)
        words = [word for word in text.strip().split() if word]
        duration_ms = 400 * len(words or text)
        payload = {
            "text": text,
            "words": words,
            "duration_ms": duration_ms,
            "utterance_index": self._utterance_index,
            "timestamp": _isoformat(timestamp),
        }
        self.history.append(payload)
        self._utterance_index += 1
        return payload


class MockDisplayOverlay(DisplayOverlay):
    """Record overlay render calls and respond with deterministic payloads."""

    def __init__(self) -> None:
        self.history: List[Dict[str, object]] = []
        self._render_index = 0

    def render(self, card: dict) -> dict:
        rendered_at = _BASE_TIME + timedelta(milliseconds=500 * self._render_index)
        payload = {
            "card": card,
            "render_index": self._render_index,
            "rendered_at": _isoformat(rendered_at),
        }
        self.history.append(payload)
        self._render_index += 1
        return payload


class MockHaptics(Haptics):
    """Capture vibrate calls for later inspection."""

    def __init__(self) -> None:
        self.patterns: List[int] = []

    def vibrate(self, ms: int) -> None:
        self.patterns.append(ms)


class MockPermissions(Permissions):
    """Deterministic permission responses based on an allow-list."""

    def __init__(self, granted: Set[str] | None = None) -> None:
        self.granted = set(granted or {"camera", "microphone", "overlay"})
        self.requests: List[Dict[str, Sequence[str]]] = []

    def request(self, capabilities: set[str]) -> dict:  # noqa: D401 - documented in interface
        requested = set(capabilities)
        requested_list = sorted(requested)
        granted_list = sorted(requested & self.granted)
        denied_list = sorted(requested - self.granted)

        self.requests.append({"requested": requested_list})

        response = {
            "requested": requested_list,
            "granted": granted_list,
            "denied": denied_list,
            "time_ms": 42,
        }
        log_metric("permissions.time_to_ready_ms", response["time_ms"], unit="ms")
        return response


@dataclass
class MockProvider:
    """Aggregate of deterministic mock drivers."""

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

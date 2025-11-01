"""Interfaces for hardware-style drivers used by the agent runtime."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Protocol, Sequence, Tuple


Frame = List[List[int]]
AudioSamples = Sequence[float]
HapticPattern = Sequence[float]


class CameraIn(Protocol):
    """Capture still frames from a camera feed."""

    def get_frame(self) -> Tuple[datetime, Frame]:
        """Return a deterministic timestamp and a synthetic greyscale frame."""


class MicIn(Protocol):
    """Capture short audio segments from a microphone input."""

    def get_audio_chunk(self) -> Tuple[datetime, List[float]]:
        """Return a timestamp and a single-channel audio buffer."""


class AudioOut(Protocol):
    """Send audio to the user's speakers."""

    def play_audio(self, samples: AudioSamples, sample_rate_hz: int) -> float:
        """Play samples at the requested rate and return the clip duration in seconds."""


class DisplayOverlay(Protocol):
    """Show text overlays in the user's field of view."""

    def show_text(self, text: str, duration: timedelta) -> datetime:
        """Display ``text`` for ``duration`` and return the scheduled end time."""


class Haptics(Protocol):
    """Trigger haptic patterns on wearable hardware."""

    def pulse(self, pattern: HapticPattern) -> float:
        """Activate the pattern and return its total length in seconds."""


class Permissions(Protocol):
    """Gate access to privileged capabilities."""

    def has_permission(self, capability: str) -> bool:
        """Return ``True`` if the capability may be used without prompting."""

    def require(self, capability: str) -> None:
        """Raise ``PermissionError`` if the capability is not granted."""


__all__ = [
    "AudioOut",
    "AudioSamples",
    "CameraIn",
    "DisplayOverlay",
    "Frame",
    "Haptics",
    "HapticPattern",
    "MicIn",
    "Permissions",
]

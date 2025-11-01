"""Protocol definitions for hardware-style drivers exposed via the DAL."""

from __future__ import annotations

from typing import Iterator, Protocol

import numpy as np


class CameraIn(Protocol):
    """Capture frames from a camera sensor."""

    def get_frames(self) -> Iterator[np.ndarray]:
        """Yield successive frames as ``numpy.ndarray`` instances."""


class MicIn(Protocol):
    """Capture audio frames from a microphone input."""

    def get_frames(self) -> Iterator[np.ndarray]:
        """Yield successive audio buffers as ``numpy.ndarray`` values."""


class AudioOut(Protocol):
    """Produce synthesized speech for the user."""

    def speak(self, text: str) -> dict:
        """Render ``text`` and return structured metadata about the utterance."""


class DisplayOverlay(Protocol):
    """Render UI overlays to the user's display."""

    def render(self, card: dict) -> dict:
        """Render ``card`` and return a deterministic rendering payload."""


class Haptics(Protocol):
    """Trigger tactile feedback on wearable hardware."""

    def vibrate(self, ms: int) -> None:
        """Vibrate for ``ms`` milliseconds."""


class Permissions(Protocol):
    """Coordinate user permissions for privileged capabilities."""

    def request(self, capabilities: set[str]) -> dict:
        """Request ``capabilities`` and return a structured permission response."""


__all__ = [
    "AudioOut",
    "CameraIn",
    "DisplayOverlay",
    "Haptics",
    "MicIn",
    "Permissions",
]

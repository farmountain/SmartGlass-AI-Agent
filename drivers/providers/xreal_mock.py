"""XREAL deterministic mock provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

import numpy as np

from ..interfaces import CameraIn, MicIn
from .mock import MockAudioOut, MockDisplayOverlay, MockHaptics, MockPermissions


class XrealMockCameraIn(CameraIn):
    """Produce 1080p frames shaped like the XREAL Beam."""

    def __init__(self, height: int = 1080, width: int = 1920) -> None:
        self.height = height
        self.width = width

    def get_frames(self) -> Iterator[np.ndarray]:
        grid_y, grid_x = np.meshgrid(
            np.linspace(0, 1, self.height, dtype=np.float32),
            np.linspace(0, 1, self.width, dtype=np.float32),
            indexing="ij",
        )
        frame_idx = 0
        while True:
            wave = np.sin(2 * np.pi * (grid_x * 3 + frame_idx / 10.0))
            gradient = np.clip(grid_y + frame_idx * 0.01, 0, 1)
            rgb = np.stack(
                [
                    (gradient * 255) % 256,
                    ((wave + 1) * 127.5) % 256,
                    ((gradient * 128) + (wave * 64) + 64) % 256,
                ],
                axis=2,
            ).astype(np.uint8)
            yield rgb
            frame_idx = (frame_idx + 1) % 240


class XrealMockMicIn(MicIn):
    """Emit 48 kHz deterministic microphone frames."""

    def __init__(self, sample_rate_hz: int = 48000, frame_size: int = 960) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.frame_size = frame_size

    def get_frames(self) -> Iterator[np.ndarray]:
        base = np.arange(self.frame_size, dtype=np.float32)
        freqs = np.array([310.0, 620.0], dtype=np.float32)
        index = 0
        while True:
            frame = np.sum(
                np.sin(2 * np.pi * (freqs.reshape(-1, 1) * (base + index) / self.sample_rate_hz)),
                axis=0,
            ).astype(np.float32)
            yield frame
            index = (index + self.frame_size) % self.sample_rate_hz


class XrealMockAudioOut(MockAudioOut):
    """Tag responses with the Nebula runtime."""

    def speak(self, text: str) -> dict:  # noqa: D401
        payload = super().speak(text)
        payload["runtime"] = "xreal-nebula"
        return payload


class XrealMockDisplayOverlay(MockDisplayOverlay):
    """Signal the availability of the AR display."""

    display_name = "nebula"

    def render(self, card: dict) -> dict:  # noqa: D401
        payload = super().render(card)
        payload.update({"display": self.display_name, "has_display": True})
        return payload


class XrealMockHaptics(MockHaptics):
    """Reuse the base haptics recorder."""


class XrealMockPermissions(MockPermissions):
    """Annotate responses with the runtime identifier."""

    def request(self, capabilities: set[str]) -> dict:  # noqa: D401
        payload = super().request(capabilities)
        payload["runtime"] = "xreal"
        return payload


@dataclass
class XrealMockProvider:
    """Aggregate of XREAL-specific mocks."""

    camera: XrealMockCameraIn = field(default_factory=XrealMockCameraIn)
    microphone: XrealMockMicIn = field(default_factory=XrealMockMicIn)
    audio_out: XrealMockAudioOut = field(default_factory=XrealMockAudioOut)
    overlay: XrealMockDisplayOverlay = field(default_factory=XrealMockDisplayOverlay)
    haptics: XrealMockHaptics = field(default_factory=XrealMockHaptics)
    permissions: XrealMockPermissions = field(default_factory=XrealMockPermissions)

    def has_display(self) -> bool:
        return True


__all__ = [
    "XrealMockAudioOut",
    "XrealMockCameraIn",
    "XrealMockDisplayOverlay",
    "XrealMockHaptics",
    "XrealMockMicIn",
    "XrealMockPermissions",
    "XrealMockProvider",
]

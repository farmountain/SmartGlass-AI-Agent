"""Vuzix-branded deterministic mock provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

import numpy as np

from ..interfaces import CameraIn, MicIn
from .mock import MockAudioOut, MockDisplayOverlay, MockHaptics, MockPermissions


class VuzixMockCameraIn(CameraIn):
    """Yield RGB frames shaped like a Vuzix 640x480 sensor."""

    def __init__(self, height: int = 480, width: int = 640) -> None:
        self.height = height
        self.width = width

    def get_frames(self) -> Iterator[np.ndarray]:
        rows = np.linspace(0, 255, self.height, dtype=np.uint8).reshape(self.height, 1, 1)
        cols = np.linspace(0, 255, self.width, dtype=np.uint8).reshape(1, self.width, 1)
        base = (rows + cols) % 256
        frame_idx = 0
        while True:
            offset = (frame_idx * 7) % 256
            red = (base + offset) % 256
            green = np.roll(base, frame_idx % self.height, axis=0)
            blue = np.roll(base, frame_idx % self.width, axis=1)
            frame = np.stack((red, green, blue), axis=2).astype(np.uint8)
            yield frame
            frame_idx = (frame_idx + 1) % 256


class VuzixMockMicIn(MicIn):
    """Stereo-style deterministic microphone frames."""

    def __init__(self, sample_rate_hz: int = 44100, frame_size: int = 2205) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.frame_size = frame_size

    def get_frames(self) -> Iterator[np.ndarray]:
        t = np.arange(self.frame_size, dtype=np.float32) / self.sample_rate_hz
        freqs = np.array([220.0, 440.0, 880.0], dtype=np.float32)
        index = 0
        while True:
            phase = index / 32.0
            frame = np.sum(
                np.sin(2 * np.pi * (freqs.reshape(-1, 1) * t + phase)), axis=0
            ).astype(np.float32)
            yield frame
            index += 1


class VuzixMockAudioOut(MockAudioOut):
    """Annotate mock audio responses with Vuzix metadata."""

    def speak(self, text: str) -> dict:  # noqa: D401 - see base class
        payload = super().speak(text)
        payload["device"] = "vuzix-ultra-lite"
        return payload


class VuzixMockDisplayOverlay(MockDisplayOverlay):
    """Track overlay calls while signalling the display surface."""

    display_name = "waveguide"

    def render(self, card: dict) -> dict:  # noqa: D401
        payload = super().render(card)
        payload.update({"display": self.display_name, "has_display": True})
        return payload


class VuzixMockHaptics(MockHaptics):
    """Tag haptic patterns with the vendor."""

    def vibrate(self, ms: int) -> None:  # noqa: D401
        super().vibrate(ms)
        self.patterns[-1] = int(ms)


class VuzixMockPermissions(MockPermissions):
    """Include vendor annotations in permission responses."""

    def request(self, capabilities: set[str]) -> dict:  # noqa: D401
        payload = super().request(capabilities)
        payload["vendor"] = "vuzix"
        return payload


@dataclass
class VuzixMockProvider:
    """Aggregate of Vuzix-flavoured mocks."""

    camera: VuzixMockCameraIn = field(default_factory=VuzixMockCameraIn)
    microphone: VuzixMockMicIn = field(default_factory=VuzixMockMicIn)
    audio_out: VuzixMockAudioOut = field(default_factory=VuzixMockAudioOut)
    overlay: VuzixMockDisplayOverlay = field(default_factory=VuzixMockDisplayOverlay)
    haptics: VuzixMockHaptics = field(default_factory=VuzixMockHaptics)
    permissions: VuzixMockPermissions = field(default_factory=VuzixMockPermissions)

    def has_display(self) -> bool:
        return True


__all__ = [
    "VuzixMockAudioOut",
    "VuzixMockCameraIn",
    "VuzixMockDisplayOverlay",
    "VuzixMockHaptics",
    "VuzixMockMicIn",
    "VuzixMockPermissions",
    "VuzixMockProvider",
]

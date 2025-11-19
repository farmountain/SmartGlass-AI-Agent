"""visionOS deterministic mock provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

import numpy as np

from ..interfaces import CameraIn, MicIn
from .mock import MockAudioOut, MockDisplayOverlay, MockHaptics, MockPermissions


class VisionOSMockCameraIn(CameraIn):
    """Produce square RGB buffers similar to Persona captures."""

    def __init__(self, size: int = 1440) -> None:
        self.size = size

    def get_frames(self) -> Iterator[np.ndarray]:
        grid = np.linspace(0, 1, self.size, dtype=np.float32)
        grid_y, grid_x = np.meshgrid(grid, grid, indexing="ij")
        frame_idx = 0
        while True:
            swirl = np.sin((grid_x + grid_y) * np.pi * 4 + frame_idx * 0.15)
            depth = np.cos((grid_x - grid_y) * np.pi * 2 + frame_idx * 0.1)
            red = ((grid_x * 255) + frame_idx) % 256
            green = ((grid_y * 255) + (depth * 30)) % 256
            blue = ((swirl + 1) * 127.5) % 256
            frame = np.stack([red, green, blue], axis=2).astype(np.uint8)
            yield frame
            frame_idx = (frame_idx + 1) % 360


class VisionOSMockMicIn(MicIn):
    """Emit deterministic buffers tuned for 48 kHz downlink."""

    def __init__(self, sample_rate_hz: int = 48000, frame_size: int = 960) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.frame_size = frame_size

    def get_frames(self) -> Iterator[np.ndarray]:
        samples = np.arange(self.frame_size, dtype=np.float32)
        freqs = np.array([200.0, 400.0, 800.0, 1600.0], dtype=np.float32)
        tick = 0
        while True:
            phase_offset = tick / self.sample_rate_hz
            frame = np.sum(
                np.sin(
                    2
                    * np.pi
                    * (freqs.reshape(-1, 1) * (samples + phase_offset))
                    / self.sample_rate_hz
                ),
                axis=0,
            ).astype(np.float32)
            yield frame
            tick = (tick + self.frame_size) % self.sample_rate_hz


class VisionOSMockAudioOut(MockAudioOut):
    """Label speech responses as being rendered by AVSpeechSynthesizer."""

    def speak(self, text: str) -> dict:  # noqa: D401
        payload = super().speak(text)
        payload["engine"] = "visionos-avspeech"
        return payload


class VisionOSMockDisplayOverlay(MockDisplayOverlay):
    """Indicate shared-space rendering."""

    display_name = "visionos-shared-space"

    def render(self, card: dict) -> dict:  # noqa: D401
        payload = super().render(card)
        payload.update({"display": self.display_name, "has_display": True})
        return payload


class VisionOSMockHaptics(MockHaptics):
    """Reuse the base haptics log."""


class VisionOSMockPermissions(MockPermissions):
    """Annotate responses with a visionOS origin."""

    def request(self, capabilities: set[str]) -> dict:  # noqa: D401
        payload = super().request(capabilities)
        payload["origin"] = "visionos"
        return payload


@dataclass
class VisionOSMockProvider:
    """Aggregate of visionOS-specific mocks."""

    camera: VisionOSMockCameraIn = field(default_factory=VisionOSMockCameraIn)
    microphone: VisionOSMockMicIn = field(default_factory=VisionOSMockMicIn)
    audio_out: VisionOSMockAudioOut = field(default_factory=VisionOSMockAudioOut)
    overlay: VisionOSMockDisplayOverlay = field(default_factory=VisionOSMockDisplayOverlay)
    haptics: VisionOSMockHaptics = field(default_factory=VisionOSMockHaptics)
    permissions: VisionOSMockPermissions = field(default_factory=VisionOSMockPermissions)

    def has_display(self) -> bool:
        return True


__all__ = [
    "VisionOSMockAudioOut",
    "VisionOSMockCameraIn",
    "VisionOSMockDisplayOverlay",
    "VisionOSMockHaptics",
    "VisionOSMockMicIn",
    "VisionOSMockPermissions",
    "VisionOSMockProvider",
]

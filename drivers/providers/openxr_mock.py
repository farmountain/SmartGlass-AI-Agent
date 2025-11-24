"""OpenXR runtime mock provider with deterministic fixtures."""

from __future__ import annotations

from typing import Iterator

import numpy as np

from ..interfaces import CameraIn, MicIn
from .base import ProviderBase
from .mock import MockAudioOut, MockDisplayOverlay, MockHaptics, MockPermissions


class OpenXRMockCameraIn(CameraIn):
    """Return square eye-buffer frames typical of OpenXR runtimes."""

    def __init__(self, size: int = 1024) -> None:
        self.size = size

    def get_frames(self) -> Iterator[np.ndarray]:
        coords = np.linspace(-1.0, 1.0, self.size, dtype=np.float32)
        grid_y, grid_x = np.meshgrid(coords, coords, indexing="ij")
        frame_idx = 0
        while True:
            radial = np.sqrt(grid_x**2 + grid_y**2)
            pulse = np.sin(4 * np.pi * radial + frame_idx * 0.2)
            red = ((pulse + 1) * 127.5).astype(np.uint8)
            green = ((grid_x + 1) * 127.5).astype(np.uint8)
            blue = ((grid_y + 1) * 127.5).astype(np.uint8)
            frame = np.stack([red, green, blue], axis=2)
            yield frame
            frame_idx = (frame_idx + 1) % 512


class OpenXRMockMicIn(MicIn):
    """Emit deterministic mono buffers shaped to 48 kHz streaming."""

    def __init__(self, sample_rate_hz: int = 48000, frame_size: int = 960) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.frame_size = frame_size

    def get_frames(self) -> Iterator[np.ndarray]:
        indices = np.arange(self.frame_size, dtype=np.float32)
        modulation = np.linspace(0.2, 0.8, self.frame_size, dtype=np.float32)
        tick = 0
        while True:
            base = np.sin(2 * np.pi * (indices + tick) / (self.sample_rate_hz / 200))
            frame = (base * modulation).astype(np.float32)
            yield frame
            tick = (tick + self.frame_size) % self.sample_rate_hz


class OpenXRMockAudioOut(MockAudioOut):
    """Record audio metadata while labelling the OpenXR runtime."""

    def speak(self, text: str) -> dict:  # noqa: D401
        payload = super().speak(text)
        payload["runtime"] = "openxr"
        return payload


class OpenXRMockDisplayOverlay(MockDisplayOverlay):
    """Indicate that overlay rendering must be delegated to the host."""

    def __init__(self) -> None:
        super().__init__()
        self.available = False

    def render(self, card: dict) -> dict:  # noqa: D401
        payload = {
            "card": card,
            "render_index": len(self.history),
            "has_display": False,
            "status": "forward_to_host",
        }
        self.history.append(payload)
        return payload


class OpenXRMockHaptics(MockHaptics):
    """Reuse base haptic recorder."""


class OpenXRMockPermissions(MockPermissions):
    """Annotate responses with the OpenXR layer name."""

    def request(self, capabilities: set[str]) -> dict:  # noqa: D401
        payload = super().request(capabilities)
        payload["layer"] = "XR_EXT_eye_gaze_interaction"
        return payload


class OpenXRMockProvider(ProviderBase):
    """Aggregate of OpenXR-optimised mocks."""

    def __init__(self, *, eye_buffer_size: int = 1024, **kwargs) -> None:
        self._eye_buffer_size = eye_buffer_size
        super().__init__(**kwargs)

    def _create_camera(self) -> CameraIn | None:
        return OpenXRMockCameraIn(size=self._eye_buffer_size)

    def _create_microphone(self) -> MicIn | None:
        return OpenXRMockMicIn()

    def _create_audio_out(self):
        return OpenXRMockAudioOut()

    def _create_overlay(self):
        return OpenXRMockDisplayOverlay()

    def _create_haptics(self):
        return OpenXRMockHaptics()

    def _create_permissions(self):
        return OpenXRMockPermissions()

    def has_display(self) -> bool:
        return False


__all__ = [
    "OpenXRMockAudioOut",
    "OpenXRMockCameraIn",
    "OpenXRMockDisplayOverlay",
    "OpenXRMockHaptics",
    "OpenXRMockMicIn",
    "OpenXRMockPermissions",
    "OpenXRMockProvider",
]

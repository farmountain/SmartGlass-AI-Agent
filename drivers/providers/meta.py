"""Stubs for production-grade driver implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

import numpy as np

from ..interfaces import AudioOut, CameraIn, DisplayOverlay, Haptics, MicIn, Permissions


class MetaCameraIn(CameraIn):
    """Placeholder for the production camera driver."""

    def get_frames(self) -> Iterator[np.ndarray]:  # type: ignore[override]
        raise NotImplementedError


class MetaMicIn(MicIn):
    """Placeholder for the production microphone driver."""

    def get_frames(self) -> Iterator[np.ndarray]:  # type: ignore[override]
        raise NotImplementedError


class MetaAudioOut(AudioOut):
    """Placeholder for the production audio output driver."""

    def speak(self, text: str) -> dict:
        raise NotImplementedError


class MetaDisplayOverlay(DisplayOverlay):
    """Placeholder for the production overlay renderer."""

    def render(self, card: dict) -> dict:
        raise NotImplementedError


class MetaHaptics(Haptics):
    """Placeholder for the production haptics driver."""

    def vibrate(self, ms: int) -> None:
        raise NotImplementedError


class MetaPermissions(Permissions):
    """Placeholder for the production permissions broker."""

    def request(self, capabilities: set[str]) -> dict:
        raise NotImplementedError


@dataclass
class MetaProvider:
    """Aggregate of production driver placeholders."""

    camera: MetaCameraIn = field(default_factory=MetaCameraIn)
    microphone: MetaMicIn = field(default_factory=MetaMicIn)
    audio_out: MetaAudioOut = field(default_factory=MetaAudioOut)
    overlay: MetaDisplayOverlay = field(default_factory=MetaDisplayOverlay)
    haptics: MetaHaptics = field(default_factory=MetaHaptics)
    permissions: MetaPermissions = field(default_factory=MetaPermissions)


__all__ = [
    "MetaAudioOut",
    "MetaCameraIn",
    "MetaDisplayOverlay",
    "MetaHaptics",
    "MetaMicIn",
    "MetaPermissions",
    "MetaProvider",
]

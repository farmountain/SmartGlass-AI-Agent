"""Stubs for production hardware integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Sequence, Tuple

from ..interfaces import (
    AudioOut,
    CameraIn,
    DisplayOverlay,
    Frame,
    Haptics,
    MicIn,
    Permissions,
)


class MetaCameraIn(CameraIn):
    """Placeholder for the production camera driver."""

    def get_frame(self) -> Tuple[datetime, Frame]:
        raise NotImplementedError


class MetaMicIn(MicIn):
    """Placeholder for the production microphone driver."""

    def get_audio_chunk(self) -> Tuple[datetime, List[float]]:
        raise NotImplementedError


class MetaAudioOut(AudioOut):
    """Placeholder for the production audio output driver."""

    def play_audio(self, samples: Sequence[float], sample_rate_hz: int) -> float:
        raise NotImplementedError


class MetaDisplayOverlay(DisplayOverlay):
    """Placeholder for the production overlay driver."""

    def show_text(self, text: str, duration: timedelta) -> datetime:
        raise NotImplementedError


class MetaHaptics(Haptics):
    """Placeholder for the production haptics driver."""

    def pulse(self, pattern: Sequence[float]) -> float:
        raise NotImplementedError


class MetaPermissions(Permissions):
    """Placeholder for the production permissions implementation."""

    def has_permission(self, capability: str) -> bool:
        raise NotImplementedError

    def require(self, capability: str) -> None:
        raise NotImplementedError


@dataclass
class MetaProvider:
    """Aggregate of the Meta hardware driver placeholders."""

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

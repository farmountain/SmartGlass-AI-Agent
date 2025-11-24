"""Shared provider interface and convenience hooks."""

from __future__ import annotations

from typing import Iterator, Protocol

import numpy as np

from ..interfaces import AudioOut, CameraIn, DisplayOverlay, Haptics, MicIn, Permissions


class BaseProvider(Protocol):
    """Protocol describing the common provider surface area."""

    camera: CameraIn | None
    microphone: MicIn | None
    audio_out: AudioOut | None
    overlay: DisplayOverlay | None
    haptics: Haptics | None
    permissions: Permissions | None

    def open_video_stream(self) -> CameraIn | None:
        """Return the camera interface associated with the provider."""

    def open_audio_stream(self) -> MicIn | None:
        """Return the microphone interface associated with the provider."""

    def iter_frames(self) -> Iterator[np.ndarray]:
        """Yield successive video frames from ``open_video_stream``."""

    def iter_audio_chunks(self) -> Iterator[np.ndarray]:
        """Yield successive audio buffers from ``open_audio_stream``."""

    def has_display(self) -> bool:
        """Return ``True`` when a display surface is available."""

    def get_audio_out(self) -> AudioOut | None:
        """Return the audio output device, if configured."""

    def get_overlay(self) -> DisplayOverlay | None:
        """Return the overlay renderer, if configured."""

    def get_haptics(self) -> Haptics | None:
        """Return the haptics driver, if configured."""

    def get_permissions(self) -> Permissions | None:
        """Return the permissions broker, if configured."""


class ProviderBase:
    """Lightweight base class implementing :class:`BaseProvider` conveniences."""

    camera: CameraIn | None
    microphone: MicIn | None
    audio_out: AudioOut | None
    overlay: DisplayOverlay | None
    haptics: Haptics | None
    permissions: Permissions | None

    def __init__(
        self,
        *,
        camera: CameraIn | None = None,
        microphone: MicIn | None = None,
        audio_out: AudioOut | None = None,
        overlay: DisplayOverlay | None = None,
        haptics: Haptics | None = None,
        permissions: Permissions | None = None,
    ) -> None:
        self.camera = camera or self._create_camera()
        self.microphone = microphone or self._create_microphone()
        self.audio_out = audio_out or self._create_audio_out()
        self.overlay = overlay or self._create_overlay()
        self.haptics = haptics or self._create_haptics()
        self.permissions = permissions or self._create_permissions()

    # Factory hooks -----------------------------------------------------
    def _create_camera(self) -> CameraIn | None:
        return None

    def _create_microphone(self) -> MicIn | None:
        return None

    def _create_audio_out(self) -> AudioOut | None:
        return None

    def _create_overlay(self) -> DisplayOverlay | None:
        return None

    def _create_haptics(self) -> Haptics | None:
        return None

    def _create_permissions(self) -> Permissions | None:
        return None

    # Interface helpers -------------------------------------------------
    def open_video_stream(self) -> CameraIn | None:
        return self.camera

    def open_audio_stream(self) -> MicIn | None:
        return self.microphone

    def iter_frames(self) -> Iterator[np.ndarray]:
        camera = self.open_video_stream()
        if camera is None:
            return iter(())
        return camera.get_frames()

    def iter_audio_chunks(self) -> Iterator[np.ndarray]:
        microphone = self.open_audio_stream()
        if microphone is None:
            return iter(())
        return microphone.get_frames()

    def has_display(self) -> bool:
        return bool(self.overlay)

    def get_audio_out(self) -> AudioOut | None:
        return self.audio_out

    def get_overlay(self) -> DisplayOverlay | None:
        return self.overlay

    def get_haptics(self) -> Haptics | None:
        return self.haptics

    def get_permissions(self) -> Permissions | None:
        return self.permissions


__all__ = ["BaseProvider", "ProviderBase"]

"""Ray-Ban aware provider and deterministic SDK simulation hooks.

This module introduces the ``MetaRayBanProvider`` which mirrors the
expected Meta Ray-Ban SDK surface area while keeping CI friendly by
emitting deterministic mock data whenever the SDK or its native
dependencies are not available. The individual driver classes embed
Ray-Ban-flavoured metadata so downstream code can validate payload
shapes without needing hardware.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import itertools
import logging
from typing import Iterator, Mapping

import numpy as np

from ..interfaces import AudioOut, CameraIn, DisplayOverlay, Haptics, MicIn, Permissions
from .base import ProviderBase

LOGGER = logging.getLogger(__name__)

_BASE_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)
_META_SDK_SPEC = importlib.util.find_spec("metarayban")
_META_SDK_AVAILABLE = _META_SDK_SPEC is not None
if _META_SDK_AVAILABLE:
    _META_SDK = importlib.import_module("metarayban")
else:
    _META_SDK = None


def _isoformat(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _normalize_payload(payload: object) -> dict[str, object]:
    if isinstance(payload, Mapping):
        return dict(payload)
    if hasattr(payload, "model_dump"):
        return dict(payload.model_dump())  # type: ignore[call-arg]
    if hasattr(payload, "__dict__"):
        return dict(vars(payload))
    return {"frame": payload}


class MetaRayBanCameraIn(CameraIn):
    """Yield Ray-Ban shaped frames from the SDK or a deterministic mock.

    TODO: Replace the mock generator with a call into the Meta Ray-Ban SDK
    once the official camera streaming APIs are available. The current
    implementation mirrors the expected schema while running entirely
    offline.
    """

    def __init__(
        self,
        *,
        device_id: str,
        transport: str,
        resolution: tuple[int, int] = (720, 960),
        use_sdk: bool = False,
    ) -> None:
        self._device_id = device_id
        self._transport = transport
        self._height, self._width = resolution
        self._use_sdk = use_sdk and _META_SDK_AVAILABLE

    def _wrap_camera_stream(self, stream: Iterator[object]) -> Iterator[dict[str, object]]:
        for frame_id, payload in enumerate(stream):
            enriched = _normalize_payload(payload)
            enriched.setdefault("frame_id", frame_id)
            enriched.setdefault(
                "timestamp_ms",
                int((_BASE_TIME + timedelta(milliseconds=33 * frame_id)).timestamp() * 1000),
            )
            enriched.setdefault("format", "rgb888")
            enriched.setdefault("device_id", self._device_id)
            enriched.setdefault("transport", self._transport)
            yield enriched

    def _sdk_frames(self) -> Iterator[dict[str, object]] | None:
        if not self._use_sdk or _META_SDK is None:
            return None

        stream_iter: Iterator[object] | None = None
        camera_api = getattr(_META_SDK, "camera", None)
        if camera_api is not None:
            stream_factory = getattr(camera_api, "stream_frames", None)
            if callable(stream_factory):
                stream_iter = stream_factory(
                    device_id=self._device_id,
                    transport=self._transport,
                    resolution=(self._height, self._width),
                )
            elif callable(getattr(camera_api, "stream", None)):
                stream_obj = camera_api.stream(
                    device_id=self._device_id, transport=self._transport, resolution=(self._height, self._width)
                )
                frames_callable = getattr(stream_obj, "frames", None)
                if callable(frames_callable):
                    stream_iter = frames_callable()

        if stream_iter is None:
            legacy_factory = getattr(_META_SDK, "camera_frames", None)
            if callable(legacy_factory):
                stream_iter = legacy_factory(
                    device_id=self._device_id,
                    transport=self._transport,
                    resolution=(self._height, self._width),
                )

        if stream_iter is None:
            LOGGER.info("Meta SDK detected; camera streaming is not yet implemented")
            return None

        return self._wrap_camera_stream(stream_iter)

    def get_frames(self) -> Iterator[dict[str, object]]:  # type: ignore[override]
        sdk_stream = self._sdk_frames()
        if sdk_stream is not None:
            yield from sdk_stream
            return

        base = np.linspace(0, 255, num=self._width, dtype=np.uint8)
        gradient = np.tile(base, (self._height, 1))
        for frame_id in itertools.count():
            timestamp = _BASE_TIME + timedelta(milliseconds=33 * frame_id)
            frame = np.stack(
                [
                    gradient,
                    np.roll(gradient, shift=frame_id % self._width, axis=1),
                    np.full_like(gradient, 128, dtype=np.uint8),
                ],
                axis=-1,
            )
            yield {
                "frame": frame,
                "frame_id": frame_id,
                "timestamp_ms": int(timestamp.timestamp() * 1000),
                "device_id": self._device_id,
                "transport": self._transport,
                "format": "rgb888",
            }


class MetaRayBanMicIn(MicIn):
    """Return Ray-Ban-like PCM buffers or stub in deterministic audio.

    TODO: Replace the deterministic generator with SDK microphone capture
    when the Meta Ray-Ban audio APIs are exposed.
    """

    def __init__(
        self,
        *,
        device_id: str,
        transport: str,
        sample_rate_hz: int = 16000,
        frame_size: int = 400,
        channels: int = 1,
        use_sdk: bool = False,
    ) -> None:
        self._device_id = device_id
        self._transport = transport
        self._sample_rate_hz = sample_rate_hz
        self._frame_size = frame_size
        self._channels = channels
        self._use_sdk = use_sdk and _META_SDK_AVAILABLE

    def _wrap_microphone_stream(self, stream: Iterator[object]) -> Iterator[dict[str, object]]:
        for sequence_id, payload in enumerate(stream):
            enriched = _normalize_payload(payload)
            enriched.setdefault("sequence_id", sequence_id)
            enriched.setdefault(
                "timestamp_ms",
                int((_BASE_TIME + timedelta(milliseconds=25 * sequence_id)).timestamp() * 1000),
            )
            enriched.setdefault("sample_rate_hz", self._sample_rate_hz)
            enriched.setdefault("frame_size", self._frame_size)
            enriched.setdefault("channels", self._channels)
            enriched.setdefault("format", "pcm_float32")
            enriched.setdefault("device_id", self._device_id)
            enriched.setdefault("transport", self._transport)
            yield enriched

    def _sdk_frames(self) -> Iterator[dict[str, object]] | None:
        if not self._use_sdk or _META_SDK is None:
            return None

        stream_iter: Iterator[object] | None = None
        microphone_api = getattr(_META_SDK, "microphone", None)
        if microphone_api is not None:
            stream_factory = getattr(microphone_api, "stream_frames", None)
            if callable(stream_factory):
                stream_iter = stream_factory(
                    device_id=self._device_id,
                    transport=self._transport,
                    sample_rate_hz=self._sample_rate_hz,
                    frame_size=self._frame_size,
                    channels=self._channels,
                )
            elif callable(getattr(microphone_api, "stream", None)):
                stream_obj = microphone_api.stream(
                    device_id=self._device_id,
                    transport=self._transport,
                    sample_rate_hz=self._sample_rate_hz,
                    frame_size=self._frame_size,
                    channels=self._channels,
                )
                frames_callable = getattr(stream_obj, "frames", None)
                if callable(frames_callable):
                    stream_iter = frames_callable()

        if stream_iter is None:
            legacy_factory = getattr(_META_SDK, "microphone_frames", None)
            if callable(legacy_factory):
                stream_iter = legacy_factory(
                    device_id=self._device_id,
                    transport=self._transport,
                    sample_rate_hz=self._sample_rate_hz,
                    frame_size=self._frame_size,
                    channels=self._channels,
                )

        if stream_iter is None:
            LOGGER.info("Meta SDK detected; microphone capture is not yet implemented")
            return None

        return self._wrap_microphone_stream(stream_iter)

    def get_frames(self) -> Iterator[dict[str, object]]:  # type: ignore[override]
        sdk_stream = self._sdk_frames()
        if sdk_stream is not None:
            yield from sdk_stream
            return

        t = np.arange(self._frame_size, dtype=np.float32)
        base_wave = np.sin(2 * np.pi * 523.25 * t / self._sample_rate_hz).astype(np.float32)
        for sequence_id in itertools.count():
            timestamp = _BASE_TIME + timedelta(milliseconds=25 * sequence_id)
            gain = 0.2 + 0.05 * np.cos(sequence_id)
            frame = gain * np.roll(base_wave, sequence_id)
            payload = {
                "pcm": frame.reshape(-1, self._channels),
                "sample_rate_hz": self._sample_rate_hz,
                "frame_size": self._frame_size,
                "channels": self._channels,
                "sequence_id": sequence_id,
                "device_id": self._device_id,
                "transport": self._transport,
                "timestamp_ms": int(timestamp.timestamp() * 1000),
            }
            yield payload


class MetaRayBanAudioOut(AudioOut):
    """Synthesize Ray-Ban style TTS payloads or delegate to the SDK.

    TODO: Delegate to the Meta Ray-Ban SDK TTS/earcon API when available.
    """

    def __init__(
        self,
        *,
        device_id: str,
        transport: str,
        api_key: str | None = None,
        use_sdk: bool = False,
    ) -> None:
        self._device_id = device_id
        self._transport = transport
        self._api_key = api_key
        self._utterance_index = 0
        self._use_sdk = use_sdk and _META_SDK_AVAILABLE

    def _sdk_speak(self, text: str) -> dict[str, object] | None:
        if not self._use_sdk or _META_SDK is None:
            return None

        audio_api = getattr(_META_SDK, "audio", None)
        speak_fn = None
        if audio_api is not None:
            speak_fn = getattr(audio_api, "speak", None) or getattr(audio_api, "speak_text", None)
        speak_fn = speak_fn or getattr(_META_SDK, "speak", None)

        if not callable(speak_fn):
            LOGGER.info("Meta SDK detected; audio output is not yet implemented")
            return None

        return speak_fn(
            text=text,
            device_id=self._device_id,
            transport=self._transport,
            api_key=self._api_key,
        )

    def speak(self, text: str) -> dict:
        timestamp = _BASE_TIME + timedelta(milliseconds=480 * self._utterance_index)
        payload = {
            "text": text,
            "utterance_index": self._utterance_index,
            "timestamp": _isoformat(timestamp),
            "device_id": self._device_id,
            "transport": self._transport,
            "api_key": bool(self._api_key),
            "status": "mock",
        }
        sdk_raw = self._sdk_speak(text)
        sdk_response = _normalize_payload(sdk_raw) if sdk_raw is not None else None
        self._utterance_index += 1
        if sdk_response is None:
            return payload

        merged = {**payload, **sdk_response}
        merged.setdefault("status", "sdk")
        return merged


class MetaRayBanDisplayOverlay(DisplayOverlay):
    """Record overlay renders with Ray-Ban metadata for testing.

    TODO: Route overlay cards into the Meta Ray-Ban SDK overlay surface
    once the SDK supports developer access.
    """

    def __init__(self, *, device_id: str, transport: str) -> None:
        self._device_id = device_id
        self._transport = transport
        self.history: list[dict[str, object]] = []
        self._render_index = 0

    def render(self, card: dict) -> dict:
        rendered_at = _BASE_TIME + timedelta(milliseconds=350 * self._render_index)
        payload = {
            "card": card,
            "render_index": self._render_index,
            "device_id": self._device_id,
            "transport": self._transport,
            "rendered_at": _isoformat(rendered_at),
            "status": "mock",
        }
        self.history.append(payload)
        self._render_index += 1
        return payload


class MetaRayBanHaptics(Haptics):
    """Simulate Ray-Ban haptics envelopes and timestamps."""

    def __init__(self, *, device_id: str, transport: str) -> None:
        self._device_id = device_id
        self._transport = transport
        self.patterns: list[dict[str, object]] = []

    def vibrate(self, ms: int) -> None:
        payload = {
            "duration_ms": ms,
            "device_id": self._device_id,
            "transport": self._transport,
            "timestamp": _isoformat(_BASE_TIME + timedelta(milliseconds=len(self.patterns) * 200)),
        }
        self.patterns.append(payload)

    def buzz(self, ms: int) -> None:
        self.vibrate(ms)


class MetaRayBanPermissions(Permissions):
    """Deterministic permission responses mirroring Ray-Ban SDK."""

    def __init__(self, *, device_id: str, transport: str) -> None:
        self._device_id = device_id
        self._transport = transport
        self.requests: list[dict[str, object]] = []

    def request(self, capabilities: set[str]) -> dict:  # noqa: D401 - documented in interface
        requested = sorted(capabilities)
        granted = requested
        denied: list[str] = []
        payload = {
            "requested": requested,
            "granted": granted,
            "denied": denied,
            "device_id": self._device_id,
            "transport": self._transport,
            "time_ms": 12,
        }
        self.requests.append(payload)
        return payload


class MetaRayBanProvider(ProviderBase):
    """Aggregate Meta Ray-Ban drivers that gracefully mock absent SDK calls."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        device_id: str | None = None,
        transport: str = "mock",
        endpoint: str | None = None,
        prefer_sdk: bool | None = None,
        camera_resolution: tuple[int, int] = (720, 960),
        microphone_sample_rate_hz: int = 16000,
        microphone_frame_size: int = 400,
        microphone_channels: int = 1,
        **kwargs,
    ) -> None:
        self._api_key = api_key
        self._device_id = device_id or "RAYBAN-MOCK-DEVICE"
        self._transport = transport
        self._endpoint = endpoint or "https://graph.meta.com/rayban/mock"
        self._use_sdk = bool(prefer_sdk and _META_SDK_AVAILABLE)
        self._camera_resolution = camera_resolution
        self._microphone_sample_rate_hz = microphone_sample_rate_hz
        self._microphone_frame_size = microphone_frame_size
        self._microphone_channels = microphone_channels
        super().__init__(**kwargs)

    def _create_camera(self) -> CameraIn | None:
        return MetaRayBanCameraIn(
            device_id=self._device_id,
            transport=self._transport,
            resolution=self._camera_resolution,
            use_sdk=self._use_sdk,
        )

    def _create_microphone(self) -> MicIn | None:
        return MetaRayBanMicIn(
            device_id=self._device_id,
            transport=self._transport,
            sample_rate_hz=self._microphone_sample_rate_hz,
            frame_size=self._microphone_frame_size,
            channels=self._microphone_channels,
            use_sdk=self._use_sdk,
        )

    def _create_audio_out(self) -> AudioOut | None:
        return MetaRayBanAudioOut(
            device_id=self._device_id,
            transport=self._transport,
            api_key=self._api_key,
            use_sdk=self._use_sdk,
        )

    def _create_overlay(self) -> DisplayOverlay | None:
        return MetaRayBanDisplayOverlay(device_id=self._device_id, transport=self._transport)

    def _create_haptics(self) -> Haptics | None:
        return MetaRayBanHaptics(device_id=self._device_id, transport=self._transport)

    def _create_permissions(self) -> Permissions | None:
        return MetaRayBanPermissions(device_id=self._device_id, transport=self._transport)


__all__ = [
    "MetaRayBanAudioOut",
    "MetaRayBanCameraIn",
    "MetaRayBanDisplayOverlay",
    "MetaRayBanHaptics",
    "MetaRayBanMicIn",
    "MetaRayBanPermissions",
    "MetaRayBanProvider",
]

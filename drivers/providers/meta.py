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
import asyncio
import importlib
import itertools
import logging
from typing import Awaitable, Callable, Iterator, Mapping, Optional

import numpy as np

from ..interfaces import AudioOut, CameraIn, DisplayOverlay, Haptics, MicIn, Permissions
from .base import ProviderBase
from fsm import AsyncDriver, GlassesFSM, GlassesHooks, GlassesState, InteractionBudgets, TimerDriver, TimerHandle
from src.edge_runtime import load_config_from_env
from src.edge_runtime.session_manager import SessionManager

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

        camera_api = getattr(_META_SDK, "camera", None)
        stream_fn = None
        if camera_api is not None:
            stream_fn = getattr(camera_api, "stream_frames", None) or getattr(
                camera_api, "stream", None
            )
        stream_fn = stream_fn or getattr(_META_SDK, "stream_camera_frames", None)

        if not callable(stream_fn):
            LOGGER.info("Meta SDK detected; camera streaming is not available")
            return None

        try:
            stream = stream_fn(
                device_id=self._device_id,
                transport=self._transport,
                resolution=(self._height, self._width),
            )
        except Exception:
            LOGGER.exception("Meta SDK camera streaming failed; falling back to mock")
            return None

        return self._wrap_camera_stream(stream)

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

        microphone_api = getattr(_META_SDK, "microphone", None) or getattr(_META_SDK, "mic", None)
        stream_fn = None
        if microphone_api is not None:
            stream_fn = getattr(microphone_api, "stream_frames", None) or getattr(
                microphone_api, "stream", None
            )
        stream_fn = stream_fn or getattr(_META_SDK, "stream_microphone_frames", None)

        if not callable(stream_fn):
            LOGGER.info("Meta SDK detected; microphone streaming is not available")
            return None

        try:
            stream = stream_fn(
                device_id=self._device_id,
                transport=self._transport,
                sample_rate_hz=self._sample_rate_hz,
                frame_size=self._frame_size,
                channels=self._channels,
            )
        except Exception:
            LOGGER.exception("Meta SDK microphone streaming failed; falling back to mock")
            return None

        return self._wrap_microphone_stream(stream)

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

    def _sdk_audio(self) -> object | None:
        audio_api = getattr(_META_SDK, "audio", None) if _META_SDK is not None else None
        audio_api = audio_api or (getattr(_META_SDK, "tts", None) if _META_SDK is not None else None)
        return audio_api

    def _sdk_speak(self, text: str) -> dict[str, object] | None:
        if not self._use_sdk or _META_SDK is None:
            return None

        audio_api = self._sdk_audio()
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

    def __init__(
        self, *, device_id: str, transport: str, use_sdk: bool = False, api_key: str | None = None
    ) -> None:
        self._device_id = device_id
        self._transport = transport
        self._api_key = api_key
        self._use_sdk = use_sdk and _META_SDK_AVAILABLE
        self.history: list[dict[str, object]] = []
        self._render_index = 0

    def _sdk_render(self, card: dict) -> dict[str, object] | None:
        if not self._use_sdk or _META_SDK is None:
            return None

        overlay_api = getattr(_META_SDK, "overlay", None) or getattr(_META_SDK, "display", None)
        render_fn = None
        if overlay_api is not None:
            render_fn = getattr(overlay_api, "render", None) or getattr(overlay_api, "show", None)
        render_fn = render_fn or getattr(_META_SDK, "render_overlay", None) or getattr(_META_SDK, "display_card", None)

        if not callable(render_fn):
            LOGGER.info("Meta SDK detected; overlay rendering is not yet implemented")
            return None

        return render_fn(
            card=card, device_id=self._device_id, transport=self._transport, api_key=self._api_key
        )

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
        sdk_raw = self._sdk_render(card)
        sdk_response = _normalize_payload(sdk_raw) if sdk_raw is not None else None
        self.history.append(payload)
        self._render_index += 1
        if sdk_response is None:
            return payload

        merged = {**payload, **sdk_response}
        merged.setdefault("status", "sdk")
        return merged


class MetaRayBanHaptics(Haptics):
    """Simulate Ray-Ban haptics envelopes and timestamps."""

    def __init__(
        self,
        *,
        device_id: str,
        transport: str,
        use_sdk: bool = False,
        sdk: object | None = None,
        api_key: str | None = None,
    ) -> None:
        self._device_id = device_id
        self._transport = transport
        self._api_key = api_key
        self._sdk = sdk if sdk is not None else _META_SDK
        self._use_sdk = use_sdk and self._sdk is not None
        self.patterns: list[dict[str, object]] = []

    def _sdk_haptics(self, action: str, ms: int) -> dict[str, object] | None:
        if not self._use_sdk or self._sdk is None:
            return None

        haptics_api = getattr(self._sdk, "haptics", None)
        handler = None
        if haptics_api is not None:
            handler = getattr(haptics_api, action, None)
            handler = handler or getattr(haptics_api, "vibrate", None) or getattr(haptics_api, "buzz", None)
        handler = handler or getattr(self._sdk, action, None)
        handler = handler or getattr(self._sdk, "vibrate", None) or getattr(self._sdk, "buzz", None)

        if not callable(handler):
            LOGGER.info("Meta SDK detected; haptics control is not yet implemented")
            return None

        return handler(
            duration_ms=ms,
            device_id=self._device_id,
            transport=self._transport,
            api_key=self._api_key,
        )

    def vibrate(self, ms: int) -> None:
        payload = {
            "duration_ms": ms,
            "device_id": self._device_id,
            "transport": self._transport,
            "timestamp": _isoformat(_BASE_TIME + timedelta(milliseconds=len(self.patterns) * 200)),
            "status": "mock",
        }
        sdk_raw = self._sdk_haptics("vibrate", ms)
        sdk_response = _normalize_payload(sdk_raw) if sdk_raw is not None else None
        if sdk_response is None:
            self.patterns.append(payload)
            return

        merged = {**payload, **sdk_response}
        merged.setdefault("status", "sdk")
        self.patterns.append(merged)

    def buzz(self, ms: int) -> None:
        sdk_raw = self._sdk_haptics("buzz", ms)
        if sdk_raw is None:
            self.vibrate(ms)
            return

        payload = {
            "duration_ms": ms,
            "device_id": self._device_id,
            "transport": self._transport,
            "timestamp": _isoformat(_BASE_TIME + timedelta(milliseconds=len(self.patterns) * 200)),
            "status": "sdk",
        }
        merged = {**payload, **_normalize_payload(sdk_raw)}
        merged.setdefault("status", "sdk")
        self.patterns.append(merged)


class MetaRayBanPermissions(Permissions):
    """Deterministic permission responses mirroring Ray-Ban SDK."""

    def __init__(
        self, *, device_id: str, transport: str, use_sdk: bool = False, sdk: object | None = None
    ) -> None:
        self._device_id = device_id
        self._transport = transport
        self._sdk = sdk if sdk is not None else _META_SDK
        self._use_sdk = use_sdk and self._sdk is not None
        self.requests: list[dict[str, object]] = []

    def _sdk_request(self, capabilities: set[str]) -> dict[str, object] | None:
        if not self._use_sdk or self._sdk is None:
            return None

        permissions_api = getattr(self._sdk, "permissions", None) or getattr(self._sdk, "permission", None)
        request_fn = None
        if permissions_api is not None:
            request_fn = getattr(permissions_api, "request", None)
        request_fn = request_fn or getattr(self._sdk, "request_permissions", None)

        if not callable(request_fn):
            LOGGER.info("Meta SDK detected; permission negotiation is not yet implemented")
            return None

        return request_fn(capabilities=capabilities, device_id=self._device_id, transport=self._transport)

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
            "status": "mock",
        }
        sdk_raw = self._sdk_request(capabilities)
        sdk_response = _normalize_payload(sdk_raw) if sdk_raw is not None else None
        if sdk_response is None:
            self.requests.append(payload)
            return payload

        merged = {**payload, **sdk_response}
        merged.setdefault("status", "sdk")
        self.requests.append(merged)
        return merged


class MetaRayBanProvider(ProviderBase):
    """Aggregate Meta Ray-Ban drivers that gracefully mock absent SDK calls."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        device_id: str | None = None,
        transport: str = "mock",
        endpoint: str | None = None,
        prefer_sdk: bool = False,
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
        return MetaRayBanDisplayOverlay(
            device_id=self._device_id,
            transport=self._transport,
            use_sdk=self._use_sdk,
            api_key=self._api_key,
        )

    def _create_haptics(self) -> Haptics | None:
        return MetaRayBanHaptics(
            device_id=self._device_id,
            transport=self._transport,
            use_sdk=self._use_sdk,
            sdk=_META_SDK,
            api_key=self._api_key,
        )

    def _create_permissions(self) -> Permissions | None:
        return MetaRayBanPermissions(
            device_id=self._device_id, transport=self._transport, use_sdk=self._use_sdk, sdk=_META_SDK
        )


class _AsyncioTimerHandle(TimerHandle):
    """Adapter allowing :class:`asyncio.TimerHandle` to satisfy ``TimerHandle``."""

    def __init__(self, handle: asyncio.TimerHandle) -> None:
        self._handle = handle

    def cancel(self) -> None:  # pragma: no cover - trivial adapter
        self._handle.cancel()


class AsyncioTimerDriver(TimerDriver):
    """Thin ``TimerDriver`` backed by the current ``asyncio`` loop."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def call_later(self, delay: float, callback: Callable[[], None]) -> TimerHandle:  # type: ignore[override]
        handle = self._loop.call_later(delay, callback)
        return _AsyncioTimerHandle(handle)


class AsyncioAsyncDriver(AsyncDriver):
    """Schedule coroutines without blocking the caller."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def create_task(self, coro: Awaitable[None]) -> None:  # type: ignore[override]
        self._loop.create_task(coro)


class MetaRayBanRuntime:
    """Runtime entrypoint wiring the Meta provider to the glasses FSM."""

    def __init__(
        self,
        provider: Optional[MetaRayBanProvider] = None,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        budgets: Optional[InteractionBudgets] = None,
        session_manager: Optional[SessionManager] = None,
    ) -> None:
        self._loop = loop or asyncio.get_event_loop()
        self._provider = provider or MetaRayBanProvider()
        self._session_manager = session_manager or SessionManager(load_config_from_env())
        self._session_id: Optional[str] = None
        self._audio_task: asyncio.Task[None] | None = None
        self._stop_audio = asyncio.Event()

        self._hooks = GlassesHooks(
            start_audio_stream=self._start_audio_stream,
            stop_audio_stream=self._stop_audio_stream,
            start_tts=self._start_tts,
            stop_tts=self._stop_tts,
            show_overlay=self._show_overlay,
            hide_overlay=self._hide_overlay,
        )

        self._fsm = GlassesFSM(
            timer=AsyncioTimerDriver(self._loop),
            async_driver=AsyncioAsyncDriver(self._loop),
            budgets=budgets
            or InteractionBudgets(listen_timeout=8.0, thinking_timeout=20.0, response_timeout=15.0),
            hooks=self._hooks,
        )

    # Public event bridges -------------------------------------------------
    def handle_wake_word(self) -> None:
        """Dispatch a wake-word event into the FSM."""

        self._fsm.wake_word_detected()

    def handle_button_tap(self) -> None:
        """Dispatch a button-tap event into the FSM."""

        self._fsm.button_tapped()

    def handle_response_ready(self, response_text: str) -> None:
        """Notify the FSM that a response is available."""

        self._fsm.response_ready(response_text)

    def handle_network_error(self) -> None:
        """Propagate network failures into the FSM."""

        self._fsm.network_error()

    def handle_timeout(self) -> None:
        """Signal a timeout to the FSM."""

        self._fsm.timeout()

    # FSM hook implementations --------------------------------------------
    async def _ensure_session(self) -> str:
        if self._session_id is None:
            self._session_id = await asyncio.to_thread(self._session_manager.create_session)
        return self._session_id

    async def _start_audio_stream(self) -> None:
        if self._audio_task and not self._audio_task.done():
            return

        await self._ensure_session()

        microphone = self._provider.open_audio_stream()
        if microphone is None:
            return

        self._stop_audio.clear()

        async def _stream() -> None:
            try:
                for frame in microphone.get_frames():
                    if self._stop_audio.is_set():
                        break
                    payload = frame if isinstance(frame, Mapping) else {"pcm": frame}
                    pcm = payload.get("pcm")
                    if pcm is None:
                        continue
                    sample_rate = payload.get("sample_rate_hz")
                    audio_array = np.asarray(pcm).reshape(-1)
                    await asyncio.to_thread(
                        self._session_manager.ingest_audio,
                        self._session_id,
                        audio_array,
                        None,
                        sample_rate,
                    )
                    await asyncio.sleep(0)
            finally:
                self._stop_audio.clear()

        self._audio_task = self._loop.create_task(_stream())

    async def _stop_audio_stream(self) -> None:
        if self._audio_task is None:
            return
        self._stop_audio.set()
        try:
            await self._audio_task
        finally:
            self._audio_task = None

    async def _start_tts(self, text: str) -> None:
        audio_out = self._provider.get_audio_out()
        if audio_out is None:
            return
        await asyncio.to_thread(audio_out.speak, text)

    async def _stop_tts(self) -> None:
        audio_out = self._provider.get_audio_out()
        if audio_out is None:
            return

        stop_fn = None
        for candidate in ("stop", "flush", "stop_playback", "cancel"):
            maybe = getattr(audio_out, candidate, None)
            if callable(maybe):
                stop_fn = maybe
                break

        if stop_fn is not None:
            await asyncio.to_thread(stop_fn)
            return

        sdk_audio = getattr(_META_SDK, "audio", None) if _META_SDK is not None else None
        for candidate in ("stop", "flush", "stop_playback", "cancel"):
            stop_fn = None
            if sdk_audio is not None:
                stop_fn = getattr(sdk_audio, candidate, None)
            stop_fn = stop_fn or (getattr(_META_SDK, candidate, None) if _META_SDK is not None else None)
            if callable(stop_fn):
                await asyncio.to_thread(
                    stop_fn,
                    device_id=getattr(audio_out, "_device_id", None),
                    transport=getattr(audio_out, "_transport", None),
                )
                return

    async def _show_overlay(self, state: GlassesState) -> None:
        overlay = self._provider.get_overlay()
        if overlay is None:
            return
        card = {"state": state.name.lower(), "visible": True}
        await asyncio.to_thread(overlay.render, card)

    async def _hide_overlay(self, state: GlassesState) -> None:
        overlay = self._provider.get_overlay()
        if overlay is None:
            return
        card = {"state": state.name.lower(), "visible": False}
        await asyncio.to_thread(overlay.render, card)


__all__ = [
    "MetaRayBanAudioOut",
    "MetaRayBanCameraIn",
    "MetaRayBanDisplayOverlay",
    "MetaRayBanHaptics",
    "MetaRayBanMicIn",
    "MetaRayBanPermissions",
    "MetaRayBanProvider",
    "AsyncioAsyncDriver",
    "AsyncioTimerDriver",
    "MetaRayBanRuntime",
]

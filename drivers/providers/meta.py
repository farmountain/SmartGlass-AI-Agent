"""Ray-Ban aware provider and deterministic SDK simulation hooks.

This module introduces the ``MetaRayBanProvider`` which abstracts the
concept of a Meta Ray-Ban data source in the SmartGlass-AI-Agent architecture.

**New Architecture (Meta DAT Integration)**:
- The provider no longer talks directly to hardware via local SDK calls.
- Instead, it expects inputs from the mobile companion app using the Meta
  Wearables Device Access Toolkit (DAT SDK).
- The Android app streams camera frames and audio to the Python backend via HTTP.
- This provider exposes methods to access the latest buffered data from those streams.

**Backward Compatibility**:
- The provider keeps CI-friendly mock data generators for testing.
- Mock fixtures emit deterministic Ray-Ban-shaped payloads when no live data is available.
- This ensures tests work without physical hardware or active DAT connections.

See Also:
    - docs/meta_dat_integration.md: Complete Meta DAT integration guide
    - docs/hello_smartglass_quickstart.md: Quickstart tutorial
    - sdk-android/README_DAT_INTEGRATION.md: Android SDK integration
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio
import importlib
import itertools
import logging
import threading
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


class MetaDatRegistry:
    """Thread-safe registry tracking latest DAT payloads per session.
    
    This registry maintains the most recent camera frame and audio buffer
    for each active session, as received from the mobile companion app via
    the Meta Wearables Device Access Toolkit (DAT).
    
    The HTTP ingestion layer should update this registry when new data arrives:
    
    Example:
        >>> registry = MetaDatRegistry()
        >>> # In your HTTP handler:
        >>> registry.set_frame("session-123", frame_array, metadata)
        >>> registry.set_audio("session-123", audio_buffer, metadata)
        >>> # Later, the provider can retrieve:
        >>> frame, meta = registry.get_latest_frame("session-123")
    
    Thread Safety:
        All methods use an internal lock for safe concurrent access from
        asyncio tasks and threading contexts.
    
    See Also:
        - docs/meta_dat_integration.md: Details on DAT payload formats
        - src/edge_runtime/server.py: HTTP endpoints that should use this registry
    """
    
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frames: dict[str, tuple[np.ndarray, dict[str, object]]] = {}
        self._audio: dict[str, tuple[np.ndarray, dict[str, object]]] = {}
    
    def set_frame(
        self, 
        session_id: str, 
        frame: np.ndarray, 
        metadata: Optional[dict[str, object]] = None
    ) -> None:
        """Store the latest camera frame for a session.
        
        Args:
            session_id: Unique session identifier from the mobile app
            frame: RGB or grayscale frame as numpy array
            metadata: Optional dict with timestamp_ms, device_id, format, etc.
        """
        with self._lock:
            self._frames[session_id] = (frame, metadata or {})
    
    def get_latest_frame(
        self, 
        session_id: str
    ) -> tuple[Optional[np.ndarray], dict[str, object]]:
        """Retrieve the most recent frame for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Tuple of (frame_array, metadata_dict). Returns (None, {}) if no frame.
        """
        with self._lock:
            if session_id not in self._frames:
                return (None, {})
            return self._frames[session_id]
    
    def set_audio(
        self,
        session_id: str,
        audio_buffer: np.ndarray,
        metadata: Optional[dict[str, object]] = None
    ) -> None:
        """Store the latest audio buffer for a session.
        
        Args:
            session_id: Unique session identifier from the mobile app
            audio_buffer: PCM audio samples as numpy array
            metadata: Optional dict with sample_rate_hz, channels, timestamp_ms, etc.
        """
        with self._lock:
            self._audio[session_id] = (audio_buffer, metadata or {})
    
    def get_latest_audio_buffer(
        self,
        session_id: str
    ) -> tuple[Optional[np.ndarray], dict[str, object]]:
        """Retrieve the most recent audio buffer for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Tuple of (audio_array, metadata_dict). Returns (None, {}) if no audio.
        """
        with self._lock:
            if session_id not in self._audio:
                return (None, {})
            return self._audio[session_id]
    
    def clear_session(self, session_id: str) -> None:
        """Remove all data for a session (called on session cleanup).
        
        Args:
            session_id: Session to clear
        """
        with self._lock:
            self._frames.pop(session_id, None)
            self._audio.pop(session_id, None)
    
    def list_sessions(self) -> list[str]:
        """Return all active session IDs with buffered data.
        
        Returns:
            List of session IDs that have frame or audio data
        """
        with self._lock:
            return list(set(self._frames.keys()) | set(self._audio.keys()))


# Global registry instance for DAT payloads
# TODO: This should be updated by HTTP handlers in src/edge_runtime/server.py
# when mobile app sends frames/audio via POST /sessions/{session_id}/frame
# or POST /sessions/{session_id}/audio endpoints.
_DAT_REGISTRY = MetaDatRegistry()


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
    """Aggregate Meta Ray-Ban drivers that gracefully mock absent SDK calls.
    
    **New Architecture**:
    This provider now supports both the legacy direct SDK mode (for backward 
    compatibility) and the new DAT-based streaming mode where the mobile app
    sends frames and audio via HTTP to the backend.
    
    **Usage with Meta DAT**:
        >>> provider = MetaRayBanProvider(session_id="session-123")
        >>> # Mobile app updates the registry via HTTP handlers
        >>> frame = provider.get_latest_frame()
        >>> audio = provider.get_latest_audio_buffer()
    
    **Mock Mode**:
    When no session_id is provided or no DAT data is available, the provider
    falls back to deterministic mock data for testing.
    
    See Also:
        - MetaDatRegistry: Stores per-session frames and audio
        - docs/meta_dat_integration.md: DAT integration architecture
    """

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
        session_id: str | None = None,
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
        self._session_id = session_id  # For DAT streaming mode
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
    
    # DAT Integration Methods -----------------------------------------------
    
    def has_display(self) -> bool:
        """Check if the provider has display capabilities.
        
        Meta Ray-Ban glasses currently do not have a built-in display.
        This returns False to indicate no display surface is available.
        
        Returns:
            False, as Ray-Ban Meta glasses lack a display
        """
        # Meta Ray-Ban glasses don't have a display (unlike Ray-Ban Display glasses)
        # Overlay methods are for future compatibility or mock testing
        return False
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Retrieve the most recent camera frame from DAT streaming.
        
        This method reads from the shared buffer populated by the HTTP ingestion
        layer when the mobile app sends frames via Meta DAT SDK.
        
        Returns:
            The latest RGB frame as numpy array, or None if no frame available
            
        Example:
            >>> provider = MetaRayBanProvider(session_id="my-session")
            >>> frame = provider.get_latest_frame()
            >>> if frame is not None:
            ...     print(f"Frame shape: {frame.shape}")
        
        Note:
            - Falls back to mock data if session_id is None or no frame exists
            - HTTP handlers should update _DAT_REGISTRY when receiving frames
        """
        if self._session_id is None:
            # No session ID, return None (mock mode or legacy usage)
            return None
        
        frame, metadata = _DAT_REGISTRY.get_latest_frame(self._session_id)
        return frame
    
    def get_latest_audio_buffer(self) -> Optional[np.ndarray]:
        """Retrieve the most recent audio buffer from DAT streaming.
        
        This method reads from the shared buffer populated by the HTTP ingestion
        layer when the mobile app sends audio via Meta DAT SDK.
        
        Returns:
            The latest PCM audio buffer as numpy array, or None if unavailable
            
        Example:
            >>> provider = MetaRayBanProvider(session_id="my-session")
            >>> audio = provider.get_latest_audio_buffer()
            >>> if audio is not None:
            ...     print(f"Audio samples: {audio.shape}")
        
        Note:
            - Falls back to None if session_id is None or no audio exists
            - HTTP handlers should update _DAT_REGISTRY when receiving audio
        """
        if self._session_id is None:
            # No session ID, return None (mock mode or legacy usage)
            return None
        
        audio, metadata = _DAT_REGISTRY.get_latest_audio_buffer(self._session_id)
        return audio


# TODO: HTTP Handler Integration
# ================================
# The following shows how HTTP handlers in src/edge_runtime/server.py should
# update the MetaDatRegistry when receiving DAT payloads from the mobile app.
#
# Example integration in server.py:
#
# ```python
# from drivers.providers.meta import _DAT_REGISTRY
#
# @app.post("/sessions/{session_id}/dat/frame")
# def post_dat_frame(session_id: str, payload: DatFramePayload):
#     \"\"\"Receive camera frame from Meta DAT SDK.\"\"\"
#     frame = _decode_image_payload(payload.image_base64)
#     frame_array = np.array(frame)
#     metadata = {
#         "timestamp_ms": payload.timestamp_ms,
#         "device_id": payload.device_id,
#         "format": "rgb888",
#     }
#     _DAT_REGISTRY.set_frame(session_id, frame_array, metadata)
#     return {"status": "ok", "session_id": session_id}
#
# @app.post("/sessions/{session_id}/dat/audio")
# def post_dat_audio(session_id: str, payload: DatAudioPayload):
#     \"\"\"Receive audio chunk from Meta DAT SDK.\"\"\"
#     audio_array, sample_rate = _decode_audio_payload(payload.audio_base64)
#     metadata = {
#         "timestamp_ms": payload.timestamp_ms,
#         "sample_rate_hz": sample_rate,
#         "device_id": payload.device_id,
#     }
#     _DAT_REGISTRY.set_audio(session_id, audio_array, metadata)
#     return {"status": "ok", "session_id": session_id}
# ```
#
# See docs/meta_dat_integration.md for complete payload schemas and examples.


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
    "MetaDatRegistry",
    "AsyncioAsyncDriver",
    "AsyncioTimerDriver",
    "MetaRayBanRuntime",
]

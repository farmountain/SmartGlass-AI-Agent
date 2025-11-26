"""Contract tests for the deterministic mock provider."""

from __future__ import annotations

from itertools import islice
import types

import numpy as np
import pytest

from drivers.providers.mock import MockProvider
from drivers.providers.meta import MetaRayBanProvider
import drivers.providers.meta as meta_module


PROVIDER_FACTORIES = (
    pytest.param(MockProvider, id="mock-provider"),
    pytest.param(lambda: MetaRayBanProvider(prefer_sdk=False), id="meta-mock-provider"),
)


def _take(iterator, count: int):
    return list(islice(iterator, count))


def _extract_frame(raw_frame: object) -> np.ndarray:
    if isinstance(raw_frame, dict) and "frame" in raw_frame:
        return np.asarray(raw_frame["frame"])
    return np.asarray(raw_frame)


def _extract_audio_frame(chunk: object) -> np.ndarray:
    if isinstance(chunk, dict) and "pcm" in chunk:
        return np.asarray(chunk["pcm"], dtype=np.float32).squeeze()
    return np.asarray(chunk, dtype=np.float32)


def _install_fake_sdk(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    class FakeCamera:
        def __init__(self):
            self.calls: list[dict[str, object]] = []

        def stream_frames(self, *, device_id: str, transport: str, resolution: tuple[int, int]):
            self.calls.append({"device_id": device_id, "transport": transport, "resolution": resolution})
            for idx in range(2):
                yield {
                    "frame": np.full((*resolution, 3), idx, dtype=np.uint8),
                    "timestamp_ms": 1700000000 + idx,
                }

    class FakeMicrophone:
        def __init__(self):
            self.calls: list[dict[str, object]] = []

        def stream_frames(
            self, *, device_id: str, transport: str, sample_rate_hz: int, frame_size: int, channels: int
        ):
            self.calls.append(
                {
                    "device_id": device_id,
                    "transport": transport,
                    "sample_rate_hz": sample_rate_hz,
                    "frame_size": frame_size,
                    "channels": channels,
                }
            )
            while True:
                yield {
                    "pcm": np.zeros((frame_size, channels), dtype=np.float32),
                    "format": "pcm_float32",
                }

    class FakeAudio:
        def __init__(self):
            self.calls: list[dict[str, object]] = []

        def speak(self, *, text: str, device_id: str, transport: str, api_key: str | None):
            self.calls.append(
                {"text": text, "device_id": device_id, "transport": transport, "api_key": api_key}
            )
            return {
                "text": text,
                "device_id": device_id,
                "transport": transport,
                "status": "sdk",
            }

    class FakeOverlay:
        def __init__(self):
            self.calls: list[dict[str, object]] = []

        def render(self, *, card: dict, device_id: str, transport: str):
            self.calls.append({"card": card, "device_id": device_id, "transport": transport})
            return {"card": card, "device_id": device_id, "transport": transport, "status": "sdk"}

    class FakeHaptics:
        def __init__(self):
            self.calls: list[dict[str, object]] = []

        def vibrate(self, *, duration_ms: int, device_id: str, transport: str):
            payload = {
                "duration_ms": duration_ms,
                "device_id": device_id,
                "transport": transport,
                "status": "sdk",
            }
            self.calls.append(payload)
            return payload

        def buzz(self, *, duration_ms: int, device_id: str, transport: str):
            return self.vibrate(duration_ms=duration_ms, device_id=device_id, transport=transport)

    class FakePermissions:
        def __init__(self):
            self.calls: list[dict[str, object]] = []

        def request(self, *, capabilities: set[str], device_id: str, transport: str):
            payload = {
                "requested": sorted(capabilities),
                "granted": sorted(capabilities),
                "denied": [],
                "device_id": device_id,
                "transport": transport,
                "status": "sdk",
            }
            self.calls.append(payload)
            return payload

    fake_sdk = types.SimpleNamespace(
        camera=FakeCamera(),
        microphone=FakeMicrophone(),
        audio=FakeAudio(),
        overlay=FakeOverlay(),
        haptics=FakeHaptics(),
        permissions=FakePermissions(),
    )
    fake_sdk.camera_calls = fake_sdk.camera.calls
    fake_sdk.microphone_calls = fake_sdk.microphone.calls
    fake_sdk.audio_calls = fake_sdk.audio.calls
    fake_sdk.overlay_calls = fake_sdk.overlay.calls
    fake_sdk.haptics_calls = fake_sdk.haptics.calls
    fake_sdk.permissions_calls = fake_sdk.permissions.calls

    monkeypatch.setattr(meta_module, "_META_SDK_AVAILABLE", True)
    monkeypatch.setattr(meta_module, "_META_SDK", fake_sdk)
    return fake_sdk


@pytest.mark.parametrize("provider_factory", PROVIDER_FACTORIES)
def test_camera_frames_are_deterministic(provider_factory) -> None:
    provider = provider_factory()
    frames_a = [_extract_frame(frame) for frame in _take(provider.iter_frames(), 3)]
    frames_b = [_extract_frame(frame) for frame in _take(provider.iter_frames(), 3)]
    assert all(np.array_equal(a, b) for a, b in zip(frames_a, frames_b))
    assert frames_a[0].dtype == np.uint8
    assert not np.array_equal(frames_a[0], frames_a[1])


@pytest.mark.parametrize("provider_factory", PROVIDER_FACTORIES)
def test_microphone_frames_are_deterministic(provider_factory) -> None:
    provider = provider_factory()
    frames = [_extract_audio_frame(chunk) for chunk in _take(provider.iter_audio_chunks(), 2)]
    assert all(frame.dtype == np.float32 for frame in frames)
    assert all(frame.shape == frames[0].shape for frame in frames)
    second_run = [_extract_audio_frame(chunk) for chunk in _take(provider.iter_audio_chunks(), 2)]
    assert all(np.array_equal(a, b) for a, b in zip(frames, second_run))


@pytest.mark.parametrize("provider_factory", PROVIDER_FACTORIES)
def test_audio_out_metadata_progresses(provider_factory) -> None:
    provider = provider_factory()
    audio_out = provider.get_audio_out()
    assert audio_out is not None
    first = audio_out.speak("hello world")
    second = audio_out.speak("hello world")
    assert first["utterance_index"] == 0
    assert second["utterance_index"] == 1
    assert first["timestamp"] != second["timestamp"]
    assert first["text"] == "hello world"
    if "words" in first:
        assert first["words"] == ["hello", "world"]


def test_meta_audio_out_mock_fallback_when_sdk_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(meta_module, "_META_SDK_AVAILABLE", False)
    monkeypatch.setattr(meta_module, "_META_SDK", None)
    provider = MetaRayBanProvider(prefer_sdk=True)
    audio_out = provider.get_audio_out()
    assert audio_out is not None
    first = audio_out.speak("offline")
    second = audio_out.speak("offline")
    assert first["status"] == "mock"
    assert first["transport"] == "mock"
    assert first["utterance_index"] == 0
    assert second["utterance_index"] == 1


@pytest.mark.parametrize("provider_factory", PROVIDER_FACTORIES)
def test_overlay_render_metadata(provider_factory) -> None:
    provider = provider_factory()
    overlay = provider.get_overlay()
    assert overlay is not None
    result = overlay.render({"title": "test"})
    assert result["card"] == {"title": "test"}
    assert result["render_index"] == 0
    again = overlay.render({"title": "test"})
    assert again["render_index"] == 1


def test_overlay_prefers_sdk_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sdk = _install_fake_sdk(monkeypatch)
    provider = MetaRayBanProvider(prefer_sdk=True, transport="sdk")
    overlay = provider.get_overlay()
    assert overlay is not None

    response = overlay.render({"title": "sdk"})

    assert fake_sdk.overlay_calls
    assert fake_sdk.overlay_calls[0]["card"] == {"title": "sdk"}
    assert fake_sdk.overlay_calls[0]["transport"] == "sdk"
    assert response["status"] == "sdk"
    assert response["render_index"] == 0


def test_overlay_history_retained_without_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(meta_module, "_META_SDK_AVAILABLE", False)
    monkeypatch.setattr(meta_module, "_META_SDK", None)
    provider = MetaRayBanProvider(prefer_sdk=True)
    overlay = provider.get_overlay()
    assert overlay is not None

    first = overlay.render({"title": "offline"})
    second = overlay.render({"title": "offline"})

    assert first["status"] == "mock"
    assert second["render_index"] == 1
    assert overlay.history == [first, second]


def test_meta_haptics_uses_sdk_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sdk = _install_fake_sdk(monkeypatch)
    provider = MetaRayBanProvider(prefer_sdk=True, transport="sdk")

    haptics = provider.get_haptics()
    assert haptics is not None

    haptics.vibrate(250)
    haptics.buzz(180)

    assert len(fake_sdk.haptics_calls) == 2
    assert fake_sdk.haptics_calls[0]["duration_ms"] == 250
    assert fake_sdk.haptics_calls[1]["duration_ms"] == 180
    assert all(call["transport"] == "sdk" for call in fake_sdk.haptics_calls)
    assert all(pattern.get("status") == "sdk" for pattern in haptics.patterns)


def test_meta_haptics_falls_back_without_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(meta_module, "_META_SDK_AVAILABLE", False)
    monkeypatch.setattr(meta_module, "_META_SDK", None)
    provider = MetaRayBanProvider(prefer_sdk=True)
    haptics = provider.get_haptics()
    assert haptics is not None

    haptics.vibrate(100)
    haptics.buzz(200)

    assert len(haptics.patterns) == 2
    assert all(pattern["status"] == "mock" for pattern in haptics.patterns)
    assert haptics.patterns[0]["duration_ms"] == 100
    assert haptics.patterns[1]["duration_ms"] == 200


def test_meta_permissions_uses_sdk_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sdk = _install_fake_sdk(monkeypatch)
    provider = MetaRayBanProvider(prefer_sdk=True, transport="sdk")

    permissions = provider.get_permissions()
    assert permissions is not None

    response = permissions.request({"camera", "gps"})

    assert fake_sdk.permissions_calls
    assert response["status"] == "sdk"
    assert response["requested"] == sorted({"camera", "gps"})
    assert response["granted"] == sorted({"camera", "gps"})
    assert response["transport"] == "sdk"


def test_meta_permissions_fall_back_without_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(meta_module, "_META_SDK_AVAILABLE", False)
    monkeypatch.setattr(meta_module, "_META_SDK", None)
    provider = MetaRayBanProvider(prefer_sdk=True)
    permissions = provider.get_permissions()
    assert permissions is not None

    response = permissions.request({"camera", "gps"})

    assert response["status"] == "mock"
    assert set(response["granted"]) | set(response["denied"]) == set(response["requested"])
    assert response["transport"] == "mock"


@pytest.mark.parametrize("provider_factory", PROVIDER_FACTORIES)
def test_haptics_vibrate_records_calls(provider_factory) -> None:
    provider = provider_factory()
    haptics = provider.get_haptics()
    assert haptics is not None
    assert haptics.vibrate(120) is None
    assert len(haptics.patterns) == 1
    pattern = haptics.patterns[0]
    if isinstance(pattern, dict):
        assert pattern["duration_ms"] == 120
    else:
        assert pattern == 120


@pytest.mark.parametrize("provider_factory", PROVIDER_FACTORIES)
def test_permissions_request_reports_grants(provider_factory) -> None:
    provider = provider_factory()
    permissions = provider.get_permissions()
    assert permissions is not None
    response = permissions.request({"camera", "gps"})
    assert response["requested"] == sorted(response["requested"])
    assert set(response["granted"]) | set(response["denied"]) == set(response["requested"])


def test_meta_provider_prefers_sdk_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sdk = _install_fake_sdk(monkeypatch)
    provider = MetaRayBanProvider(prefer_sdk=True, transport="sdk")

    with pytest.raises(NotImplementedError):
        next(provider.iter_frames())

    with pytest.raises(NotImplementedError):
        next(provider.iter_audio_chunks())

    audio_out = provider.get_audio_out()
    assert audio_out is not None

    with pytest.raises(NotImplementedError):
        audio_out.speak("hi")

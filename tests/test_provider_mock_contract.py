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
    fake_sdk = types.SimpleNamespace(camera_calls=[], microphone_calls=[])

    def camera_frames(*, device_id: str, transport: str, resolution: tuple[int, int]):
        fake_sdk.camera_calls.append({"device_id": device_id, "transport": transport, "resolution": resolution})
        for idx in range(2):
            yield {
                "frame_id": f"sdk-camera-{idx}",
                "frame": np.full((*resolution, 3), idx, dtype=np.uint8),
                "timestamp_ms": 1700000000 + idx,
                "device_id": device_id,
                "transport": transport,
                "format": "rgb888",
            }

    def microphone_frames(
        *, device_id: str, transport: str, sample_rate_hz: int, frame_size: int, channels: int
    ):
        fake_sdk.microphone_calls.append(
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
                "sample_rate_hz": sample_rate_hz,
                "frame_size": frame_size,
                "channels": channels,
                "device_id": device_id,
                "transport": transport,
                "format": "pcm_float32",
            }

    fake_sdk.camera_frames = camera_frames
    fake_sdk.microphone_frames = microphone_frames

    monkeypatch.setattr(meta_module.meta, "_META_SDK_AVAILABLE", True)
    monkeypatch.setattr(meta_module.meta, "_META_SDK", fake_sdk)
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

    frame = next(provider.iter_frames())
    audio_chunk = next(provider.iter_audio_chunks())

    assert fake_sdk.camera_calls and fake_sdk.microphone_calls
    assert frame["frame_id"].startswith("sdk-camera-")
    assert frame["format"] == "rgb888"
    assert frame["device_id"] == fake_sdk.camera_calls[0]["device_id"]
    assert frame["transport"] == "sdk"

    assert audio_chunk["format"] == "pcm_float32"
    assert audio_chunk["sample_rate_hz"] == fake_sdk.microphone_calls[0]["sample_rate_hz"]
    assert audio_chunk["frame_size"] == fake_sdk.microphone_calls[0]["frame_size"]
    assert audio_chunk["channels"] == fake_sdk.microphone_calls[0]["channels"]
    assert audio_chunk["device_id"] == fake_sdk.microphone_calls[0]["device_id"]
    assert audio_chunk["transport"] == "sdk"

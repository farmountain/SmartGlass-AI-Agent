"""Contract tests for the deterministic mock provider."""

from __future__ import annotations

from itertools import islice
from types import SimpleNamespace

import numpy as np
import pytest

from drivers.providers.mock import MockProvider
from drivers.providers.meta import MetaRayBanProvider


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


def test_meta_provider_prefers_sdk_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    camera_payloads = [
        {
            "frame": np.zeros((2, 2, 3), dtype=np.uint8),
            "frame_id": 10,
            "timestamp_ms": 1234,
            "format": "rgb888",
        },
        {
            "frame": np.ones((2, 2, 3), dtype=np.uint8),
            "frame_id": 11,
            "timestamp_ms": 1235,
            "format": "rgb888",
        },
    ]
    mic_payloads = [
        {
            "pcm": np.full((4, 1), 0.5, dtype=np.float32),
            "sequence_id": 3,
            "timestamp_ms": 2000,
        }
    ]

    stub_sdk = SimpleNamespace(
        camera=SimpleNamespace(stream_frames=lambda **_: iter(camera_payloads)),
        microphone=SimpleNamespace(stream_pcm=lambda **_: iter(mic_payloads)),
    )
    import drivers.providers.meta as meta_module

    monkeypatch.setattr(meta_module, "_META_SDK", stub_sdk)
    monkeypatch.setattr(meta_module, "_META_SDK_AVAILABLE", True)

    provider = MetaRayBanProvider(
        prefer_sdk=True,
        device_id="SDK-DEVICE",
        transport="wifi",
        camera_resolution=(2, 2),
        microphone_frame_size=4,
        microphone_channels=1,
    )

    frame = next(provider.iter_frames())
    assert frame["frame_id"] == 10
    assert frame["device_id"] == "SDK-DEVICE"
    assert frame["transport"] == "wifi"
    assert frame["timestamp_ms"] == camera_payloads[0]["timestamp_ms"]
    assert frame["format"] == camera_payloads[0]["format"]
    assert np.array_equal(frame["frame"], camera_payloads[0]["frame"])

    audio_chunk = next(provider.iter_audio_chunks())
    assert audio_chunk["sequence_id"] == 3
    assert audio_chunk["device_id"] == "SDK-DEVICE"
    assert audio_chunk["transport"] == "wifi"
    assert audio_chunk["timestamp_ms"] == mic_payloads[0]["timestamp_ms"]
    assert audio_chunk["sample_rate_hz"] == 16000
    assert audio_chunk["frame_size"] == 4
    assert audio_chunk["channels"] == 1
    assert np.array_equal(np.asarray(audio_chunk["pcm"]), mic_payloads[0]["pcm"])

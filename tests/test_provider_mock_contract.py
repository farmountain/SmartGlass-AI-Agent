"""Contract tests for the deterministic mock provider."""

from __future__ import annotations

from itertools import islice

import numpy as np

from drivers.providers.mock import MockProvider


def _take(iterator, count: int):
    return list(islice(iterator, count))


def test_camera_frames_are_deterministic() -> None:
    provider = MockProvider()
    frames_a = _take(provider.iter_frames(), 3)
    frames_b = _take(provider.iter_frames(), 3)
    assert all(np.array_equal(a, b) for a, b in zip(frames_a, frames_b))
    assert frames_a[0].shape == (4, 4)
    assert not np.array_equal(frames_a[0], frames_a[1])


def test_microphone_frames_are_deterministic() -> None:
    provider = MockProvider()
    frames = _take(provider.iter_audio_chunks(), 2)
    assert all(frame.dtype == np.float32 for frame in frames)
    assert all(frame.shape == frames[0].shape for frame in frames)
    second_run = _take(provider.iter_audio_chunks(), 2)
    assert all(np.array_equal(a, b) for a, b in zip(frames, second_run))


def test_audio_out_metadata_progresses() -> None:
    provider = MockProvider()
    audio_out = provider.get_audio_out()
    assert audio_out is not None
    first = audio_out.speak("hello world")
    second = audio_out.speak("hello world")
    assert first["utterance_index"] == 0
    assert second["utterance_index"] == 1
    assert first["timestamp"] != second["timestamp"]
    assert first["words"] == ["hello", "world"]


def test_overlay_render_metadata() -> None:
    provider = MockProvider()
    overlay = provider.get_overlay()
    assert overlay is not None
    result = overlay.render({"title": "test"})
    assert result["card"] == {"title": "test"}
    assert result["render_index"] == 0
    again = overlay.render({"title": "test"})
    assert again["render_index"] == 1


def test_haptics_vibrate_records_calls() -> None:
    provider = MockProvider()
    haptics = provider.get_haptics()
    assert haptics is not None
    assert haptics.vibrate(120) is None
    assert haptics.patterns == [120]


def test_permissions_request_reports_grants() -> None:
    provider = MockProvider()
    permissions = provider.get_permissions()
    assert permissions is not None
    response = permissions.request({"camera", "gps"})
    assert response["requested"] == ["camera", "gps"]
    assert response["granted"] == ["camera"]
    assert response["denied"] == ["gps"]

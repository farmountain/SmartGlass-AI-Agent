"""Behavioural contract tests for the deterministic mock provider."""

from __future__ import annotations

from datetime import timedelta
import math

import pytest

from drivers.providers.mock import (
    MockAudioOut,
    MockCameraIn,
    MockDisplayOverlay,
    MockHaptics,
    MockMicIn,
    MockPermissions,
    MockProvider,
    _BASE_TIME,
)


@pytest.fixture()
def mock_provider() -> MockProvider:
    return MockProvider()


def test_mock_camera_frames_progress_by_index(mock_provider: MockProvider) -> None:
    timestamp0, frame0 = mock_provider.camera.get_frame()
    timestamp1, frame1 = mock_provider.camera.get_frame()

    assert timestamp0 == _BASE_TIME
    assert timestamp1 == _BASE_TIME + timedelta(milliseconds=100)

    expected_first_frame = [
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [8, 9, 10, 11],
        [12, 13, 14, 15],
    ]
    assert frame0 == expected_first_frame

    expected_second_frame = [[(value + 1) % 256 for value in row] for row in frame0]
    assert frame1 == expected_second_frame


def test_mock_microphone_returns_repeatable_sine_wave(mock_provider: MockProvider) -> None:
    timestamp0, samples0 = mock_provider.microphone.get_audio_chunk()
    timestamp1, samples1 = mock_provider.microphone.get_audio_chunk()

    assert timestamp0 == _BASE_TIME
    assert timestamp1 == _BASE_TIME + timedelta(seconds=len(samples0) / 16000.0)

    assert len(samples0) == len(samples1) == 160

    for index, sample in enumerate(samples0[:5]):
        expected = round(math.sin(index / 40.0), 6)
        assert sample == expected

    delta = [round(b - a, 6) for a, b in zip(samples0, samples1)]
    assert any(value != 0.0 for value in delta)


def test_mock_audio_out_records_playback_history() -> None:
    audio_out = MockAudioOut()
    samples = [0.0, 0.25, -0.25, 0.0]
    duration = audio_out.play_audio(samples, sample_rate_hz=16000)

    assert pytest.approx(duration) == len(samples) / 16000.0
    assert audio_out.history == [
        (tuple(samples), 16000, duration),
    ]


def test_mock_overlay_stores_text_and_end_times(mock_provider: MockProvider) -> None:
    end_a = mock_provider.overlay.show_text("hello", timedelta(milliseconds=300))
    end_b = mock_provider.overlay.show_text("world", timedelta(milliseconds=200))

    assert end_a == _BASE_TIME + timedelta(milliseconds=300)
    assert end_b == _BASE_TIME + timedelta(milliseconds=50 + 200)

    assert mock_provider.overlay.history == [
        ("hello", timedelta(milliseconds=300), end_a),
        ("world", timedelta(milliseconds=200), end_b),
    ]


def test_mock_haptics_store_patterns_and_totals(mock_provider: MockProvider) -> None:
    total = mock_provider.haptics.pulse([0.1, 0.2, 0.3])
    assert pytest.approx(total) == 0.6
    assert mock_provider.haptics.patterns == [
        ((0.1, 0.2, 0.3), total),
    ]


def test_mock_permissions_track_requests_and_enforce(mock_provider: MockProvider) -> None:
    assert mock_provider.permissions.has_permission("camera")
    mock_provider.permissions.require("camera")
    assert mock_provider.permissions.requests == ["camera"]

    with pytest.raises(PermissionError):
        mock_provider.permissions.require("forbidden")


def test_mock_provider_exposes_component_singletons(mock_provider: MockProvider) -> None:
    assert isinstance(mock_provider.camera, MockCameraIn)
    assert isinstance(mock_provider.microphone, MockMicIn)
    assert isinstance(mock_provider.audio_out, MockAudioOut)
    assert isinstance(mock_provider.overlay, MockDisplayOverlay)
    assert isinstance(mock_provider.haptics, MockHaptics)
    assert isinstance(mock_provider.permissions, MockPermissions)

    # Repeated access should return the same component instances.
    assert mock_provider.camera is mock_provider.camera
    assert mock_provider.microphone is mock_provider.microphone

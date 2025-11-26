"""Provider conformance tests for SmartGlassAgent ingestion compatibility."""

from __future__ import annotations

from itertools import islice
from typing import Iterable

import pytest

np = pytest.importorskip("numpy")

try:
    from drivers.providers import get_provider
    import drivers.providers.meta as meta_module
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    if exc.name == "whisper":
        pytest.skip("whisper dependency missing", allow_module_level=True)
    raise

SUPPORTED_PROVIDER_NAMES = ("mock", "meta", "vuzix", "xreal", "openxr", "visionos")


@pytest.fixture(autouse=True)
def _force_mock_meta_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the Meta provider operates in mock mode for hermetic tests."""

    monkeypatch.setattr(meta_module, "_META_SDK_AVAILABLE", False)
    monkeypatch.setattr(meta_module, "_META_SDK", None)


def _take(items: Iterable[object], count: int) -> list[object]:
    return list(islice(items, count))


def _extract_frame(raw_frame: object) -> np.ndarray:
    if isinstance(raw_frame, dict) and "frame" in raw_frame:
        return np.asarray(raw_frame["frame"])
    return np.asarray(raw_frame)


def _extract_audio(raw_chunk: object) -> np.ndarray:
    if isinstance(raw_chunk, dict) and "pcm" in raw_chunk:
        return np.asarray(raw_chunk["pcm"], dtype=np.float32).squeeze()
    return np.asarray(raw_chunk, dtype=np.float32)


@pytest.mark.parametrize("provider_name", SUPPORTED_PROVIDER_NAMES)
def test_supported_providers_expose_camera_and_mic(provider_name: str) -> None:
    """Every supported provider must expose camera and microphone streams."""

    provider = get_provider(provider_name)

    camera = provider.open_video_stream()
    microphone = provider.open_audio_stream()

    assert camera is not None, f"camera missing for provider {provider_name}"
    assert microphone is not None, f"microphone missing for provider {provider_name}"

    first_frame = _extract_frame(next(provider.iter_frames()))
    first_audio = _extract_audio(next(provider.iter_audio_chunks()))

    assert first_frame.ndim >= 2 and first_frame.size > 0
    assert first_audio.ndim >= 1 and first_audio.size > 0
    assert first_frame.dtype == np.uint8
    assert first_audio.dtype == np.float32


@pytest.mark.parametrize("provider_name", ["mock", "meta"])
def test_mocked_providers_emit_deterministic_shapes(provider_name: str) -> None:
    """Mock-backed providers yield stable frame and audio buffer shapes."""

    provider = get_provider(provider_name)

    frames = [_extract_frame(frame) for frame in _take(provider.iter_frames(), 2)]
    audio = [_extract_audio(chunk) for chunk in _take(provider.iter_audio_chunks(), 2)]

    assert all(frame.shape == frames[0].shape for frame in frames)
    assert all(chunk.shape == audio[0].shape for chunk in audio)

    if provider_name == "mock":
        expected_size = getattr(provider.camera, "_size", None) or 4
        expected_audio = getattr(provider.microphone, "_frame_size", None) or 400

        assert frames[0].shape == (expected_size, expected_size)
        assert audio[0].shape == (expected_audio,)
        assert np.array_equal(
            frames[0],
            np.add.outer(np.arange(expected_size), np.arange(expected_size)).astype(np.uint8),
        )

    if provider_name == "meta":
        expected_height = getattr(provider.camera, "_height", None) or 720
        expected_width = getattr(provider.camera, "_width", None) or 960
        expected_audio = getattr(provider.microphone, "_frame_size", None) or 400
        expected_channels = getattr(provider.microphone, "_channels", None) or 1

        assert frames[0].shape == (expected_height, expected_width, 3)
        assert audio[0].shape == (expected_audio, expected_channels)
        assert np.allclose(audio[0][:5], audio[1][:5])

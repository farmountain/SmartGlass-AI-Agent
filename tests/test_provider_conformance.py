"""Provider conformance tests for SmartGlassAgent ingestion compatibility."""

from __future__ import annotations

from itertools import islice
from typing import Iterable

import pytest

np = pytest.importorskip("numpy")

try:
    from drivers.factory import get_provider
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
def test_supported_providers_expose_camera_and_mic(provider_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every supported provider must expose camera and microphone streams."""

    monkeypatch.setenv("PROVIDER", provider_name)
    provider = get_provider()

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
def test_mock_providers_emit_deterministic_streams(provider_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock-backed providers must yield repeatable camera and microphone frames."""

    monkeypatch.setenv("PROVIDER", provider_name)
    provider = get_provider()

    frames_first = [_extract_frame(frame) for frame in _take(provider.iter_frames(), 3)]
    frames_second = [_extract_frame(frame) for frame in _take(provider.iter_frames(), 3)]

    audio_first = [_extract_audio(chunk) for chunk in _take(provider.iter_audio_chunks(), 2)]
    audio_second = [_extract_audio(chunk) for chunk in _take(provider.iter_audio_chunks(), 2)]

    assert all(np.array_equal(a, b) for a, b in zip(frames_first, frames_second))
    assert all(np.array_equal(a, b) for a, b in zip(audio_first, audio_second))

    assert frames_first[0].shape == frames_second[0].shape
    assert audio_first[0].shape == audio_second[0].shape

    if provider_name == "mock":
        assert np.array_equal(frames_first[0], np.array([[0, 1, 2, 3], [1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6]], dtype=np.uint8))
        assert np.allclose(audio_first[0][:5], audio_first[1][:5])

    if provider_name == "meta":
        assert frames_first[0].shape[-1] == 3  # RGB888 mock frames
        assert audio_first[0].shape == (provider.microphone._frame_size,) or audio_first[0].ndim == 2
        assert np.allclose(audio_first[0][:10], audio_second[0][:10])

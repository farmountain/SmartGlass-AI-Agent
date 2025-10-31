"""Perception utilities for keyframing, VAD, vector quantization, and OCR."""

import os

from .asr_stream import ASRStream, MockASR, WhisperASRStream
from .ocr import MockOCR
from .vad import EnergyVAD
from .vision_keyframe import VQEncoder, select_keyframes


def get_default_keyframer():
    """Return the default keyframe selection callable."""

    return select_keyframes


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_default_vad(
    *,
    frame_ms: float = 20.0,
    sample_rate: int = 16_000,
    threshold: float = 0.01,
) -> EnergyVAD:
    """Return the default VAD backend implementation."""

    return EnergyVAD(frame_ms=frame_ms, sample_rate=sample_rate, threshold=threshold)


def get_default_asr(
    *,
    stability_delta: float = 0.1,
    stability_consecutive: int = 2,
    frame_duration_ms: float = 20.0,
) -> ASRStream:
    """Return the default streaming ASR interface."""

    if _env_flag("USE_WHISPER_STREAMING"):
        return WhisperASRStream(
            stability_delta=stability_delta,
            stability_consecutive=stability_consecutive,
            frame_duration_ms=frame_duration_ms,
        )

    return ASRStream(
        asr_backend=MockASR(),
        stability_delta=stability_delta,
        stability_consecutive=stability_consecutive,
        frame_duration_ms=frame_duration_ms,
    )


def get_default_vq(seed: int | None = None) -> VQEncoder:
    """Return the default vector-quantizer encoder instance.

    Parameters
    ----------
    seed:
        Optional override for the deterministic encoder seed. When ``None`` the
        module default is used.
    """

    return VQEncoder(seed=seed)


def get_default_ocr() -> MockOCR:
    """Return the default OCR backend implementation."""

    if _env_flag("USE_EASYOCR"):
        raise RuntimeError("EasyOCR backend is not available in offline mode.")
    if _env_flag("USE_TESSERACT"):
        raise RuntimeError("Tesseract backend is not available in offline mode.")
    return MockOCR()


__all__ = [
    "ASRStream",
    "get_default_keyframer",
    "get_default_asr",
    "get_default_ocr",
    "get_default_vad",
    "get_default_vq",
    "EnergyVAD",
    "MockASR",
    "WhisperASRStream",
    "select_keyframes",
    "VQEncoder",
]

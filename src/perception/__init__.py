"""Perception utilities for keyframing, VAD, vector quantization, and OCR."""

import os

from .ocr import MockOCR
from .vad import EnergyVAD
from .vision_keyframe import VQEncoder, select_keyframes


def get_default_keyframer():
    """Return the default keyframe selection callable."""

    return select_keyframes


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


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
    "get_default_keyframer",
    "get_default_ocr",
    "get_default_vq",
    "EnergyVAD",
    "select_keyframes",
    "VQEncoder",
]

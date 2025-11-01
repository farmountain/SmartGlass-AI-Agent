"""Tests for the vector-quantised encoder stub."""

from __future__ import annotations

import numpy as np

from tests.vision_keyframe_utils import VQEncoder


def _synthetic_frame(size: int = 32) -> np.ndarray:
    frame = np.zeros((size, size), dtype=np.float32)
    frame[size // 4 : size // 4 + 6, size // 3 : size // 3 + 6] = 0.5
    frame[size // 2 : size // 2 + 4, size // 2 : size // 2 + 4] = 1.0
    return frame


def test_vq_encoder_shape_and_dtype() -> None:
    encoder = VQEncoder()
    frame = _synthetic_frame()
    code = encoder.encode(frame)
    assert code.shape == (encoder.code_dim,)
    assert code.dtype == np.float32


def test_vq_encoder_is_brightness_invariant() -> None:
    encoder = VQEncoder()
    frame = _synthetic_frame()
    brighter = frame + 1.5
    code = encoder.encode(frame)
    bright_code = encoder.encode(brighter)
    np.testing.assert_allclose(code, bright_code)

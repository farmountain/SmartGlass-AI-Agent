"""Tests for frame-difference driven keyframe selection."""

from __future__ import annotations

import numpy as np

from tests.vision_keyframe_utils import select_keyframes


def _moving_square_clip(frames: int = 24, size: int = 32) -> np.ndarray:
    clip = np.zeros((frames, size, size), dtype=np.float32)
    square_size = size // 8
    for idx in range(frames):
        col = (idx * 2) % (size - square_size)
        clip[idx, size // 4 : size // 4 + square_size, col : col + square_size] = 1.0
    return clip


def _static_clip(frames: int = 16, size: int = 32) -> np.ndarray:
    base = np.zeros((size, size), dtype=np.float32)
    base[size // 3 : size // 3 + 4, size // 2 : size // 2 + 4] = 0.5
    return np.repeat(base[None, ...], frames, axis=0)


def test_moving_scene_selects_reasonable_keyframes() -> None:
    clip = _moving_square_clip()
    keyframes = select_keyframes(clip, diff_tau=6.0, min_gap=2)
    assert keyframes[0] == 0
    assert keyframes[-1] == clip.shape[0] - 1
    assert 4 <= len(keyframes) <= clip.shape[0] // 2
    gaps = np.diff(keyframes)
    assert np.all(gaps >= 2)


def test_static_scene_has_minimal_keyframes() -> None:
    clip = _static_clip()
    keyframes = select_keyframes(clip)
    assert keyframes == [0, clip.shape[0] - 1]

"""Provider contract tests for camera keyframe utilities."""

from __future__ import annotations

import numpy as np

from drivers.providers.mock import MockProvider

from tests.vision_keyframe_utils import frames_from_camera, select_keyframes


def test_frames_from_camera_is_deterministic() -> None:
    provider = MockProvider()
    clip_a = frames_from_camera(provider, seconds=1.0)
    clip_b = frames_from_camera(provider, seconds=1.0)
    assert clip_a.shape == clip_b.shape
    assert clip_a.shape[:2] == (4, 4)
    np.testing.assert_allclose(clip_a, clip_b)


def test_camera_keyframes_are_stable() -> None:
    provider = MockProvider()
    clip = frames_from_camera(provider, seconds=1.0)
    frames = np.moveaxis(clip, -1, 0)
    indices_a = select_keyframes(frames, diff_tau=2.0, min_gap=1)
    indices_b = select_keyframes(frames, diff_tau=2.0, min_gap=1)
    assert indices_a == indices_b
    assert indices_a[0] == 0
    assert indices_a[-1] == frames.shape[0] - 1

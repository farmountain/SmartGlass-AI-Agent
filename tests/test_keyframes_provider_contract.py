import numpy as np

from src.perception.vision_keyframe import frames_from_camera, select_keyframes


class MockProvider:
    def __init__(self, clip: np.ndarray):
        self._clip = np.asarray(clip, dtype=np.float32)

    def camera(self, *, seconds: int = 1):
        assert seconds >= 1
        for frame in self._clip:
            yield frame.copy()


def test_frames_from_camera_returns_grayscale_tensor():
    time_steps = 5
    height, width = 8, 12
    clip = np.stack(
        [
            np.full((height, width, 3), fill_value=float(t), dtype=np.float32)
            for t in range(time_steps)
        ],
        axis=0,
    )
    provider = MockProvider(clip)

    frames = frames_from_camera(provider, seconds=2)

    assert frames.shape == (height, width, time_steps)
    assert frames.dtype == np.float32
    expected_first = np.full((height, width), fill_value=0.0, dtype=np.float32)
    assert np.allclose(frames[..., 0], expected_first)
    assert np.allclose(frames[..., -1], np.full((height, width), time_steps - 1, dtype=np.float32))


def test_select_keyframes_stable_from_provider_clip():
    time_steps = 12
    height, width = 16, 16
    clip = np.zeros((time_steps, height, width), dtype=np.float32)
    for idx in range(time_steps):
        clip[idx, idx % height] = idx
    provider = MockProvider(clip)

    frames_a = frames_from_camera(provider, seconds=1)
    frames_b = frames_from_camera(provider, seconds=1)

    np.testing.assert_allclose(frames_a, frames_b)

    sequence_a = np.moveaxis(frames_a, -1, 0)
    sequence_b = np.moveaxis(frames_b, -1, 0)
    keyframes_a = select_keyframes(sequence_a, min_gap=2)
    keyframes_b = select_keyframes(sequence_b, min_gap=2)

    assert keyframes_a == keyframes_b
    assert keyframes_a[0] == 0
    assert keyframes_a[-1] == time_steps - 1

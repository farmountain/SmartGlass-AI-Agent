import numpy as np

from src.perception import get_default_keyframer


def _make_moving_square(num_frames: int = 30, size: int = 12, frame_size: int = 64) -> np.ndarray:
    frames = np.zeros((num_frames, frame_size, frame_size, 1), dtype=np.float32)
    step = (frame_size - size) / (num_frames - 1)
    for idx in range(num_frames):
        top = int(round(idx * step))
        left = int(round(idx * step / 2))
        frames[idx, top : top + size, left : left + size, 0] = 1.0
    return frames


def test_keyframe_rate_bounds():
    frames = _make_moving_square()
    selector = get_default_keyframer()
    keyframes = selector(frames, min_gap=3)

    assert 5 <= len(keyframes) <= 12
    assert keyframes[0] == 0
    assert keyframes[-1] == len(frames) - 1

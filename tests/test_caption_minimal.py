import numpy as np

from src.perception.vision_keyframe import VQEncoder, select_keyframes
from src.skills.caption import MockCaptioner, caption_from_frames


def _moving_square(num_frames: int = 12, size: int = 6) -> np.ndarray:
    frames = []
    height = width = 32
    for idx in range(num_frames):
        frame = np.zeros((height, width), dtype=np.float32)
        start = min(idx, width - size)
        frame[8:8 + size, start:start + size] = 1.0
        frames.append(frame)
    return np.stack(frames, axis=0)


def test_caption_from_frames_reports_motion_and_signature():
    frames = _moving_square()
    caption = caption_from_frames(frames, ocr_text="EXIT")

    key_indices = select_keyframes(frames)
    keyframes = [frames[i] for i in key_indices]
    features = VQEncoder(seed=0).encode(keyframes)
    codes = np.clip(np.floor(np.abs(features.mean(axis=0)[:3]) * 10).astype(int), 0, 999)
    signature = "-".join(str(int(code)) for code in codes)

    assert f"{len(key_indices)} keyframes" in caption
    assert "motion towards right" in caption
    assert f"texture codes {signature}" in caption
    assert caption.endswith("OCR snippet: EXIT.")


def test_mock_captioner_matches_helper():
    frames = _moving_square()
    helper_caption = caption_from_frames(frames)
    captioner = MockCaptioner()
    assert captioner.generate(frames) == helper_caption

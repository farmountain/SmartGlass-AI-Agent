import numpy as np

from src.perception.vision_keyframe import VQEncoder, select_keyframes
from src.skills.caption import MockCaptioner, caption_from_frames, caption_from_provider


def _moving_square(num_frames: int = 12, size: int = 6) -> np.ndarray:
    frames = []
    height = width = 32
    for idx in range(num_frames):
        frame = np.zeros((height, width), dtype=np.float32)
        start = min(idx, width - size)
        frame[8:8 + size, start:start + size] = 1.0
        frames.append(frame)
    return np.stack(frames, axis=0)


class _Audio:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> dict:
        self.spoken.append(text)
        return {"text": text}


class _Display:
    def __init__(self) -> None:
        self.rendered: dict | None = None

    def render(self, payload: dict) -> dict:
        self.rendered = payload
        return payload


class _Provider:
    def __init__(self, frames: np.ndarray, *, show_overlay: bool) -> None:
        self._frames = frames
        self.audio = _Audio()
        self.display = _Display()
        self._show_overlay = show_overlay

    def camera(self, *, seconds: int = 1):
        del seconds
        for frame in self._frames:
            yield frame

    def has_display(self) -> bool:
        return self._show_overlay


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


def test_caption_from_provider_produces_caption_and_audio():
    frames = _moving_square()
    provider = _Provider(frames, show_overlay=False)

    payload = caption_from_provider(provider)

    assert payload["type"] == "caption"
    assert payload["text"].strip()
    assert provider.audio.spoken == [payload["text"]]
    assert provider.display.rendered is None

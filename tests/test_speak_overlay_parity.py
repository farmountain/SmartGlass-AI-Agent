import numpy as np

from src.skills.caption import caption_from_provider


def _moving_square(num_frames: int = 8, size: int = 5) -> np.ndarray:
    frames = []
    height = width = 24
    for idx in range(num_frames):
        frame = np.zeros((height, width), dtype=np.float32)
        start = min(idx, width - size)
        frame[4:4 + size, start:start + size] = 1.0
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


def test_caption_overlay_phone_parity():
    frames = _moving_square()

    overlay_provider = _Provider(frames, show_overlay=True)
    phone_provider = _Provider(frames, show_overlay=False)

    overlay_payload = caption_from_provider(overlay_provider)
    phone_payload = caption_from_provider(phone_provider)

    assert overlay_provider.display.rendered == overlay_payload
    assert overlay_payload == phone_payload
    assert overlay_provider.audio.spoken == [overlay_payload["text"]]
    assert phone_provider.audio.spoken == [phone_payload["text"]]

"""Caption synthesis utilities for keyframe-based video descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from src.perception.vision_keyframe import VQEncoder, select_keyframes

__all__ = ["MockCaptioner", "caption_from_frames"]


def _to_array(frames: Sequence[np.ndarray] | np.ndarray) -> np.ndarray:
    """Normalize inputs into a ``(T, H, W[, C])`` numpy array."""

    array = np.asarray(frames)
    if array.ndim < 3:
        raise ValueError("Expected frames with at least 3 dimensions")
    return array


def _centroid(frame: np.ndarray) -> np.ndarray:
    """Return the intensity-weighted centroid of a frame as ``(y, x)``."""

    if frame.ndim == 3:
        frame = frame.mean(axis=2)
    grid = np.asarray(frame, dtype=np.float32)
    height, width = grid.shape
    total = float(grid.sum())
    if total <= 0:
        return np.array([height / 2.0, width / 2.0], dtype=np.float32)

    ys, xs = np.indices(grid.shape, dtype=np.float32)
    cy = float((ys * grid).sum() / total)
    cx = float((xs * grid).sum() / total)
    return np.array([cy, cx], dtype=np.float32)


def _describe_motion(frames: Iterable[np.ndarray]) -> str:
    frames = list(frames)
    if not frames:
        return "no visible content"

    centroids = [_centroid(frame) for frame in frames]
    start, end = centroids[0], centroids[-1]
    diff = end - start
    magnitude = float(np.linalg.norm(diff))
    if magnitude < 0.5:
        return "scene appears static"

    horizontal: str | None = None
    vertical: str | None = None
    dx = diff[1]
    dy = diff[0]
    if abs(dx) > 0.5:
        horizontal = "right" if dx > 0 else "left"
    if abs(dy) > 0.5:
        vertical = "down" if dy > 0 else "up"

    if horizontal and vertical:
        return f"motion towards {horizontal} and {vertical}"
    if horizontal:
        return f"motion towards {horizontal}"
    if vertical:
        return f"motion towards {vertical}"
    return "scene appears static"


def _signature_from_features(features: np.ndarray) -> str:
    if features.size == 0:
        return "0-0-0"
    mean = features.mean(axis=0)
    codes = np.clip(np.floor(np.abs(mean[:3]) * 10).astype(int), 0, 999)
    return "-".join(str(int(code)) for code in codes)


def caption_from_frames(
    frames: Sequence[np.ndarray] | np.ndarray,
    *,
    ocr_text: str | None = None,
    diff_tau: float = 8.0,
    min_gap: int = 3,
    encoder: VQEncoder | None = None,
) -> str:
    """Generate a deterministic caption from a clip of frames."""

    array = _to_array(frames)
    if array.shape[0] == 0:
        return "No frames available."

    key_indices = select_keyframes(array, diff_tau=diff_tau, min_gap=min_gap)
    keyframes = [array[idx] for idx in key_indices]

    vq = encoder or VQEncoder(seed=0)
    features = vq.encode(keyframes)
    motion = _describe_motion(keyframes)
    signature = _signature_from_features(features)

    parts = [
        f"{len(key_indices)} keyframes",
        motion,
        f"texture codes {signature}",
    ]
    caption = "; ".join(parts) + "."
    if ocr_text:
        ocr = ocr_text.strip()
        if ocr:
            caption += f" OCR snippet: {ocr}."
    return caption


@dataclass
class MockCaptioner:
    """A reproducible captioner that summarizes clips using keyframes."""

    diff_tau: float = 8.0
    min_gap: int = 3
    seed: int | None = 0

    def __post_init__(self) -> None:
        self._encoder = VQEncoder(seed=self.seed)

    def generate(self, frames: Sequence[np.ndarray] | np.ndarray, *, ocr_text: str | None = None) -> str:
        return caption_from_frames(
            frames,
            ocr_text=ocr_text,
            diff_tau=self.diff_tau,
            min_gap=self.min_gap,
            encoder=self._encoder,
        )

    __call__ = generate

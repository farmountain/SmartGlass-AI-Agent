"""Keyframe selection and deterministic vector-quantized encoding utilities."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from typing import List

import numpy as np


def _to_grayscale(frame: np.ndarray) -> np.ndarray:
    """Convert a frame to grayscale float32 representation."""

    array = np.asarray(frame)
    if array.ndim == 2:
        return array.astype(np.float32, copy=False)
    if array.ndim == 3:
        return array.mean(axis=-1, dtype=np.float32)
    raise ValueError("frame must have shape (H, W) or (H, W, C)")


def _downsample(frame: np.ndarray) -> np.ndarray:
    """Downsample a frame to an 8x8 grid via average pooling."""

    gray = _to_grayscale(frame)
    height, width = gray.shape

    if height == 8 and width == 8:
        return gray.astype(np.float32, copy=False)

    row_edges = np.linspace(0, height, num=9, dtype=int)
    col_edges = np.linspace(0, width, num=9, dtype=int)

    downsampled = np.zeros((8, 8), dtype=np.float32)
    for i in range(8):
        r0, r1 = row_edges[i], row_edges[i + 1]
        if r1 <= r0:
            continue
        for j in range(8):
            c0, c1 = col_edges[j], col_edges[j + 1]
            if c1 <= c0:
                continue
            region = gray[r0:r1, c0:c1]
            downsampled[i, j] = float(region.mean()) if region.size else 0.0

    return downsampled


def select_keyframes(frames: np.ndarray, diff_tau: float = 8.0, min_gap: int = 3) -> List[int]:
    """Select keyframes using downsampled L1 frame differences."""

    if min_gap < 1:
        raise ValueError("min_gap must be at least 1")

    sequence = np.asarray(frames)
    if sequence.ndim < 3:
        raise ValueError("frames should have shape (T, H, W[, C])")

    total_frames = sequence.shape[0]
    if total_frames == 0:
        return []

    downsampled = np.array([_downsample(frame).reshape(-1) for frame in sequence], dtype=np.float32)

    keyframes: List[int] = [0]
    last_selected = 0
    accumulated = 0.0

    for idx in range(1, total_frames):
        diff = np.sum(np.abs(downsampled[idx] - downsampled[idx - 1]))
        accumulated += float(diff)
        if idx - last_selected < min_gap:
            continue
        if accumulated >= diff_tau:
            keyframes.append(idx)
            last_selected = idx
            accumulated = 0.0

    if keyframes[-1] != total_frames - 1:
        keyframes.append(total_frames - 1)

    return keyframes


def frames_from_camera(provider, seconds: float = 1.0) -> np.ndarray:
    """Fetch a grayscale ``H×W×T`` clip from ``provider.camera``."""

    if seconds <= 0:
        raise ValueError("seconds must be positive")

    camera = getattr(provider, "camera", None)
    if camera is None or not hasattr(camera, "get_frames"):
        raise AttributeError("provider.camera.get_frames is required")

    fps = getattr(camera, "fps", None) or getattr(camera, "frames_per_second", None)
    if fps is None:
        frame_count = max(1, int(round(seconds * 10)))
    else:
        frame_count = max(1, int(round(float(fps) * float(seconds))))

    iterator = camera.get_frames()
    frames = list(islice(iterator, frame_count))
    if not frames:
        raise RuntimeError("camera returned no frames")

    grayscale = [_to_grayscale(frame) for frame in frames]
    first_shape = grayscale[0].shape
    if any(frame.shape != first_shape for frame in grayscale):
        raise ValueError("camera frames must share dimensions")

    stack = np.stack(grayscale, axis=-1)
    return stack.astype(np.float32, copy=False)


@dataclass
class VQEncoder:
    """Deterministic vector-quantized encoder for keyframe representations."""

    codebook_size: int = 256
    code_dim: int = 8
    seed: int | None = 0

    def __post_init__(self) -> None:
        rng = np.random.default_rng(0 if self.seed is None else int(self.seed))
        self._projection = rng.standard_normal((64, self.code_dim), dtype=np.float32)
        self._codebook = rng.standard_normal((self.codebook_size, self.code_dim), dtype=np.float32)

    def encode(self, frame: np.ndarray) -> np.ndarray:
        """Encode a frame by projecting and quantizing to the nearest centroid."""

        downsampled = _downsample(frame).reshape(-1).astype(np.float32)
        downsampled -= float(downsampled.mean())
        projected = downsampled @ self._projection
        distances = np.sum((self._codebook - projected) ** 2, axis=1)
        centroid = self._codebook[int(np.argmin(distances))]
        return centroid.astype(np.float32, copy=True)

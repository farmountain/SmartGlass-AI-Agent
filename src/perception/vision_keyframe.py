"""Keyframe selection and deterministic vector-quantized encoding utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import numpy as np


def _downsample(frame: np.ndarray) -> np.ndarray:
    """Downsample a frame to an 8x8 grayscale grid using average pooling.

    The function accepts frames with shapes ``(H, W)`` or ``(H, W, C)`` and
    returns a float32 array. Channels, if present, are averaged before the
    spatial reduction. The computation is deterministic and purely uses NumPy
    operations, ensuring compatibility with environments where OpenCV or PIL are
    unavailable.
    """

    if frame.ndim == 3:
        frame = frame.mean(axis=2)
    frame = np.asarray(frame, dtype=np.float32)

    height, width = frame.shape[:2]
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
            region = frame[r0:r1, c0:c1]
            downsampled[i, j] = float(region.mean()) if region.size else 0.0

    return downsampled


def select_keyframes(frames: np.ndarray, diff_tau: float = 8.0, min_gap: int = 3) -> List[int]:
    """Select keyframes from a sequence based on downsampled L2 differences.

    Parameters
    ----------
    frames:
        Array of frames with shape ``(T, H, W, C)`` or ``(T, H, W)``.
    diff_tau:
        Threshold for the L2 distance between downsampled frames required to
        accept a new keyframe.
    min_gap:
        Minimum number of frames that must separate two keyframes.

    Returns
    -------
    list[int]
        Sorted list of frame indices to retain.
    """

    if min_gap < 1:
        raise ValueError("min_gap must be at least 1")

    frames = np.asarray(frames)
    if frames.ndim < 3:
        raise ValueError("frames should have at least 3 dimensions")

    total_frames = frames.shape[0]
    if total_frames == 0:
        return []

    downsampled = np.array([_downsample(f).reshape(-1) for f in frames], dtype=np.float32)
    if frames.ndim >= 3:
        scale = (frames.shape[1] * frames.shape[2]) / float(downsampled.shape[1])
    else:
        scale = 1.0

    keyframes: List[int] = [0]
    last_idx = 0
    accumulated_diff = 0.0
    for idx in range(1, total_frames):
        diff = float(np.linalg.norm(downsampled[idx] - downsampled[idx - 1]) * scale)
        accumulated_diff += diff
        if idx - last_idx < min_gap:
            continue
        if accumulated_diff >= diff_tau:
            keyframes.append(idx)
            last_idx = idx
            accumulated_diff = 0.0

    if keyframes[-1] != total_frames - 1:
        keyframes.append(total_frames - 1)

    return keyframes


@dataclass
class VQEncoder:
    """Deterministic vector-quantized encoder for keyframe representations."""

    seed: int | None = None
    projection_dim: int = 16
    codebook_size: int = 64

    def __post_init__(self) -> None:
        rng_seed = 0 if self.seed is None else int(self.seed)
        self._rng = np.random.default_rng(rng_seed)
        self._projection = self._rng.standard_normal((64, self.projection_dim), dtype=np.float32)
        self._codebook = self._rng.standard_normal((self.codebook_size, self.projection_dim), dtype=np.float32)

    def encode(self, frames: Iterable[np.ndarray]) -> np.ndarray:
        """Encode frames by quantizing projected, centered 8x8 downsampled grids."""

        features = []
        for frame in frames:
            downsampled = _downsample(np.asarray(frame))
            flat = downsampled.reshape(-1).astype(np.float32)
            flat -= flat.mean()
            projected = flat @ self._projection
            distances = np.sum((self._codebook - projected) ** 2, axis=1)
            centroid = self._codebook[int(np.argmin(distances))]
            features.append(centroid)

        if not features:
            return np.empty((0, self.projection_dim), dtype=np.float32)

        return np.stack(features, axis=0).astype(np.float32)

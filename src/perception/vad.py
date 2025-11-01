"""Lightweight energy-based voice activity detection targeting ~20 ms latency.

The :class:`EnergyVAD` implementation slices mono PCM buffers into short,
fixed-duration frames (20 milliseconds by default) and compares their mean
squared energy against a configurable threshold. Larger thresholds filter out
quieter speakers or background noise, while smaller thresholds increase
sensitivity at the cost of more false positives. Adjusting the ``frame_ms``
parameter trades latency for smoothing: shorter frames reduce decision latency
while longer frames average across more samples and provide additional
robustness at the cost of responsiveness.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator, Sequence

import math

try:  # pragma: no cover - exercised implicitly by import
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - environment without numpy
    np = None  # type: ignore[assignment]


def _ensure_mono_numpy(buffer: object, dtype: "np.dtype[Any]" | type) -> "np.ndarray":
    """Coerce input into a 1-D NumPy array when NumPy is available."""

    samples = np.asarray(buffer, dtype=dtype)  # type: ignore[union-attr]
    if samples.ndim != 1:  # type: ignore[union-attr]
        raise ValueError("EnergyVAD expects mono (1-D) audio input")
    return samples


def _ensure_mono_python(buffer: Iterable[float] | Sequence[float]) -> list[float]:
    """Fallback conversion that accepts basic Python iterables."""

    if isinstance(buffer, (str, bytes, bytearray)):
        raise TypeError("EnergyVAD expects an iterable of numeric samples")

    if hasattr(buffer, "tolist"):
        data = buffer.tolist()  # type: ignore[call-arg]
    else:
        try:
            data = list(buffer)  # type: ignore[arg-type]
        except TypeError as exc:  # pragma: no cover - defensive
            raise TypeError("EnergyVAD expects an iterable of numeric samples") from exc

    if not data:
        return []

    first = data[0]
    if isinstance(first, (list, tuple)):
        raise ValueError("EnergyVAD expects mono (1-D) audio input")

    return [float(sample) for sample in data]


class EnergyVAD:
    """Energy-based voice activity detector with simple latency controls."""

    def __init__(
        self,
        *,
        frame_ms: float = 20.0,
        sample_rate: int = 16_000,
        threshold: float = 0.01,
    ) -> None:
        if frame_ms <= 0:
            raise ValueError("frame_ms must be positive")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if threshold < 0:
            raise ValueError("threshold must be non-negative")

        frame_samples = max(1, int(round(sample_rate * (frame_ms / 1000.0))))

        self.frame_ms = float(frame_ms)
        self.sample_rate = int(sample_rate)
        self.threshold = float(threshold)
        self._frame_samples = frame_samples
        self._use_numpy = np is not None
        self._dtype = np.float32 if self._use_numpy else float  # type: ignore[union-attr]

    @property
    def frame_length(self) -> int:
        """Number of samples per full frame."""

        return self._frame_samples

    @property
    def decision_latency_ms(self) -> float:
        """Nominal latency introduced by frame buffering."""

        return self.frame_ms

    def frames(self, pcm: Iterable[float] | Sequence[float]) -> Iterator[Sequence[float]]:
        """Yield consecutive frames from a mono PCM buffer.

        Parameters
        ----------
        pcm:
            One-dimensional NumPy array containing floating-point PCM samples.
            The buffer is not padded; the final frame may contain fewer samples
            than ``frame_length`` when the input does not align to the frame
            size.
        """

        if self._use_numpy:
            samples = _ensure_mono_numpy(pcm, self._dtype)  # type: ignore[arg-type]
            total_samples = int(samples.size)
            if total_samples == 0:
                return

            frame_size = self._frame_samples
            for start in range(0, total_samples, frame_size):
                end = min(start + frame_size, total_samples)
                frame = samples[start:end]
                # Copy to ensure downstream consumers can modify the buffer safely.
                yield frame.copy()
            return

        samples = _ensure_mono_python(pcm)
        total_samples = len(samples)
        if total_samples == 0:
            return

        frame_size = self._frame_samples
        for start in range(0, total_samples, frame_size):
            end = min(start + frame_size, total_samples)
            frame = samples[start:end]
            yield list(frame)

    def is_speech(self, frame: Iterable[float] | Sequence[float]) -> bool:
        """Return ``True`` when the frame's energy exceeds the threshold."""

        if self._use_numpy:
            samples = _ensure_mono_numpy(frame, self._dtype)  # type: ignore[arg-type]
            if samples.size == 0:
                return False

            energy = float(np.mean(samples * samples))
            return energy >= self.threshold

        samples = _ensure_mono_python(frame)
        if not samples:
            return False

        energy = math.fsum(sample * sample for sample in samples) / len(samples)
        return energy >= self.threshold


__all__ = ["EnergyVAD"]

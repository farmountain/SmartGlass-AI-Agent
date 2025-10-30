"""Energy-based voice activity detection utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterator, Sequence, Union

import numpy as np


@dataclass(frozen=True)
class AudioFrame:
    """Container describing a chunk of audio samples.

    Attributes
    ----------
    index:
        Index of the frame within the original stream (0-based).
    start:
        Start sample offset of the frame (inclusive).
    end:
        End sample offset (exclusive) of the frame before padding.
    timestamp_ms:
        Timestamp in milliseconds corresponding to the start of the frame.
    samples:
        A contiguous vector of samples representing the frame. Padding with
        zeros is applied to guarantee that every frame has the same length.
    """

    index: int
    start: int
    end: int
    timestamp_ms: float
    samples: np.ndarray


class EnergyVAD:
    """A lightweight, energy-based voice activity detector.

    The detector slices incoming mono audio buffers into fixed-size frames and
    computes the mean-square energy of each frame. Speech is detected when the
    frame energy exceeds the configured threshold.

    Parameters
    ----------
    frame_ms:
        Frame size in milliseconds. Defaults to 2 ms, which bounds the median
        decision latency to two milliseconds while allowing users to configure
        larger frames when desired.
    sample_rate:
        Sample rate of the incoming audio buffer.
    threshold:
        Energy threshold (mean-square) above which a frame is labelled as
        speech. Typical floating-point PCM ranges from -1.0 to 1.0.
    """

    def __init__(self, *, frame_ms: float = 2.0, sample_rate: int = 16_000, threshold: float = 1e-3) -> None:
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
        self._dtype = np.float32

    @property
    def frame_length(self) -> int:
        """Number of samples per frame."""

        return self._frame_samples

    @property
    def decision_latency_ms(self) -> float:
        """Median decision latency implied by the current frame size."""

        return self.frame_ms

    def frames(self, audio: Union[Sequence[float], np.ndarray], *, pad: bool = True) -> Iterator[AudioFrame]:
        """Yield sequential frames from a mono audio buffer.

        Parameters
        ----------
        audio:
            Sequence or NumPy array containing mono PCM samples. The samples
            are interpreted as floating-point values.
        pad:
            If ``True`` (default), the last frame is zero padded to match the
            configured frame length. Padding keeps energy estimates stable.
        """

        samples = np.asarray(audio, dtype=self._dtype)
        if samples.ndim != 1:
            raise ValueError("EnergyVAD expects 1-D (mono) audio buffers")

        total_samples = int(samples.size)
        if total_samples == 0:
            return

        frame_size = self._frame_samples
        total_frames = math.ceil(total_samples / frame_size)
        for index in range(total_frames):
            start = index * frame_size
            end = min(start + frame_size, total_samples)
            frame = samples[start:end]
            if pad and frame.size < frame_size:
                padded = np.zeros(frame_size, dtype=self._dtype)
                if frame.size:
                    padded[: frame.size] = frame
                frame = padded
            else:
                frame = frame.copy()

            timestamp_ms = (start / self.sample_rate) * 1000.0
            yield AudioFrame(
                index=index,
                start=start,
                end=end,
                timestamp_ms=timestamp_ms,
                samples=frame,
            )

    def is_speech(self, frame: Union[AudioFrame, Sequence[float], np.ndarray]) -> bool:
        """Return ``True`` when the provided frame contains speech."""

        if isinstance(frame, AudioFrame):
            samples = frame.samples
        else:
            samples = np.asarray(frame, dtype=self._dtype)

        if samples.ndim != 1:
            raise ValueError("EnergyVAD expects 1-D frames")
        if samples.size == 0:
            return False

        energy = float(np.dot(samples, samples) / samples.size)
        return energy >= self.threshold


__all__ = ["AudioFrame", "EnergyVAD"]


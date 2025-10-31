"""Confidence-based fusion gate utilities."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

__all__ = [
    "FusionResult",
    "ConfidenceFusion",
]


@dataclass(frozen=True)
class FusionResult:
    """Container describing the outcome of a fusion decision."""

    audio_conf: float
    vision_conf: float
    score: float
    decision: bool
    audio_ms: float
    vision_ms: float
    total_ms: float


class ConfidenceFusion:
    """Blend audio and vision confidence signals with a soft gate."""

    def __init__(
        self,
        *,
        audio_weight: float = 0.45,
        vision_weight: float = 0.55,
        threshold: float = 0.35,
    ) -> None:
        if not 0.0 <= audio_weight <= 1.0:
            raise ValueError("audio_weight must lie within [0, 1]")
        if not 0.0 <= vision_weight <= 1.0:
            raise ValueError("vision_weight must lie within [0, 1]")

        total_weight = audio_weight + vision_weight
        if math.isclose(total_weight, 0.0):
            raise ValueError("audio_weight + vision_weight must be > 0")
        if threshold <= 0.0:
            raise ValueError("threshold must be positive")

        self.audio_weight = audio_weight / total_weight
        self.vision_weight = vision_weight / total_weight
        self.threshold = threshold

    @staticmethod
    def _squash(value: float) -> float:
        """Squash raw scores into the ``[0, 1]`` interval using a sigmoid."""

        return 1.0 / (1.0 + math.exp(-float(value)))

    def evaluate(self, audio_signal: float, vision_signal: float) -> FusionResult:
        """Evaluate the fusion gate for the supplied modality scores."""

        audio_start = time.perf_counter()
        audio_conf = self._squash(audio_signal)
        audio_ms = (time.perf_counter() - audio_start) * 1000.0

        vision_start = time.perf_counter()
        vision_conf = self._squash(vision_signal)
        vision_ms = (time.perf_counter() - vision_start) * 1000.0

        score = self.audio_weight * audio_conf + self.vision_weight * vision_conf
        decision = score >= self.threshold

        return FusionResult(
            audio_conf=audio_conf,
            vision_conf=vision_conf,
            score=score,
            decision=decision,
            audio_ms=audio_ms,
            vision_ms=vision_ms,
            total_ms=audio_ms + vision_ms,
        )

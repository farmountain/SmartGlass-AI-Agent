"""Confidence fusion utilities using a mutual-information inspired gate."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

__all__ = [
    "alpha_from_conf",
    "smooth_alpha",
    "ConfidenceFusion",
]

_LOGGER = logging.getLogger("fusion")
_SIGMOID_LIMIT = 60.0


def _stable_sigmoid(value: float) -> float:
    """Return the logistic sigmoid of ``value`` with overflow protection."""

    value = float(value)
    if value >= 0.0:
        # Clamp the exponent to avoid overflow when ``value`` is large.
        z = math.exp(-min(value, _SIGMOID_LIMIT))
        return 1.0 / (1.0 + z)
    z = math.exp(max(value, -_SIGMOID_LIMIT))
    return z / (1.0 + z)


def alpha_from_conf(conf_v: float, conf_a: float, k: float = 4.0, bias: float = 0.0) -> float:
    """Compute the fusion gate ``alpha`` from vision and audio confidences.

    The gate relies on the relative confidence between the modalities.  A
    positive difference ``(conf_v - conf_a)`` produces an ``alpha`` closer to
    one, favouring the vision stream, while a negative difference favours audio.
    ``k`` controls the steepness of the transition and ``bias`` shifts the
    midpoint.
    """

    scaled = k * (float(conf_v) - float(conf_a)) + float(bias)
    return _stable_sigmoid(scaled)


def smooth_alpha(prev: float, new: float, beta: float = 0.25) -> float:
    """Exponentially smooth ``alpha`` updates while staying within ``[0, 1]``."""

    if not 0.0 <= beta <= 1.0:
        raise ValueError("beta must lie within [0, 1]")

    prev = max(0.0, min(1.0, float(prev)))
    new = max(0.0, min(1.0, float(new)))
    blended = (1.0 - beta) * prev + beta * new
    return max(0.0, min(1.0, blended))


@dataclass
class ConfidenceFusion:
    """Maintain a smoothed ``alpha`` coefficient for cross-modal fusion."""

    beta: float = 0.25
    k: float = 4.0
    bias: float = 0.0
    initial_alpha: float = 0.5
    logger: logging.Logger = field(default_factory=lambda: _LOGGER)

    def __post_init__(self) -> None:
        if not 0.0 <= self.beta <= 1.0:
            raise ValueError("beta must lie within [0, 1]")
        self.alpha_last = max(0.0, min(1.0, float(self.initial_alpha)))
        self.alpha_avg = self.alpha_last
        self._count = 0

    def update(self, conf_v: float, conf_a: float) -> float:
        """Update the smoothed ``alpha`` and log diagnostics."""

        target = alpha_from_conf(conf_v, conf_a, k=self.k, bias=self.bias)
        alpha = smooth_alpha(self.alpha_last, target, beta=self.beta)
        self.alpha_last = alpha

        self._count += 1
        if self._count == 1:
            self.alpha_avg = alpha
        else:
            self.alpha_avg += (alpha - self.alpha_avg) / self._count

        if self.logger:
            self.logger.debug(
                "fusion.alpha_last=%0.6f fusion.alpha_avg=%0.6f",
                self.alpha_last,
                self.alpha_avg,
            )

        return self.alpha_last

"""Confidence-based fusion gate utilities.

The routines in this module implement the Week-4 confidence fusion
specification.  They intentionally avoid importing any heavy runtime
dependencies so that the module can be used in lightweight agents and
unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Optional


def sigmoid(x: float) -> float:
    """Return the logistic sigmoid of *x*.

    The implementation is numerically stable for large magnitude values of
    ``x`` to avoid overflow when the exponent is evaluated.
    """

    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def clip01(value: float) -> float:
    """Clip *value* into the closed unit interval ``[0, 1]``."""

    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


def alpha_from_conf(
    confidence: float,
    *,
    threshold: float = 0.5,
    temperature: float = 0.15,
) -> float:
    """Map a confidence score into a gating weight ``α``.

    Parameters
    ----------
    confidence:
        Raw model confidence, typically in ``[0, 1]``.  Values outside the
        interval are handled gracefully via clipping.
    threshold:
        The mid-point around which the sigmoid is centred.  The default of
        ``0.5`` mirrors the Week-4 fusion spec which balances uncertain
        observations around that level.
    temperature:
        Controls the softness of the gating transition.  Lower values make
        the mapping steeper while still remaining smooth and monotonic.
    """

    conf = clip01(confidence)
    temp = max(temperature, 1e-6)
    centred = (conf - threshold) / temp
    return sigmoid(centred)


def smooth_alpha(previous: float, target: float, smoothing: float) -> float:
    """Smoothly update the gating value toward ``target``.

    ``smoothing`` acts as a step size and is constrained to ``[0, 1]`` so the
    update is a 1-Lipschitz map of the target.  Setting ``smoothing`` to ``1``
    performs an immediate update, while smaller values provide exponential
    smoothing over time.
    """

    prev = clip01(previous)
    tgt = clip01(target)
    step = clip01(smoothing)
    return prev + step * (tgt - prev)


@dataclass
class ConfidenceFusion:
    """Stateful helper that tracks a smoothed, clipped gating weight ``α``.

    The fusion gate follows the Week-4 specification:

    * Convert raw confidence to a target ``α`` via :func:`alpha_from_conf`.
    * Apply an exponential smoothing step controlled by ``smoothing``.
    * Clip results into the closed unit interval to maintain stability.

    Attributes
    ----------
    temperature:
        Softness parameter forwarded to :func:`alpha_from_conf`.
    threshold:
        Mid-point parameter forwarded to :func:`alpha_from_conf`.
    smoothing:
        Exponential smoothing factor in ``[0, 1]`` used by :func:`smooth_alpha`.
    alpha:
        Current gating value.  Public for inspection, but should be mutated
        through :meth:`update` or :meth:`reset` to maintain invariants.
    """

    smoothing: float = 0.2
    temperature: float = 0.15
    threshold: float = 0.5
    alpha: float = 0.0

    def __post_init__(self) -> None:
        self.smoothing = clip01(self.smoothing)
        self.alpha = clip01(self.alpha)

    def target_from_confidence(self, confidence: float) -> float:
        """Compute the instantaneous target ``α`` for *confidence*."""

        return alpha_from_conf(
            confidence,
            threshold=self.threshold,
            temperature=self.temperature,
        )

    def update(self, confidence: float) -> float:
        """Update the gating state using *confidence* and return the result."""

        target = self.target_from_confidence(confidence)
        self.alpha = smooth_alpha(self.alpha, target, self.smoothing)
        return self.alpha

    def reset(self, alpha: Optional[float] = None) -> None:
        """Reset the fusion gate to *alpha* (default 0)."""

        if alpha is None:
            self.alpha = 0.0
        else:
            self.alpha = clip01(alpha)

    def warm_start(self, confidences: Iterable[float]) -> float:
        """Prime the fusion state with a sequence of past confidences."""

        result = self.alpha
        for conf in confidences:
            result = self.update(conf)
        return result

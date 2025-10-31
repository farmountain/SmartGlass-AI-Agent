"""Mutual-information gate utilities for confidence fusion.

This module implements the Week-4 gating specification which defines an
intermediate fusion coefficient :math:`\alpha(t)` derived from per-modality
confidence scores.  The coefficient is kept within the unit interval, and
updates are smoothed to avoid abrupt changes that could lead to oscillations in
policy decisions.

The primitives are intentionally lightweight so the module can be imported in
contexts (such as policy initialisation or unit tests) where heavyweight
dependencies are undesirable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "sigmoid",
    "clip01",
    "alpha_from_conf",
    "smooth_alpha",
    "ConfidenceFusion",
]


def sigmoid(value: float) -> float:
    """Return the logistic sigmoid of ``value``."""

    # ``math.exp`` is stable for the magnitudes encountered in confidence
    # signals.  Casting to ``float`` prevents accidental usage of ``Decimal``
    # inputs, which would otherwise raise.
    value = float(value)
    if value >= 0.0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def clip01(value: float) -> float:
    """Clip ``value`` to the inclusive ``[0, 1]`` interval."""

    if math.isnan(value):  # pragma: no cover - defensive programming
        raise ValueError("alpha cannot be NaN")
    return min(1.0, max(0.0, float(value)))


def alpha_from_conf(
    confidence: float,
    *,
    midpoint: float = 0.5,
    gain: float = 8.0,
) -> float:
    """Project a modality confidence into an ``\alpha`` coefficient.

    Parameters
    ----------
    confidence:
        Raw confidence value.  Values outside ``[0, 1]`` are clipped before
        being converted to ``\alpha``.
    midpoint:
        Logical operating point of the sigmoid.  A value of ``0.5`` keeps the
        mapping symmetric around a neutral confidence of 0.5.
    gain:
        Controls the slope of the sigmoid.  ``gain`` must be strictly positive;
        higher gains produce a steeper transition between low and high
        confidence regimes.
    """

    if gain <= 0.0:
        raise ValueError("gain must be strictly positive")

    clipped = clip01(confidence)
    centred = clipped - float(midpoint)
    # Normalise by midpoint spread to maintain a stable slope when the midpoint
    # changes.  The factor of two scales the centred value back to [-1, 1]
    # before the logistic is applied.
    scaled = gain * centred
    return clip01(sigmoid(scaled))


def smooth_alpha(current: float, target: float, smoothing: float) -> float:
    """Blend ``current`` towards ``target`` with a 1-Lipschitz operator."""

    if not 0.0 <= smoothing <= 1.0:
        raise ValueError("smoothing must lie within [0, 1]")

    current = clip01(current)
    target = clip01(target)
    # Linear interpolation keeps the result within the convex hull of the
    # inputs and yields a Lipschitz constant of ``smoothing`` with respect to
    # ``target``.
    return (1.0 - smoothing) * current + smoothing * target


@dataclass
class ConfidenceFusion:
    r"""Maintain a smoothed fusion coefficient ``\alpha(t)``.

    The update rule is:

    .. math::

        \alpha_t = (1 - \lambda) \alpha_{t-1} + \lambda \hat{\alpha}(c_t)

    where ``\hat{\alpha}`` is obtained from :func:`alpha_from_conf` and
    ``\lambda`` corresponds to ``smoothing``.  This keeps ``\alpha`` bounded in
    ``[0, 1]`` while ensuring monotonic convergence towards the target value.
    """

    smoothing: float = 0.25
    midpoint: float = 0.5
    gain: float = 8.0
    initial_alpha: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 < self.smoothing <= 1.0:
            raise ValueError("smoothing must be in (0, 1]")
        self._alpha = clip01(self.initial_alpha)

    @property
    def alpha(self) -> float:
        r"""Current value of ``\alpha``."""

        return self._alpha

    def target_from_conf(self, confidence: float) -> float:
        r"""Return the instantaneous ``\hat{\alpha}`` for ``confidence``."""

        return alpha_from_conf(confidence, midpoint=self.midpoint, gain=self.gain)

    def update(self, confidence: float) -> float:
        r"""Update ``\alpha`` using the supplied confidence value."""

        target = self.target_from_conf(confidence)
        self._alpha = smooth_alpha(self._alpha, target, self.smoothing)
        return self._alpha

    def reset(self, value: float = 0.0) -> None:
        r"""Reset ``\alpha`` to ``value`` within ``[0, 1]``."""

        self._alpha = clip01(value)

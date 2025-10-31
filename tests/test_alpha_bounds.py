"""Boundary and Lipschitz tests for the fusion gate smoothing operator."""

from __future__ import annotations

import itertools
import random

from src.fusion.gate_mi import alpha_from_conf, smooth_alpha


def test_alpha_from_conf_is_clipped() -> None:
    """alpha_from_conf should remain within the unit interval."""

    test_values = [-5.0, -1.0, 0.0, 0.2, 0.5, 0.9, 1.0, 1.2, 5.0]
    for value in test_values:
        alpha = alpha_from_conf(value)
        assert 0.0 <= alpha <= 1.0


def test_smoothing_is_one_lipschitz() -> None:
    """smooth_alpha must be 1-Lipschitz with respect to the target signal."""

    rng = random.Random(0xC0FFEE)
    current = rng.random()
    smoothing = 0.3

    targets = [rng.random() for _ in range(8)]
    for left, right in itertools.permutations(targets, 2):
        smoothed_left = smooth_alpha(current, left, smoothing)
        smoothed_right = smooth_alpha(current, right, smoothing)
        assert abs(smoothed_left - smoothed_right) <= abs(left - right) + 1e-12

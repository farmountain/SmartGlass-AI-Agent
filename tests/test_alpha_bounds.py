"""Bounds and Lipschitz properties of the smoothing update."""

import itertools

from src.fusion.gate_mi import alpha_from_conf, smooth_alpha


def test_smoothing_respects_unit_interval() -> None:
    smoothing = 0.4
    prev_values = [0.0, 0.25, 0.5, 0.75, 1.0]
    confidences = [i / 10 for i in range(-2, 12)]

    for prev, confidence in itertools.product(prev_values, confidences):
        target = alpha_from_conf(confidence)
        updated = smooth_alpha(prev, target, smoothing)
        assert 0.0 <= updated <= 1.0


def test_smoothing_is_one_lipschitz_in_target() -> None:
    smoothing = 0.3
    prev = 0.4
    conf_pairs = [(0.2, 0.8), (0.0, 1.0), (0.45, 0.55)]

    for c1, c2 in conf_pairs:
        t1 = alpha_from_conf(c1)
        t2 = alpha_from_conf(c2)
        s1 = smooth_alpha(prev, t1, smoothing)
        s2 = smooth_alpha(prev, t2, smoothing)
        assert abs(s1 - s2) <= abs(t1 - t2) + 1e-12

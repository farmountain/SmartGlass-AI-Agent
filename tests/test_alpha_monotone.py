"""Monotonicity tests for the Week-4 fusion gate."""

from __future__ import annotations

from src.fusion.gate_mi import alpha_from_conf


def test_alpha_is_monotone() -> None:
    """alpha_from_conf should be monotonically non-decreasing."""

    confidences = [step / 200.0 for step in range(201)]
    alphas = [alpha_from_conf(conf) for conf in confidences]

    for lower, upper in zip(alphas, alphas[1:]):
        assert lower <= upper + 1e-12

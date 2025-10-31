"""Monotonicity checks for the confidence-to-alpha mapping."""

from src.fusion.gate_mi import alpha_from_conf


def test_alpha_is_monotone_on_unit_grid() -> None:
    confidences = [i / 100 for i in range(0, 101, 2)]
    alphas = [alpha_from_conf(c) for c in confidences]
    for lower, upper in zip(alphas, alphas[1:]):
        assert lower <= upper + 1e-12

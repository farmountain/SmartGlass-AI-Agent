"""Bounds and stability checks for the mutual-information fusion gate."""

from __future__ import annotations

import math

import pytest

from src.fusion.gate_mi import alpha_from_conf, smooth_alpha


@pytest.mark.parametrize(
    "conf_v, conf_a",
    [
        (0.0, 0.0),
        (1.0, 0.0),
        (0.0, 1.0),
        (1.0, 1.0),
        (0.3, 0.9),
    ],
)
def test_alpha_from_conf_is_bounded(conf_v: float, conf_a: float) -> None:
    alpha = alpha_from_conf(conf_v, conf_a)
    assert 0.0 <= alpha <= 1.0


@pytest.mark.parametrize("beta", [0.0, 0.25, 1.0])
def test_smooth_alpha_respects_bounds(beta: float) -> None:
    result = smooth_alpha(0.2, 0.9, beta=beta)
    assert 0.0 <= result <= 1.0


def test_smooth_alpha_invalid_beta() -> None:
    with pytest.raises(ValueError):
        smooth_alpha(0.0, 1.0, beta=-0.1)
    with pytest.raises(ValueError):
        smooth_alpha(0.0, 1.0, beta=1.1)

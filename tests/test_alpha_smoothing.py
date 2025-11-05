"""Behavioural tests for the smoothed fusion controller."""

from __future__ import annotations

import logging

from src.fusion.gate_mi import ConfidenceFusion, alpha_from_conf, smooth_alpha


def test_smooth_alpha_matches_ema() -> None:
    prev = 0.2
    new = 0.8
    beta = 0.25
    expected = (1.0 - beta) * prev + beta * new
    assert smooth_alpha(prev, new, beta=beta) == expected


def test_confidence_fusion_updates_and_logs(caplog) -> None:
    fusion = ConfidenceFusion(beta=0.5, initial_alpha=0.0)

    with caplog.at_level(logging.DEBUG, logger="fusion"):
        alpha1 = fusion.update(0.9, 0.1)
        alpha2 = fusion.update(0.9, 0.1)

    assert 0.0 <= alpha1 <= 1.0
    assert alpha2 >= alpha1
    assert any("fusion.alpha_last" in message for message in caplog.messages)
    assert any("fusion.alpha_avg" in message for message in caplog.messages)


def test_confidence_fusion_uses_bias() -> None:
    higher_bias = alpha_from_conf(0.4, 0.6, bias=1.0)
    lower_bias = alpha_from_conf(0.4, 0.6, bias=-1.0)
    assert higher_bias > lower_bias

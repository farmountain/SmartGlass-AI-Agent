"""Smoothing behaviour for the mutual-information fusion gate."""

from __future__ import annotations

from src.fusion.gate_mi import ConfidenceFusion


def test_alpha_converges_under_updates() -> None:
    """Repeated updates with the same confidence should converge."""

    fusion = ConfidenceFusion(smoothing=0.2, initial_alpha=0.0)
    target_confidence = 0.85

    for _ in range(64):
        alpha = fusion.update(target_confidence)

    target_alpha = fusion.target_from_conf(target_confidence)
    assert abs(alpha - target_alpha) < 1e-3


def test_alpha_updates_remain_bounded() -> None:
    """Ensure the running alpha never leaves the unit interval."""

    fusion = ConfidenceFusion(smoothing=0.5, initial_alpha=0.2)
    confidences = [0.1, 0.4, 0.9, 0.95, 0.6, 0.2]

    for confidence in confidences:
        alpha = fusion.update(confidence)
        assert 0.0 <= alpha <= 1.0

"""Convergence tests for the confidence fusion helper."""

from src.fusion.gate_mi import ConfidenceFusion


def test_updates_converge_to_target() -> None:
    fusion = ConfidenceFusion(smoothing=0.2)
    target = fusion.target_from_confidence(1.0)
    for _ in range(100):
        fusion.update(1.0)
    assert abs(fusion.alpha - target) < 1e-6


def test_reset_restores_initial_state() -> None:
    fusion = ConfidenceFusion(smoothing=0.3)
    fusion.update(1.0)
    fusion.reset()
    assert fusion.alpha == 0.0
    fusion.reset(0.75)
    assert fusion.alpha == 0.75

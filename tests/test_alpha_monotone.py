"""Monotonicity properties for the mutual-information fusion gate."""

from __future__ import annotations

from src.fusion.gate_mi import alpha_from_conf


def test_alpha_increases_with_vision_confidence() -> None:
    conf_a = 0.25
    samples = [alpha_from_conf(conf_v, conf_a) for conf_v in (0.0, 0.5, 1.0)]
    assert samples[0] < samples[1] < samples[2]


def test_alpha_decreases_with_audio_confidence() -> None:
    conf_v = 0.75
    samples = [alpha_from_conf(conf_v, conf_a) for conf_a in (0.0, 0.5, 1.0)]
    assert samples[0] > samples[1] > samples[2]

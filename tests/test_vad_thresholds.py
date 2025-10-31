from pathlib import Path

import numpy as np
import pytest

import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from audio.vad import EnergyVAD


def test_energy_threshold_behavior():
    vad = EnergyVAD(threshold=1e-3)

    quiet_frame = np.zeros(vad.frame_length, dtype=np.float32)
    assert not vad.is_speech(quiet_frame)

    energetic_frame = np.full(vad.frame_length, 0.2, dtype=np.float32)
    assert vad.is_speech(energetic_frame)


def test_is_speech_accepts_iterables():
    vad = EnergyVAD(threshold=1e-4)
    samples = [0.02] * vad.frame_length
    assert vad.is_speech(samples)


def test_latency_budget_determined_by_frame_duration():
    vad = EnergyVAD(frame_ms=12.5, sample_rate=16_000)
    assert vad.decision_latency_ms == pytest.approx(12.5)
    assert vad.frame_length == round(16_000 * 12.5 / 1000)

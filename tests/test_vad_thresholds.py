from pathlib import Path
import statistics
import sys
import time

import numpy as np
import pytest

project_src = Path(__file__).resolve().parents[1] / "src"
sys.path.append(str(project_src))

from perception.vad import EnergyVAD


@pytest.mark.parametrize(
    ("threshold", "amplitude", "expected"),
    [
        (1e-5, 0.0, False),
        (1e-5, 0.02, True),
        (1e-3, 0.02, False),
        (1e-3, 0.1, True),
    ],
)
def test_energy_threshold_behavior(threshold: float, amplitude: float, expected: bool):
    vad = EnergyVAD(threshold=threshold)
    frame = np.full(vad.frame_length, amplitude, dtype=np.float32)
    assert vad.is_speech(frame) is expected


def test_is_speech_accepts_iterables():
    vad = EnergyVAD(threshold=1e-4)
    samples = [0.02] * vad.frame_length
    assert vad.is_speech(samples)


def test_latency_budget_determined_by_frame_duration():
    vad = EnergyVAD(frame_ms=12.5, sample_rate=16_000)
    assert vad.decision_latency_ms == pytest.approx(12.5)
    assert vad.frame_length == round(16_000 * 12.5 / 1000)


def test_is_speech_latency_median_below_two_milliseconds():
    vad = EnergyVAD()
    frame = np.zeros(vad.frame_length, dtype=np.float32)

    timings = []
    for _ in range(200):
        start = time.perf_counter()
        vad.is_speech(frame)
        timings.append(time.perf_counter() - start)

    median_latency = statistics.median(timings)
    assert median_latency <= 0.002 + 0.005, (
        f"median latency {median_latency * 1_000:.3f} ms exceeds 2 ms with 5 ms slack"
    )

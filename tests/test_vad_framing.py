from pathlib import Path
import sys

import numpy as np

project_src = Path(__file__).resolve().parents[1] / "src"
sys.path.append(str(project_src))

from perception.vad import EnergyVAD


def test_frames_produce_expected_counts_for_one_second():
    vad = EnergyVAD(frame_ms=20.0, sample_rate=16_000)
    samples = np.zeros(16_000, dtype=np.float32)

    frames = list(vad.frames(samples))

    assert len(frames) == 50

    hop = vad.frame_length
    assert all(frame.shape[0] <= hop for frame in frames)
    assert frames[-1].shape[0] <= hop
    assert all(frame.dtype == np.float32 for frame in frames)

    reconstructed = np.concatenate(frames)
    np.testing.assert_array_equal(reconstructed, samples)

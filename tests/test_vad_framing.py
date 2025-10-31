from pathlib import Path

import numpy as np

import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from audio.vad import EnergyVAD


def test_frames_produce_expected_lengths_without_padding():
    vad = EnergyVAD(frame_ms=10.0, sample_rate=16_000)
    samples = np.arange(0, 400, dtype=np.float32)

    frames = list(vad.frames(samples))

    assert len(frames) == 3  # ceil(400 / 160)

    frame_lengths = [frame.shape[0] for frame in frames]
    assert frame_lengths == [vad.frame_length, vad.frame_length, 80]
    assert all(frame.dtype == np.float32 for frame in frames)

    # Reassemble the frames to confirm no padding was introduced.
    reconstructed = np.concatenate(frames)
    assert np.array_equal(reconstructed, samples)

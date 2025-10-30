from pathlib import Path

import numpy as np

import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from audio.vad import EnergyVAD


def test_frames_produce_expected_counts_and_offsets():
    vad = EnergyVAD(frame_ms=2.0, sample_rate=16_000)
    samples = np.arange(0, 160, dtype=np.float32)

    frames = list(vad.frames(samples))

    assert len(frames) == 5  # ceil(160 / 32)
    for frame in frames:
        assert frame.samples.shape == (vad.frame_length,)
        assert frame.samples.dtype == np.float32

    # Ensure timestamps advance in 2 ms increments.
    expected_increment = vad.frame_ms
    timestamps = [frame.timestamp_ms for frame in frames]
    differences = np.diff(timestamps)
    assert np.allclose(differences, expected_increment)

    # Verify sample offsets for the final frame, including padding behaviour.
    last_frame = frames[-1]
    assert last_frame.start == 128
    assert last_frame.end == 160
    assert np.allclose(last_frame.samples[: last_frame.end - last_frame.start], samples[last_frame.start : last_frame.end])
    assert np.count_nonzero(last_frame.samples[last_frame.end - last_frame.start :]) == 0

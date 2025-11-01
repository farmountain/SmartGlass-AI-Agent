from pathlib import Path
import sys

import numpy as np

project_src = Path(__file__).resolve().parents[1] / "src"
if str(project_src) not in sys.path:
    sys.path.append(str(project_src))

from drivers.providers.mock import MockProvider  # noqa: E402
from perception.vad import frames_from_mic  # noqa: E402


def test_frames_from_mic_provide_20ms_windows():
    provider = MockProvider()
    frames = list(frames_from_mic(provider.microphone, seconds=1.0))

    assert len(frames) == 50

    frame_lengths = {len(frame) for frame in frames}
    assert frame_lengths == {320}

    assert sum(len(frame) for frame in frames) == 16_000
    assert all(isinstance(frame, np.ndarray) for frame in frames)
    assert all(frame.dtype == np.float32 for frame in frames)

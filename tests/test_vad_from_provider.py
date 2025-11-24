from pathlib import Path
import sys

import numpy as np
import pytest

project_src = Path(__file__).resolve().parents[1] / "src"
if str(project_src) not in sys.path:
    sys.path.append(str(project_src))

from drivers.providers.meta import MetaRayBanProvider  # noqa: E402
from drivers.providers.mock import MockProvider  # noqa: E402
from perception.vad import frames_from_mic  # noqa: E402


PROVIDER_FACTORIES = (
    pytest.param(MockProvider, id="mock-provider"),
    pytest.param(lambda: MetaRayBanProvider(prefer_sdk=False), id="meta-mock-provider"),
)


def _mic_adapter(mic):
    class _MicWrapper:
        def __init__(self, inner):
            self._inner = inner

        def get_frames(self):
            for chunk in self._inner.get_frames():
                if isinstance(chunk, dict) and "pcm" in chunk:
                    yield chunk["pcm"].squeeze()
                else:
                    yield chunk

    return _MicWrapper(mic)


@pytest.mark.parametrize("provider_factory", PROVIDER_FACTORIES)
def test_frames_from_mic_provide_20ms_windows(provider_factory):
    provider = provider_factory()
    mic = provider.open_audio_stream()
    assert mic is not None
    frames = list(frames_from_mic(_mic_adapter(mic), seconds=1.0))

    assert len(frames) == 50

    frame_lengths = {len(frame) for frame in frames}
    assert frame_lengths == {320}

    assert sum(len(frame) for frame in frames) == 16_000
    assert all(isinstance(frame, np.ndarray) for frame in frames)
    assert all(frame.dtype == np.float32 for frame in frames)

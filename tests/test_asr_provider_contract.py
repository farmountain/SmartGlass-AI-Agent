"""Integration contract for provider-backed ASR streaming."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

project_src = Path(__file__).resolve().parents[1] / "src"
if str(project_src) not in sys.path:
    sys.path.append(str(project_src))

from drivers.providers.mock import MockProvider  # noqa: E402
from perception.vad import frames_from_mic  # noqa: E402
from perception.asr_stream import ASRStream  # noqa: E402


def test_run_with_provider_matches_manual_frames() -> None:
    manual_provider = MockProvider()
    manual_mic = manual_provider.open_audio_stream()
    assert manual_mic is not None
    manual_frames = list(frames_from_mic(manual_mic, seconds=1.0))

    manual_stream = ASRStream(
        stability_delta=0.1,
        stability_consecutive=2,
        frame_duration_ms=20.0,
    )
    manual_events = list(manual_stream.run(iter(manual_frames)))

    provider = SimpleNamespace(mic=MockProvider().open_audio_stream())
    provider_stream = ASRStream(
        stability_delta=0.1,
        stability_consecutive=2,
        frame_duration_ms=20.0,
    )
    provider_events = list(provider_stream.run_with_provider(provider, seconds=1.0))

    assert manual_events, "expected the manual stream to emit ASR events"
    assert provider_events == manual_events

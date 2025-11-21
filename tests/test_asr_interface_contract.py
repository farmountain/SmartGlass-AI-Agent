from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio.asr_stream import ASRStream, MockASR
from src.perception.asr_stream import WhisperASRStream


def collect_by_final_flag(events, *, is_final):
    return [event for event in events if bool(event.get("is_final")) == is_final]


def _scripted_mock_asr():
    """Return a mock stream with deterministic timestamps and rollouts."""

    timeline = [
        {"text": "alpha", "timestamp": (0.0, 0.5)},
        {"text": "alpha beta", "timestamp": (0.0, 1.0)},
        {"text": "alpha beta gam", "timestamp": (0.0, 1.5)},
        {"text": "alpha beta gamma", "timestamp": (0.0, 2.0)},
        {"text": "alpha beta gamma", "timestamp": (0.0, 2.5)},
    ]
    return timeline, MockASR(timeline)


def _build_stub_whisper_stream(monkeypatch: pytest.MonkeyPatch) -> WhisperASRStream:
    """Create a ``WhisperASRStream`` backed by a lightweight fake model."""

    scripted_tokens = iter(
        [
            (["alpha"], 0.25),
            (["alpha", "beta"], 0.55),
            (["alpha", "beta", "gamma"], 0.95),
        ]
    )

    class _StubModel:
        def transcribe(self, *_args, **_kwargs):
            tokens, timestamp = next(scripted_tokens, ([], 0.0))
            words = [{"word": token, "end": timestamp} for token in tokens]
            return {"segments": [{"words": words}]}

    stub_whisper = SimpleNamespace(load_model=lambda *_args, **_kwargs: _StubModel())
    monkeypatch.setitem(sys.modules, "whisper", stub_whisper)

    stream = WhisperASRStream(
        model_name="tiny-stub",
        stability_window=0.2,
        window_duration=1.0,
    )

    def _stub_transcribe_window(self):
        tokens, timestamp = next(scripted_tokens, ([], self._current_time))
        return list(tokens), float(timestamp)

    monkeypatch.setattr(stream, "_transcribe_window", _stub_transcribe_window.__get__(stream))
    return stream


def _assert_timestamp_matches(actual_timestamp, expected_timestamp):
    if isinstance(expected_timestamp, tuple):
        assert actual_timestamp == expected_timestamp
    else:
        assert pytest.approx(actual_timestamp) == pytest.approx(expected_timestamp)


@pytest.mark.parametrize("use_whisper", [False, True])
def test_asr_stream_emits_partial_and_final_sequences(monkeypatch: pytest.MonkeyPatch, use_whisper: bool):
    monkeypatch.delenv("SMARTGLASS_USE_WHISPER", raising=False)
    monkeypatch.delenv("USE_WHISPER_STREAMING", raising=False)

    if use_whisper:
        monkeypatch.setenv("SMARTGLASS_USE_WHISPER", "1")
        monkeypatch.setenv("USE_WHISPER_STREAMING", "1")
        stream = _build_stub_whisper_stream(monkeypatch)
        audio_frames = ([0.0] * 400 for _ in range(4))
        events = list(stream.run(iter(audio_frames)))

        assert events, "expected the Whisper ASR stream to emit events"
        for event in events:
            assert set(event) == {"text", "timestamp", "is_final"}
            assert isinstance(event["text"], str)
            assert isinstance(event["timestamp"], float)
            assert isinstance(event["is_final"], bool)

        partial_events = collect_by_final_flag(events, is_final=False)
        final_events = collect_by_final_flag(events, is_final=True)

        assert partial_events, "expected Whisper to emit partial hypotheses"
        assert final_events, "expected Whisper to emit finalized hypotheses"
        assert final_events[-1]["text"] == "alpha beta gamma"
        assert final_events[-1]["timestamp"] >= 0.0
    else:
        scripted_partials, mock_asr = _scripted_mock_asr()
        stream = ASRStream(asr=mock_asr, stability_window=3, stability_delta=0.34)

        events = list(stream.run())
        assert events, "expected the ASR stream to emit events"

        first_event = events[0]
        assert first_event["text"] == scripted_partials[0]["text"]
        assert first_event["is_final"] is False
        assert pytest.approx(first_event["t_ms"]) == scripted_partials[0]["timestamp"][1] * 1000.0
        assert first_event["t_first_ms"] == first_event["t_ms"]

        partial_events = collect_by_final_flag(events, is_final=False)
        final_events = collect_by_final_flag(events, is_final=True)

        assert [event["text"] for event in partial_events] == [p["text"] for p in scripted_partials]
        assert [event["timestamp"] for event in partial_events] == [p["timestamp"] for p in scripted_partials]

        assert final_events, "expected at least one finalized hypothesis"

        first_final_index = next(i for i, event in enumerate(events) if event["is_final"])
        assert sum(not event["is_final"] for event in events[:first_final_index]) >= 3

        scripted_ms = [partial["timestamp"][1] * 1000.0 for partial in scripted_partials]
        for event, expected_ms in zip(partial_events, scripted_ms):
            assert pytest.approx(event["t_ms"]) == expected_ms
            assert event["t_first_ms"] == first_event["t_first_ms"]

        for final_event in final_events:
            assert final_event["t_first_ms"] == first_event["t_first_ms"]

        assert final_events[-1]["text"] == scripted_partials[-1]["text"]
        _assert_timestamp_matches(
            final_events[-1]["timestamp"], scripted_partials[-1]["timestamp"]
        )

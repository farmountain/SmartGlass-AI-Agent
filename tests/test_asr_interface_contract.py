from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio.asr_stream import ASRStream, MockASR


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


def test_asr_stream_emits_partial_and_final_sequences():
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
    assert final_events[-1]["timestamp"] == scripted_partials[-1]["timestamp"]

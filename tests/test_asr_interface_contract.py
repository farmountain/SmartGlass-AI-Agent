import itertools
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio import ASRStream, MockASR


def collect_by_final_flag(events, *, is_final):
    return [event for event in events if bool(event.get("is_final")) == is_final]


def test_asr_stream_emits_partial_and_final_sequences():
    partials = [
        {"text": "hello", "timestamp": (0.0, 0.4)},
        {"text": "hello world", "timestamp": (0.0, 0.8)},
        {"text": "hello world", "timestamp": (0.0, 1.2)},
        {"text": "hello world again", "timestamp": (0.0, 1.6)},
        {"text": "hello world again", "timestamp": (0.0, 2.0)},
    ]

    mock_asr = MockASR(partials)
    stream = ASRStream(asr=mock_asr, stability_window=3, stability_delta=0.34)

    events = list(stream.run())
    partial_events = collect_by_final_flag(events, is_final=False)
    final_events = collect_by_final_flag(events, is_final=True)

    assert [event["text"] for event in partial_events] == [p["text"] for p in partials]
    assert [event["timestamp"] for event in partial_events] == [p["timestamp"] for p in partials]

    assert all("t_ms" in event and "t_first_ms" in event for event in events)
    first_ms = events[0]["t_ms"] if events else 0.0
    assert all(abs(event["t_first_ms"] - first_ms) < 1e-9 for event in events)

    assert final_events, "expected at least one finalized hypothesis"
    final_texts = [event["text"] for event in final_events]
    assert final_texts[-1] == "hello world again"

    for previous, current in itertools.pairwise(final_events):
        assert previous["stability"] <= current["stability"] + 1e-9
        assert current["text"].startswith(previous["text"].strip())

    assert final_events[-1]["timestamp"] == partials[-1]["timestamp"]

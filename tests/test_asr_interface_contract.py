import itertools
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio import ASRStream, MockASR


def collect_types(events, event_type):
    return [event for event in events if event["type"] == event_type]


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
    partial_events = collect_types(events, "partial")
    final_events = collect_types(events, "final")

    assert [event["text"] for event in partial_events] == [p["text"] for p in partials]
    assert [event["timestamp"] for event in partial_events] == [p["timestamp"] for p in partials]

    assert final_events, "expected at least one finalized hypothesis"
    final_texts = [event["text"] for event in final_events]
    assert final_texts[-1] == "hello world again"

    for previous, current in itertools.pairwise(final_events):
        assert previous["stability"] <= current["stability"] + 1e-9
        assert current["text"].startswith(previous["text"].strip())

    assert final_events[-1]["timestamp"] == partials[-1]["timestamp"]

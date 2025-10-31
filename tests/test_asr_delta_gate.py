from pathlib import Path
import sys
from typing import Iterable

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio.asr_stream import ASRStream, MockASR


def rollback_ratio(transcripts: Iterable[str]) -> float:
    previous = ""
    rollback_chars = 0
    total = 0
    for text in transcripts:
        total += 1
        if len(text) < len(previous):
            rollback_chars += len(previous) - len(text)
        previous = text
    return rollback_chars / total if total else 0.0


def test_delta_gate_reduces_reversals():
    scripted_partials = [
        {"text": "call", "timestamp": (0.0, 0.2)},
        {"text": "calling", "timestamp": (0.0, 0.4)},
        {"text": "calli", "timestamp": (0.0, 0.6)},
        {"text": "calling", "timestamp": (0.0, 0.8)},
        {"text": "calling back", "timestamp": (0.0, 1.0)},
        {"text": "calling ba", "timestamp": (0.0, 1.2)},
        {"text": "calling back soon", "timestamp": (0.0, 1.4)},
        {"text": "calling back soon", "timestamp": (0.0, 1.6)},
    ]

    naive_ratio = rollback_ratio(partial["text"] for partial in scripted_partials)
    assert naive_ratio > 0.0

    stream = ASRStream(asr=MockASR(scripted_partials), stability_window=3, stability_delta=0.3)
    events = list(stream.run())
    finals = [event for event in events if event.get("is_final")]

    assert finals, "expected the δ gate to emit finalized transcripts"
    assert finals[-1]["text"] == scripted_partials[-1]["text"]
    assert finals[-1]["timestamp"] == scripted_partials[-1]["timestamp"]

    gated_ratio = rollback_ratio(event["text"] for event in finals)

    reduction = (naive_ratio - gated_ratio) / naive_ratio if naive_ratio else 0.0
    assert reduction >= 0.40
    assert pytest.approx(finals[-1]["t_ms"]) == scripted_partials[-1]["timestamp"][1] * 1000.0

from pathlib import Path
import sys
from typing import Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio import ASRStream, MockASR


def count_reversals(transcripts: Iterable[str]) -> int:
    previous_tokens: List[str] = []
    reversals = 0
    for text in transcripts:
        tokens = text.split()
        prefix_len = 0
        for before, after in zip(previous_tokens, tokens):
            if before == after:
                prefix_len += 1
            else:
                break
        if prefix_len < len(previous_tokens) and previous_tokens:
            reversals += 1
        previous_tokens = tokens
    return reversals


def test_delta_gate_reduces_reversals():
    noisy_partials = [
        {"text": "the quick", "timestamp": (0.0, 0.2)},
        {"text": "the quick brown", "timestamp": (0.0, 0.4)},
        {"text": "the quick brwn", "timestamp": (0.0, 0.6)},
        {"text": "the quick brown", "timestamp": (0.0, 0.8)},
        {"text": "the quick brown fox", "timestamp": (0.0, 1.0)},
        {"text": "the quick brown fx", "timestamp": (0.0, 1.2)},
        {"text": "the quick brown fox", "timestamp": (0.0, 1.4)},
    ]

    naive_reversals = count_reversals(partial["text"] for partial in noisy_partials)
    stream = ASRStream(asr=MockASR(noisy_partials), stability_window=3, stability_delta=0.4)

    finals = [event["text"] for event in stream.run() if event.get("is_final")]
    gated_reversals = count_reversals(finals)

    assert naive_reversals > 0
    assert gated_reversals == 0
    assert finals[-1] == "the quick brown fox"

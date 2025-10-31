import importlib.util
import pathlib

import pytest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[2] / "src" / "perception" / "asr_stream.py"
SPEC = importlib.util.spec_from_file_location("tests.perception.asr_stream", MODULE_PATH)
assert SPEC and SPEC.loader
asr_stream = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(asr_stream)

ASRStream = asr_stream.ASRStream
MockASR = asr_stream.MockASR


def test_stream_emits_partial_transcripts_and_finalization():
    backend = MockASR(token_prefix="w")
    stream = ASRStream(
        asr_backend=backend,
        stability_delta=0.1,
        stability_consecutive=2,
        frame_duration_ms=50.0,
    )

    frames = [b"hello", b"world", b"", b""]
    outputs = list(stream.run(iter(frames)))

    expected_texts = [
        "w:hello",
        "w:hello w:world",
        "w:hello w:world",
        "w:hello w:world",
    ]
    assert [out["text"] for out in outputs] == expected_texts
    assert [out["is_final"] for out in outputs] == [False, False, False, True]
    assert all(out["t_first_ms"] == 0.0 for out in outputs)
    assert [out["t_ms"] for out in outputs] == [50.0, 100.0, 150.0, 200.0]


def test_stream_stability_resets_when_tokens_change():
    backend = MockASR(token_prefix="w")
    stream = ASRStream(
        asr_backend=backend,
        stability_delta=0.1,
        stability_consecutive=2,
        frame_duration_ms=30.0,
    )

    frames = [b"hello", b"", b"world"]
    outputs = list(stream.run(iter(frames)))

    assert len(outputs) == 3
    assert outputs[-1]["text"].endswith("w:world")
    assert outputs[-1]["is_final"] is False


def test_stream_stops_after_final_result():
    backend = MockASR(token_prefix="w")
    stream = ASRStream(
        asr_backend=backend,
        stability_delta=0.1,
        stability_consecutive=2,
        frame_duration_ms=25.0,
    )

    frames = [b"alpha", b"", b"", b"beta"]
    consumed = []

    def frame_generator():
        for frame in frames:
            consumed.append(frame)
            yield frame

    outputs = list(stream.run(frame_generator()))

    assert len(outputs) == 3
    assert outputs[-1]["is_final"] is True
    assert outputs[-1]["text"] == "w:alpha"
    assert consumed == frames[:3]

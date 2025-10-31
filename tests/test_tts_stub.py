import json
from pathlib import Path

import pytest

from src.io import CHARS_PER_SECOND
from src.io.tts import speak


@pytest.mark.usefixtures("tmp_path")
def test_tts_stub_emits_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("SMARTGLASS_ARTIFACTS_DIR", str(tmp_path))

    text = "Hello TTS"
    result = speak(text)

    expected_duration = len(text) / CHARS_PER_SECOND
    assert result.char_count == len(text)
    assert result.duration == pytest.approx(expected_duration)
    assert result.sample_rate == 22050
    assert result.sample_count == int(round(expected_duration * result.sample_rate))

    metrics_dir = Path(tmp_path)
    csv_path = metrics_dir / "metrics.csv"
    jsonl_path = metrics_dir / "metrics.jsonl"

    assert csv_path.exists()
    assert jsonl_path.exists()

    with jsonl_path.open("r", encoding="utf-8") as fp:
        payloads = [json.loads(line) for line in fp if line.strip()]

    metrics = {entry["metric"]: entry for entry in payloads}
    assert metrics["tts.char_count"]["value"] == len(text)
    assert metrics["tts.ms"]["unit"] == "ms"
    assert metrics["tts.ms"]["value"] == pytest.approx(expected_duration * 1000.0)

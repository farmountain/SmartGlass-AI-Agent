from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from privacy.redact import DeterministicRedactor, RedactionSummary
from src.smartglass_agent import SmartGlassAgent


class DummyAudioProcessor:
    def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - trivial stub
        pass

    def transcribe_audio(self, *args, **kwargs) -> dict[str, str]:
        return {"text": "dummy"}

    def get_model_info(self) -> dict[str, str]:  # pragma: no cover - unused in tests
        return {}


class DummyVisionProcessor:
    def __init__(self, *args, **kwargs) -> None:
        self.last_image = None

    def understand_image(self, image, custom_queries):  # pragma: no cover - unused
        self.last_image = image
        return {"description": "understood"}

    def describe_scene(self, image):
        self.last_image = image
        return "scene"

    def classify_image(self, image, possible_objects):  # pragma: no cover - unused
        self.last_image = image
        return possible_objects[0]

    def get_model_info(self) -> dict[str, str]:  # pragma: no cover - unused in tests
        return {}


class DummyTextGenerator:
    def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - trivial stub
        pass

    def generate_smart_response(self, *args, **kwargs) -> str:
        return "response"

    def get_model_info(self) -> dict[str, str]:  # pragma: no cover - unused
        return {}


class SpyRedactor(DeterministicRedactor):
    def __init__(self, redacted_value: int) -> None:
        super().__init__()
        self.calls: list[np.ndarray] = []
        self._redacted_value = redacted_value

    def __call__(self, image):  # type: ignore[override]
        array = np.array(image)
        self.calls.append(array)
        redacted = np.full_like(array, self._redacted_value)
        return redacted, RedactionSummary(faces_masked=1, plates_masked=1)


@pytest.fixture(autouse=True)
def patch_processors(monkeypatch):
    monkeypatch.setattr("src.smartglass_agent.WhisperAudioProcessor", DummyAudioProcessor)
    monkeypatch.setattr("src.smartglass_agent.CLIPVisionProcessor", DummyVisionProcessor)
    monkeypatch.setattr("src.smartglass_agent.LegacyTextGenerator", DummyTextGenerator)


def test_cloud_branch_applies_redaction_before_cloud(monkeypatch, caplog):
    spy = SpyRedactor(redacted_value=7)
    agent = SmartGlassAgent(redactor=spy)
    image = np.ones((4, 4, 3), dtype=np.uint8) * 3

    caplog.set_level("INFO")
    result = agent.process_multimodal_query(image_input=image, text_query="hello", cloud_offload=True)

    assert len(spy.calls) == 1
    # Vision processor must receive the redacted imagery, not the original input.
    assert np.all(agent.vision_processor.last_image == 7)
    assert result["redaction"] == {"faces_masked": 1, "plates_masked": 1}
    assert "Redaction applied before cloud processing" in caplog.text


def test_local_branch_bypasses_redaction(monkeypatch, caplog):
    spy = SpyRedactor(redacted_value=5)
    agent = SmartGlassAgent(redactor=spy)
    image = np.ones((4, 4, 3), dtype=np.uint8) * 9

    caplog.set_level("INFO")
    result = agent.process_multimodal_query(image_input=image, text_query="hello", cloud_offload=False)

    assert spy.calls == []
    assert np.all(agent.vision_processor.last_image == image)
    assert "redaction" not in result
    assert "Processing image locally without redaction" in caplog.text

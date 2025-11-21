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
        masked_area = int(array.shape[0] * array.shape[1]) if array.size else 0
        return redacted, RedactionSummary(
            faces_masked=1, plates_masked=1, total_masked_area=masked_area
        )


@pytest.fixture(autouse=True)
def patch_processors(monkeypatch):
    monkeypatch.setattr("src.smartglass_agent.WhisperAudioProcessor", DummyAudioProcessor)
    monkeypatch.setattr("src.smartglass_agent.CLIPVisionProcessor", DummyVisionProcessor)
    monkeypatch.setattr("src.smartglass_agent.GPT2TextGenerator", DummyTextGenerator)


def test_cloud_branch_applies_redaction_before_cloud(monkeypatch, caplog):
    spy = SpyRedactor(redacted_value=7)
    agent = SmartGlassAgent(redactor=spy)
    image = np.ones((4, 4, 3), dtype=np.uint8) * 3

    caplog.set_level("INFO")
    result = agent.process_multimodal_query(image_input=image, text_query="hello", cloud_offload=True)

    assert len(spy.calls) == 1
    # Vision processor must receive the redacted imagery, not the original input.
    assert np.all(agent.vision_processor.last_image == 7)
    assert result["redaction"] == {
        "faces_masked": 1,
        "plates_masked": 1,
        "total_masked_area": 16,
    }
    assert result["metadata"]["redaction_summary"] == result["redaction"]
    assert result["metadata"]["cloud_offload"] is True
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
    assert result["metadata"]["cloud_offload"] is False
    assert "Processing image locally without redaction" in caplog.text


def test_detected_faces_are_masked(monkeypatch):
    dummy_face_locations = [(1, 4, 4, 1)]

    class DummyFaceRecognition:
        @staticmethod
        def face_locations(image):  # pragma: no cover - trivial pass-through
            return dummy_face_locations

    monkeypatch.setattr("privacy.redact.face_recognition", DummyFaceRecognition)

    image = np.ones((6, 6, 3), dtype=np.uint8) * 127
    redactor = DeterministicRedactor(
        face_padding_ratio=0.0,
        enable_plate_detection=False,
        plate_mask_size=1,
        mask_width=1,
        mask_height=1,
    )

    redacted, summary = redactor(image)

    assert summary == RedactionSummary(
        faces_masked=1, plates_masked=1, total_masked_area=10
    )
    assert np.all(redacted[1:4, 1:4] == 0)
    assert np.all(redacted[-1, -1, ...] == 255)


def test_fallback_masks_respect_configurable_sizes(monkeypatch):
    monkeypatch.setattr("privacy.redact.face_recognition", None)
    monkeypatch.setattr("privacy.redact.mediapipe", None)
    monkeypatch.setattr("privacy.redact.pytesseract", None)

    image = np.ones((4, 8, 3), dtype=np.uint8) * 200
    redactor = DeterministicRedactor(mask_width=0.5, mask_height=0.25)

    redacted, summary = redactor(image)

    assert summary == RedactionSummary(
        faces_masked=1, plates_masked=1, total_masked_area=8
    )
    # Face mask (top-left) should be 1 row by 4 columns of zeros.
    assert np.all(redacted[0, 0:4] == 0)
    # Plate mask (bottom-right) should be 1 row by 4 columns of 255s.
    assert np.all(redacted[-1, -4:] == 255)

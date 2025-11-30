from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest


class DummyAudioProcessor:
    def __init__(self, *_, **__):
        self.calls = []

    def transcribe_audio(self, audio_path=None, audio_array=None, language=None):
        self.calls.append({"audio_path": audio_path, "audio_array": audio_array, "language": language})
        return {"text": "stubbed transcription"}


class DummyVisionProcessor:
    def __init__(self, *_, **__):
        self.describe_calls = []

    def describe_scene(self, image):
        self.describe_calls.append(image)
        return "vision context from dummy"


class DummyRedactionSummary:
    def __init__(self):
        self.faces_masked = 0
        self.plates_masked = 0

    def as_dict(self):
        return {"faces_masked": self.faces_masked, "plates_masked": self.plates_masked}


class DummyRedactor:
    def __init__(self, *_, **__):
        pass

    def __call__(self, image):
        return image, DummyRedactionSummary()


class DummyLLMBackend:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls: list[dict[str, object]] = []

    def generate(self, prompt: str, *, max_tokens: int = 128, system_prompt: str | None = None):
        self.calls.append({"prompt": prompt, "max_tokens": max_tokens, "system_prompt": system_prompt})
        return self.response_text


@pytest.fixture()
def smartglass_agent_cls(monkeypatch):
    sys.modules.setdefault("whisper", types.SimpleNamespace(load_model=lambda *args, **kwargs: None))
    sys.modules.setdefault("torch", types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)))
    sys.modules.setdefault("transformers", types.SimpleNamespace(CLIPProcessor=object, CLIPModel=object))
    sys.modules.setdefault("soundfile", types.SimpleNamespace(read=lambda *args, **kwargs: None, write=lambda *args, **kwargs: None))
    sys.modules.setdefault("numpy", types.SimpleNamespace(ndarray=object, array=lambda *args, **kwargs: None))

    pil_module = types.ModuleType("PIL")
    pil_image = types.ModuleType("PIL.Image")
    pil_image.Image = object
    pil_module.Image = pil_image
    sys.modules.setdefault("PIL", pil_module)
    sys.modules.setdefault("PIL.Image", pil_image)

    module = importlib.import_module("src.smartglass_agent")

    monkeypatch.setattr(module, "WhisperAudioProcessor", DummyAudioProcessor)
    monkeypatch.setattr(module, "CLIPVisionProcessor", DummyVisionProcessor)
    monkeypatch.setattr(module, "DeterministicRedactor", DummyRedactor)

    return module.SmartGlassAgent


@pytest.fixture()
def ray_skill_signals():
    return [
        {"type": "skill_invocation", "skill_id": "skill_002", "payload": {"detected": "exit sign"}},
    ]


def test_textual_query_emits_navigation_action(monkeypatch, smartglass_agent_cls):
    backend = DummyLLMBackend(
        "Preparing navigation instructions. ```json {\"type\": \"navigate\", \"skill_id\": \"skill_001\"} ```"
    )
    agent = smartglass_agent_cls(llm_backend=backend)

    result = agent.process_multimodal_query(text_query="Navigate to the nearest exit")

    navigation_action = next(
        action
        for action in result["actions"]
        if action.get("skill_id") == "skill_001" and action.get("type") == "navigate"
    )
    assert navigation_action["source"] == "llm_json"


def test_image_query_preserves_runtime_skill_action(monkeypatch, smartglass_agent_cls, ray_skill_signals):
    backend = DummyLLMBackend(
        "Reading the sign now. ```json [{\"type\": \"skill_invocation\", \"skill_id\": \"skill_002\"}] ```"
    )
    agent = smartglass_agent_cls(llm_backend=backend)

    image_candidates = [
        Path("images/sample.jpg"),
        Path("images/sample.png"),
        Path("tests/fixtures/sample.jpg"),
        Path("tests/fixtures/sample.png"),
    ]
    image_input = next((path for path in image_candidates if path.exists()), [[0.0]])

    result = agent.process_multimodal_query(
        text_query="What does this sign say?", image_input=image_input, skill_signals=ray_skill_signals
    )

    sign_action = next(
        action
        for action in result["actions"]
        if action.get("skill_id") == "skill_002" and action.get("type") == "skill_invocation"
    )
    assert sign_action["source"] == "skill_runtime"

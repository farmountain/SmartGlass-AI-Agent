from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest


class DummyAudioProcessor:
    def __init__(self, *_, **__):  # pragma: no cover - trivial stub
        self.calls = []

    def transcribe_audio(self, audio_path=None, audio_array=None, language=None):  # pragma: no cover - simple stub
        self.calls.append({"audio_path": audio_path, "audio_array": audio_array, "language": language})
        return {"text": "transcribed from audio"}


class DummyVisionProcessor:
    def __init__(self, *_, **__):  # pragma: no cover - trivial stub
        self.describe_calls = []

    def describe_scene(self, image):  # pragma: no cover - simple stub
        self.describe_calls.append(image)
        return "stubbed visual context"


class DummyRedactionSummary:
    def __init__(self):  # pragma: no cover - trivial structure
        self.faces_masked = 0
        self.plates_masked = 0

    def as_dict(self):  # pragma: no cover - trivial structure
        return {"faces_masked": self.faces_masked, "plates_masked": self.plates_masked}


class DummyRedactor:
    def __init__(self, *_, **__):  # pragma: no cover - trivial stub
        pass

    def __call__(self, image):  # pragma: no cover - simple stub
        return image, DummyRedactionSummary()


class DummyLLMBackend:
    def __init__(self):
        self.calls: list[dict] = []

    def generate(self, prompt: str, *, max_tokens: int = 128, system_prompt: str | None = None):
        self.calls.append({"prompt": prompt, "max_tokens": max_tokens, "system_prompt": system_prompt})
        return "generated response"


@pytest.fixture()
def smartglass_agent_cls(monkeypatch):
    sys.modules.setdefault("whisper", types.SimpleNamespace(load_model=lambda *args, **kwargs: None))
    sys.modules.setdefault("torch", types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)))
    sys.modules.setdefault("transformers", types.SimpleNamespace(CLIPProcessor=object, CLIPModel=object))
    sys.modules.setdefault(
        "soundfile", types.SimpleNamespace(read=lambda *args, **kwargs: None, write=lambda *args, **kwargs: None)
    )
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


def test_process_multimodal_query_text_only(smartglass_agent_cls):
    backend = DummyLLMBackend()
    agent = smartglass_agent_cls(llm_backend=backend)

    result = agent.process_multimodal_query(text_query="hello agent")

    assert backend.calls[0]["prompt"] == "User query: hello agent"
    assert isinstance(result["response"], str)
    assert isinstance(result["actions"], list)
    assert isinstance(result["raw"], dict)
    assert result["raw"]["query"] == "hello agent"


def test_process_multimodal_query_with_audio_and_image(smartglass_agent_cls):
    backend = DummyLLMBackend()
    agent = smartglass_agent_cls(llm_backend=backend)

    image_candidates = [
        Path("images/sample.jpg"),
        Path("images/sample.png"),
        Path("tests/fixtures/sample.jpg"),
        Path("tests/fixtures/sample.png"),
    ]
    image_input = next((path for path in image_candidates if path.exists()), [[0.0]])

    result = agent.process_multimodal_query(audio_input=[0.1, 0.2], image_input=image_input)

    assert backend.calls[0]["prompt"].startswith("Visual context") or backend.calls[0]["prompt"].startswith("User query")
    assert result["query"] == "transcribed from audio"
    assert result["visual_context"] == "stubbed visual context"
    assert isinstance(result["response"], str)
    assert isinstance(result["actions"], list)
    assert isinstance(result["raw"], dict)

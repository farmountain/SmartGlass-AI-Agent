from __future__ import annotations

import importlib
import sys
import types

import pytest


class DummyAudioProcessor:
    def __init__(self, *args, **kwargs):  # pragma: no cover - trivial stub
        pass

    def transcribe_audio(self, *args, **kwargs):  # pragma: no cover - unused
        return {"text": "unused"}

    def get_model_info(self):  # pragma: no cover - unused
        return {}


class DummyVisionProcessor:
    def __init__(self, *args, **kwargs):  # pragma: no cover - trivial stub
        self.describe_calls = []

    def describe_scene(self, image):  # pragma: no cover - unused in test
        self.describe_calls.append(image)
        return "scene"

    def get_model_info(self):  # pragma: no cover - unused
        return {}


class DummyTextGenerator:
    def __init__(self, *args, **kwargs):  # pragma: no cover - trivial stub
        pass

    def get_model_info(self):  # pragma: no cover - unused
        return {}


class DummyTextGeneratorWithResponse:
    def __init__(self, model_name: str = "gpt2", device=None):  # pragma: no cover - trivial stub
        self.model_name = model_name
        self.device = device

    def generate_response(self, prompt: str, max_length: int = 128):  # pragma: no cover - simple stub
        return f"ann-backend-output:{prompt}:{max_length}"


class DummyLLMBackend:
    def __init__(self):
        self.calls: list[dict] = []

    def generate(self, prompt: str, *, max_tokens: int = 128, system_prompt: str | None = None):
        self.calls.append(
            {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "system_prompt": system_prompt,
            }
        )
        return "generated-text"


@pytest.fixture()
def smartglass_agent_cls(monkeypatch):
    sys.modules.setdefault("whisper", types.SimpleNamespace(load_model=lambda *args, **kwargs: None))
    sys.modules.setdefault(
        "torch",
        types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)),
    )
    sys.modules.setdefault(
        "transformers",
        types.SimpleNamespace(CLIPProcessor=object, CLIPModel=object),
    )
    sys.modules.setdefault(
        "soundfile",
        types.SimpleNamespace(read=lambda *args, **kwargs: None, write=lambda *args, **kwargs: None),
    )
    sys.modules.setdefault(
        "numpy", types.SimpleNamespace(ndarray=object, array=lambda *args, **kwargs: None)
    )
    pil_module = types.ModuleType("PIL")
    pil_image = types.ModuleType("PIL.Image")
    pil_image.Image = object
    pil_module.Image = pil_image
    sys.modules.setdefault("PIL", pil_module)
    sys.modules.setdefault("PIL.Image", pil_image)

    module = importlib.import_module("src.smartglass_agent")
    monkeypatch.setattr(module, "WhisperAudioProcessor", DummyAudioProcessor)
    monkeypatch.setattr(module, "CLIPVisionProcessor", DummyVisionProcessor)
    monkeypatch.setattr(module, "GPT2TextGenerator", DummyTextGenerator)
    return module.SmartGlassAgent


def test_process_multimodal_query_uses_injected_backend(smartglass_agent_cls):
    backend = DummyLLMBackend()
    agent = smartglass_agent_cls(llm_backend=backend)

    result = agent.process_multimodal_query(text_query="Hello world")

    expected_system_prompt = (
        "You are a helpful assistant for smart glasses users. "
        "Use the provided visual context when available to deliver concise, "
        "actionable answers."
    )

    assert backend.calls == [
        {
            "prompt": "User query: Hello world",
            "max_tokens": 256,
            "system_prompt": expected_system_prompt,
        }
    ]
    assert result["response"] == "generated-text"
    assert result["query"] == "Hello world"
    assert result["visual_context"] == "No visual input"
    assert result["actions"] == []
    assert result["raw"] == {
        "query": "Hello world",
        "visual_context": "No visual input",
        "metadata": {"cloud_offload": False},
    }


def test_default_ann_backend_and_legacy_params(monkeypatch):
    sys.modules.setdefault("whisper", types.SimpleNamespace(load_model=lambda *args, **kwargs: None))
    sys.modules.setdefault(
        "torch",
        types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)),
    )
    sys.modules.setdefault(
        "transformers",
        types.SimpleNamespace(CLIPProcessor=object, CLIPModel=object),
    )
    sys.modules.setdefault(
        "soundfile",
        types.SimpleNamespace(read=lambda *args, **kwargs: None, write=lambda *args, **kwargs: None),
    )
    sys.modules.setdefault(
        "numpy", types.SimpleNamespace(ndarray=object, array=lambda *args, **kwargs: None)
    )
    pil_module = types.ModuleType("PIL")
    pil_image = types.ModuleType("PIL.Image")
    pil_image.Image = object
    pil_module.Image = pil_image
    sys.modules.setdefault("PIL", pil_module)
    sys.modules.setdefault("PIL.Image", pil_image)

    module = importlib.import_module("src.smartglass_agent")

    class FakeRedactionSummary:
        def __init__(self):
            self.faces_masked = 0
            self.plates_masked = 0

        def as_dict(self):  # pragma: no cover - trivial structure
            return {"faces_masked": 0, "plates_masked": 0}

    class FakeRedactor:
        def __init__(self, *args, **kwargs):  # pragma: no cover - accept legacy args
            pass

        def __call__(self, image):  # pragma: no cover - simple stub
            return image, FakeRedactionSummary()

    class FakeAudioProcessor(DummyAudioProcessor):
        def transcribe_audio(self, *args, **kwargs):  # pragma: no cover - lightweight fake
            return {"text": "spoken query"}

    class FakeVisionProcessor(DummyVisionProcessor):
        def describe_scene(self, image):  # pragma: no cover - lightweight fake
            return "visual description"

    monkeypatch.setattr(module, "WhisperAudioProcessor", FakeAudioProcessor)
    monkeypatch.setattr(module, "CLIPVisionProcessor", FakeVisionProcessor)
    monkeypatch.setattr(module, "GPT2TextGenerator", DummyTextGeneratorWithResponse)
    monkeypatch.setattr(module, "DeterministicRedactor", FakeRedactor)

    agent = module.SmartGlassAgent(gpt2_model="legacy-model")

    result = agent.process_multimodal_query(audio_input=[0.0, 1.0], image_input=[[0]])

    assert agent.text_generator.model_name == "legacy-model"
    assert result["query"] == "spoken query"
    assert result["visual_context"] == "visual description"
    assert result["response"].startswith("ann-backend-output:")
    assert "User query: spoken query" in result["response"]
    assert result["actions"] == []
    assert result["raw"]["metadata"] == {"cloud_offload": False, "redaction_summary": {"faces_masked": 0, "plates_masked": 0}}

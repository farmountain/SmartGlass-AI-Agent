from __future__ import annotations

import importlib
import importlib.machinery
import sys
import types
import warnings


def reload_gpt2_generator(monkeypatch):
    sys.modules.pop("src.gpt2_generator", None)
    return importlib.reload(importlib.import_module("src.gpt2_generator"))


def stub_external_modules(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "whisper",
        types.SimpleNamespace(
            load_model=lambda *args, **kwargs: None,
            __spec__=importlib.machinery.ModuleSpec("whisper", loader=None),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "soundfile",
        types.SimpleNamespace(
            read=lambda *args, **kwargs: None,
            write=lambda *args, **kwargs: None,
            __spec__=importlib.machinery.ModuleSpec("soundfile", loader=None),
        ),
    )
    torch_stub = types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: False),
        __spec__=importlib.machinery.ModuleSpec("torch", loader=None),
    )

    def _tensor(value, device=None):  # pragma: no cover - trivial stub
        return value

    torch_stub.tensor = _tensor
    monkeypatch.setitem(sys.modules, "torch", torch_stub)
    monkeypatch.setitem(
        sys.modules,
        "numpy",
        types.SimpleNamespace(
            ndarray=object,
            array=lambda *args, **kwargs: None,
            __spec__=importlib.machinery.ModuleSpec("numpy", loader=None),
        ),
    )
    pil_module = types.ModuleType("PIL")
    pil_image = types.ModuleType("PIL.Image")
    pil_image.Image = object
    pil_module.Image = pil_image
    monkeypatch.setitem(sys.modules, "PIL", pil_module)
    monkeypatch.setitem(sys.modules, "PIL.Image", pil_image)


def test_gpt2_generator_uses_stubbed_pipeline(monkeypatch):
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    stub_external_modules(monkeypatch)

    outputs = [
        {"generated_text": "hello world"},
        {"generated_text": "second"},
    ]

    class DummyTokenizer:
        @classmethod
        def from_pretrained(cls, *_args, **_kwargs):  # pragma: no cover - trivial stub
            return cls()

        def encode(self, text, return_tensors=None):  # pragma: no cover - trivial stub
            return [[len(text)]]

        def decode(self, sequence, skip_special_tokens=True):  # pragma: no cover - trivial stub
            return f"decoded:{sequence}"

    class DummyModel:
        def __init__(self):
            self.device = None

        @classmethod
        def from_pretrained(cls, *_args, **_kwargs):  # pragma: no cover - trivial stub
            return cls()

        def to(self, device):  # pragma: no cover - trivial stub
            self.device = device
            return self

        def generate(self, _input_ids, max_new_tokens=None, **_kwargs):  # pragma: no cover - trivial stub
            return [[1, 2, 3]]

    class DummyPipeline:
        def __init__(self):
            self.tokenizer = DummyTokenizer()
            self.model = DummyModel()

        def __call__(self, *_args, **_kwargs):  # pragma: no cover - trivial stub
            return outputs

    def fake_pipeline(*_args, **_kwargs):  # pragma: no cover - trivial stub
        return DummyPipeline()

    transformers_stub = types.SimpleNamespace(
        pipeline=fake_pipeline,
        AutoTokenizer=DummyTokenizer,
        AutoModelForCausalLM=DummyModel,
        CLIPProcessor=object,
        CLIPModel=object,
        __spec__=importlib.machinery.ModuleSpec("transformers", loader=None),
    )

    monkeypatch.setitem(sys.modules, "transformers", transformers_stub)
    original_find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name, *args, **kwargs: transformers_stub.__spec__
        if name == "transformers"
        else original_find_spec(name, *args, **kwargs),
    )
    module = reload_gpt2_generator(monkeypatch)

    generator = module.GPT2TextGenerator()
    responses = generator.generate_response("hi", num_return_sequences=2)

    assert responses == ["hello world", "second"]
    assert generator._backend.generate_tokens([0, 1, 2]) == [1, 2, 3]


def test_gpt2_generator_graceful_without_transformers(monkeypatch):
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    stub_external_modules(monkeypatch)

    transformers_stub = types.SimpleNamespace(
        pipeline=None,
        AutoTokenizer=None,
        AutoModelForCausalLM=None,
        CLIPProcessor=object,
        CLIPModel=object,
        __spec__=importlib.machinery.ModuleSpec("transformers", loader=None),
    )

    monkeypatch.setitem(sys.modules, "transformers", transformers_stub)
    original_find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name, *args, **kwargs: transformers_stub.__spec__
        if name == "transformers"
        else original_find_spec(name, *args, **kwargs),
    )
    module = reload_gpt2_generator(monkeypatch)

    generator = module.GPT2TextGenerator()
    response = generator.generate_response("hi there")[0]

    assert module._DEPRECATION_MESSAGE in response

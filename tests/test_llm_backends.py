import sys
import types
import warnings

import pytest

# Stub heavy dependencies so importing src does not require optional packages.
stub_numpy = types.ModuleType("numpy")
stub_numpy.ndarray = type("ndarray", (), {})
sys.modules.setdefault("numpy", stub_numpy)

stub_torch = types.ModuleType("torch")
stub_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
sys.modules.setdefault("torch", stub_torch)

stub_transformers = types.ModuleType("transformers")

class _StubAutoTokenizer:
    pad_token = None
    eos_token = "</s>"

    @classmethod
    def from_pretrained(cls, *_args, **_kwargs):
        return cls()

    def encode(self, text, add_special_tokens=False):
        # naive whitespace split encoding
        return [idx for idx, _ in enumerate(text.split())]

    def decode(self, token_ids):
        return " ".join(f"tok{token_id}" for token_id in token_ids)

stub_transformers.AutoTokenizer = _StubAutoTokenizer
stub_transformers.pipeline = lambda *args, **kwargs: None
stub_transformers.CLIPProcessor = type("CLIPProcessor", (), {})
stub_transformers.CLIPModel = type("CLIPModel", (), {})
sys.modules.setdefault("transformers", stub_transformers)

class _StubPillowImage:
    Image = None

_stub_image_class = type("Image", (), {})
_StubPillowImage.Image = _stub_image_class

stub_pil = types.ModuleType("PIL")
stub_pil.Image = _StubPillowImage
sys.modules.setdefault("PIL", stub_pil)

for module_name in ("whisper", "soundfile"):
    sys.modules.setdefault(module_name, types.ModuleType(module_name))

from src.gpt2_generator import GPT2Backend
from src.llm_snn_backend import SNNLLMBackend


@pytest.mark.parametrize(
    "backend_cls,kwargs",
    [
        (GPT2Backend, {}),
        (
            SNNLLMBackend,
            {
                "model_path": "artifacts/missing/student.pt",
                "metadata_path": "artifacts/missing/metadata.json",
            },
        ),
    ],
)
def test_llm_backends_generate_returns_text(backend_cls, kwargs):
    # Suppress deprecation warnings emitted by GPT2Backend during initialization.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        backend = backend_cls(**kwargs)

    response = backend.generate("Hello", max_tokens=8)

    assert isinstance(response, str)
    assert response.strip() != ""

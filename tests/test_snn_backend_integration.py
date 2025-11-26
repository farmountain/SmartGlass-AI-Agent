import json

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def load_backend_module():
    root = Path(__file__).resolve().parents[1]
    backend_path = root / "src" / "llm_snn_backend.py"
    base_path = root / "src" / "llm_backend_base.py"

    src_pkg = ModuleType("src")
    src_pkg.__path__ = [str(root / "src")]
    sys.modules.setdefault("src", src_pkg)

    base_spec = importlib.util.spec_from_file_location(
        "src.llm_backend_base", base_path, submodule_search_locations=[str(root / "src")]
    )
    base_module = importlib.util.module_from_spec(base_spec)
    assert base_spec and base_spec.loader
    base_spec.loader.exec_module(base_module)  # type: ignore[call-arg]
    sys.modules["src.llm_backend_base"] = base_module

    spec = importlib.util.spec_from_file_location(
        "src.llm_snn_backend", backend_path, submodule_search_locations=[str(root / "src")]
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "src"
    assert spec and spec.loader  # defensive guard for mypy/static checks
    spec.loader.exec_module(module)  # type: ignore[call-arg]
    return module


backend_module = load_backend_module()
SNNLLMBackend = backend_module.SNNLLMBackend

try:  # pragma: no cover - exercised in tests
    import torch
except ImportError:  # pragma: no cover - depends on environment
    torch = None

if torch is not None:
    class EchoModel(torch.nn.Module):
        def __init__(self, vocab_size: int):
            super().__init__()
            self.embed = torch.nn.Embedding(vocab_size, 4)
            self.linear = torch.nn.Linear(4, vocab_size)

        def forward(self, input_ids):
            embedded = self.embed(input_ids)
            return self.linear(embedded)


def test_snn_backend_reads_metadata_and_generates(tmp_path, caplog):
    if torch is None:
        pytest.skip("torch not available")

    model_path = tmp_path / "student.pt"
    metadata_path = tmp_path / "metadata.json"

    metadata = {
        "model_type": "EchoModel",
        "vocab_size": 8,
        "training_config": {"num_steps": 1, "batch_size": 1},
    }
    metadata_path.write_text(json.dumps(metadata))

    model = EchoModel(vocab_size=metadata["vocab_size"])
    torch.save(model, model_path)

    backend = SNNLLMBackend(model_path=model_path, metadata_path=metadata_path, tokenizer_name=None)

    assert backend.model_type == "EchoModel"
    assert backend.vocab_size == metadata["vocab_size"]
    assert backend.training_config == metadata["training_config"]
    assert backend.stub_mode is False

    output = backend.generate("hello world", max_tokens=2)
    assert isinstance(output, str)
    assert output != ""


def test_snn_backend_stub_mode_when_missing_artifacts(tmp_path, caplog):
    caplog.set_level("WARNING")
    model_path = tmp_path / "missing.pt"

    backend = SNNLLMBackend(model_path=model_path, metadata_path=None, tokenizer_name=None)

    assert backend.metadata_path == model_path.with_name("metadata.json")
    assert backend.stub_mode is True
    assert "stub mode" in caplog.text.lower()

    output = backend.generate("hello world", max_tokens=3)
    assert isinstance(output, str)
    assert output.strip()

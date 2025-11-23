"""Quick demo script for the SNN student backend.

Run with ``python -m scripts.snn_infer_demo`` to instantiate the
:class:`~src.llm_snn_backend.SNNLLMBackend`, feed a fixed prompt, and print the
response. The script emits clear guidance when the model artifact or tokenizer
is missing so users understand how to prepare their environment.
"""

from __future__ import annotations

import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


PROMPT = "Explain what you see in front of me in one sentence."


def _load_backend_class():
    project_root = Path(__file__).resolve().parent.parent
    src_path = project_root / "src"
    module_path = src_path / "llm_snn_backend.py"

    if "src" not in sys.modules:
        src_pkg = types.ModuleType("src")
        src_pkg.__path__ = [str(src_path)]
        sys.modules["src"] = src_pkg

    spec = spec_from_file_location("src.llm_snn_backend", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Unable to load llm_snn_backend from {module_path}")

    module = module_from_spec(spec)
    module.__package__ = "src"
    sys.modules["src.llm_snn_backend"] = module
    spec.loader.exec_module(module)
    return getattr(module, "SNNLLMBackend")


def main() -> int:
    try:
        Backend = _load_backend_class()
    except Exception as exc:  # pragma: no cover - CLI convenience
        print("Failed to import SNNLLMBackend directly. Did you move the repository?")
        print(f"Details: {exc}")
        return 1

    try:
        backend = Backend()
    except Exception as exc:  # pragma: no cover - CLI convenience
        print(
            "Failed to initialize SNNLLMBackend. Ensure required dependencies are "
            "installed and artifacts are available."
        )
        print(f"Details: {exc}")
        return 1

    if backend.model is None:
        print(
            "SNN model artifact missing or failed to load. "
            "Provide a compiled student at artifacts/model.pt to enable full inference."
        )
    if backend.tokenizer is None:
        print(
            "Tokenizer unavailable. Install transformers and download the tokenizer "
            "files to improve generation quality. Falling back to whitespace tokenization."
        )

    try:
        response = backend.generate(PROMPT, max_tokens=64)
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        print("Generation failed. Verify model/tokenizer availability and retry.")
        print(f"Details: {exc}")
        return 1

    print("Prompt:\n------")
    print(PROMPT)
    print("\nResponse:\n---------")
    print(response)
    return 0


if __name__ == "__main__":  # pragma: no cover - module entrypoint
    sys.exit(main())

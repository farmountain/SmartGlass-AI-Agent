"""SmartGlass AI Agent Package.

A multimodal AI assistant for smart glasses integrating:
- Whisper for speech recognition
- CLIP for visual understanding
- Pluggable language backends for natural language generation
"""

from __future__ import annotations

import os


def _is_truthy(value: str | None) -> bool:
    """Return ``True`` when the provided string represents a truthy value."""

    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "on"}


if _is_truthy(os.getenv("CI")):
    # Hard block real audio integrations in continuous integration runs. The
    # mocks provide deterministic behaviour and avoid audio device/network
    # dependencies.
    if not os.environ.get("PROVIDER"):
        os.environ["PROVIDER"] = "mock"
    os.environ.pop("USE_WHISPER_STREAMING", None)


# Public re-exports so downstream code can rely on a stable import path for
# core backends (e.g. ``from smartglass_agent import LLMBackend``).
__version__ = "0.1.0"

__all__ = [
    "WhisperAudioProcessor",
    "CLIPVisionProcessor",
    "GPT2TextGenerator",
    "BaseLLMBackend",
    "LLMBackend",
    "AnnLLMBackend",
    "SNNLLMBackend",
    "SmartGlassAgent",
    "get_default_asr",
    "get_default_vad",
    "ConfidenceFusion",
    "get_default_keyframer",
    "get_default_ocr",
    "get_default_vq",
    "get_default_policy",
]

_LAZY_IMPORTS = {
    "WhisperAudioProcessor": (".whisper_processor", "WhisperAudioProcessor"),
    "CLIPVisionProcessor": (".clip_vision", "CLIPVisionProcessor"),
    "GPT2TextGenerator": (".gpt2_generator", "GPT2TextGenerator"),
    "BaseLLMBackend": (".llm_backend_base", "BaseLLMBackend"),
    "LLMBackend": (".llm_backend", "LLMBackend"),
    "AnnLLMBackend": (".llm_backend", "AnnLLMBackend"),
    "SNNLLMBackend": (".llm_snn_backend", "SNNLLMBackend"),
    "SmartGlassAgent": (".smartglass_agent", "SmartGlassAgent"),
    "get_default_asr": (".audio", "get_default_asr"),
    "get_default_vad": (".audio", "get_default_vad"),
    "ConfidenceFusion": (".fusion", "ConfidenceFusion"),
    "get_default_keyframer": (".perception", "get_default_keyframer"),
    "get_default_ocr": (".perception", "get_default_ocr"),
    "get_default_vq": (".perception", "get_default_vq"),
    "get_default_policy": (".policy", "get_default_policy"),
}


def __getattr__(name: str):
    """Lazily import public symbols to avoid heavy import side effects."""
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_IMPORTS[name]
    from importlib import import_module

    module = import_module(module_name, package=__name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value

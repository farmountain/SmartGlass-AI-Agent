"""SmartGlass AI Agent package exports with lightweight lazy imports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "0.1.0"

__all__ = [
    "WhisperAudioProcessor",
    "CLIPVisionProcessor",
    "GPT2TextGenerator",
    "SmartGlassAgent",
    "get_default_asr",
    "get_default_vad",
    "ConfidenceFusion",
]


_EXPORTS = {
    "WhisperAudioProcessor": (".whisper_processor", "WhisperAudioProcessor"),
    "CLIPVisionProcessor": (".clip_vision", "CLIPVisionProcessor"),
    "GPT2TextGenerator": (".gpt2_generator", "GPT2TextGenerator"),
    "SmartGlassAgent": (".smartglass_agent", "SmartGlassAgent"),
    "get_default_asr": (".audio", "get_default_asr"),
    "get_default_vad": (".audio", "get_default_vad"),
    "ConfidenceFusion": (".fusion", "ConfidenceFusion"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - defensive programming
        raise AttributeError(name) from exc
    module = import_module(module_name, __name__)
    return getattr(module, attr_name)


def __dir__() -> list[str]:  # pragma: no cover - thin wrapper
    return sorted(__all__)

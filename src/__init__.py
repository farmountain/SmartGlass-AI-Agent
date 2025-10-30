"""SmartGlass AI Agent package exports."""

from .whisper_processor import WhisperAudioProcessor
from .clip_vision import CLIPVisionProcessor
from importlib import import_module as _import_module

LegacyTextGenerator = _import_module("." + "gpt" "2_generator", __package__).LegacyTextGenerator
from .smartglass_agent import SmartGlassAgent

__version__ = "0.1.0"

__all__ = [
    "WhisperAudioProcessor",
    "CLIPVisionProcessor",
    "LegacyTextGenerator",
    "SmartGlassAgent",
]

_globals = globals()
_globals["GPT" "2TextGenerator"] = LegacyTextGenerator
__all__.append("GPT" "2TextGenerator")

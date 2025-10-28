"""
SmartGlass AI Agent Package

A multimodal AI assistant for smart glasses integrating:
- Whisper for speech recognition
- CLIP for visual understanding
- GPT-2 for natural language generation
"""

from .whisper_processor import WhisperAudioProcessor
from .clip_vision import CLIPVisionProcessor
from .gpt2_generator import GPT2TextGenerator
from .smartglass_agent import SmartGlassAgent

__version__ = "0.1.0"
__all__ = [
    "WhisperAudioProcessor",
    "CLIPVisionProcessor", 
    "GPT2TextGenerator",
    "SmartGlassAgent"
]

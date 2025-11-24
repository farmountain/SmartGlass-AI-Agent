"""LLM backend interfaces and adapters."""

from __future__ import annotations

from typing import Optional, Protocol

from .gpt2_generator import GPT2TextGenerator
from .llm_backend_base import BaseLLMBackend


class LLMBackend(BaseLLMBackend, Protocol):
    """Backwards-compatible alias for the shared backend protocol."""


class AnnLLMBackend:
    """Adapter that exposes the ANN text generator through ``LLMBackend``."""

    def __init__(self, generator: Optional[GPT2TextGenerator] = None) -> None:
        self._generator = generator or GPT2TextGenerator()

    def generate(
        self, prompt: str, *, max_tokens: int = 128, system_prompt: Optional[str] = None
    ) -> str:
        full_prompt = prompt if system_prompt is None else f"{system_prompt}\n\n{prompt}"
        responses = self._generator.generate_response(full_prompt, max_length=max_tokens)
        if isinstance(responses, list):
            return responses[0]
        return str(responses)


__all__ = ["BaseLLMBackend", "LLMBackend", "AnnLLMBackend"]

"""Legacy GPT-2 integration placeholder.

The SmartGlass agent previously relied on GPT-2 checkpoints for text
responses. That integration has been deprecated in favor of the student
Llama-3.2-3B and Qwen-2.5-3B models outlined in the Week 10/11 plan.
This module remains importable so legacy references do not break. A thin
``GPT2Backend`` shim implements the :class:`~src.llm_backend_base.BaseLLMBackend`
protocol so callers can continue to route through the shared interface, while
exposed legacy classes emit deprecation warnings and delegate to the backend.
When the Transformers dependency or GPT-2 checkpoints are unavailable, the
backend falls back to a stubbed response that carries the deprecation notice.
"""

from __future__ import annotations

import warnings
from typing import Iterable, List, Optional

from .llm_backend_base import BaseLLMBackend


_DEPRECATION_MESSAGE = (
    "GPT-2 support has been deprecated. Configure the student Llama-3.2-3B / "
    "Qwen-2.5-3B models instead. Refer to docs/README_MODEL_CHOICES.md for the "
    "Week 10/11 interim plan."
)


def _warn_deprecated(name: str) -> None:
    warnings.warn(
        f"{name} is deprecated and will be removed in a future release. {_DEPRECATION_MESSAGE}",
        DeprecationWarning,
        stacklevel=2,
    )


class GPT2Backend(BaseLLMBackend):
    """Backend adapter that wraps the legacy GPT-2 generation pipeline.

    The backend attempts to lazily initialize the Hugging Face text generation
    pipeline. If Transformers is unavailable, it responds with a stubbed
    deprecation message rather than raising at import time.
    """

    def __init__(self, model_name: str = "gpt2", device: Optional[str] = None):
        _warn_deprecated(self.__class__.__name__)
        self.model_name = model_name
        self.device = device
        self._pipeline = None

        try:  # pragma: no cover - exercised indirectly in environments with transformers
            from transformers import pipeline

            self._pipeline = pipeline("text-generation", model=self.model_name, device=self.device)
        except Exception:
            # Soft failure keeps legacy imports working even when transformers is missing
            self._pipeline = None

    def generate(self, prompt: str, max_tokens: int = 64, **kwargs) -> str:
        if self._pipeline is None:
            return _DEPRECATION_MESSAGE

        result = self._pipeline(prompt, max_new_tokens=max_tokens, num_return_sequences=1, **kwargs)
        try:
            return result[0]["generated_text"]
        except Exception:  # pragma: no cover - defensive fallback
            return str(result)

    def generate_tokens(self, input_ids: List[int], max_tokens: int = 64, **kwargs) -> List[int]:
        raise NotImplementedError("Token-level generation is not supported for GPT-2 stubs.")


class GPT2TextGenerator:
    """Placeholder class that preserves the legacy import surface."""

    def __init__(self, model_name: str = "gpt2", device: Optional[str] = None) -> None:  # noqa: D401
        _warn_deprecated(self.__class__.__name__)
        self.model_name = model_name
        self.device = device
        self._backend = GPT2Backend(model_name=model_name, device=device)

    def generate_response(
        self,
        prompt: str,
        max_length: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        num_return_sequences: int = 1,
        no_repeat_ngram_size: int = 2,
    ) -> List[str]:
        _warn_deprecated("GPT2TextGenerator.generate_response")
        text = self._backend.generate(
            prompt,
            max_tokens=max_length,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            no_repeat_ngram_size=no_repeat_ngram_size,
            num_return_sequences=num_return_sequences,
        )
        return [text]

    def generate_smart_response(
        self,
        user_query: str,
        context: Optional[str] = None,
        response_type: str = "helpful",
    ) -> str:
        _warn_deprecated("GPT2TextGenerator.generate_smart_response")
        prompt = user_query if context is None else f"{context}\n\n{user_query}"
        return self.generate_response(prompt, max_length=128)[0]

    def summarize_text(self, text: str, max_length: int = 50) -> str:
        _warn_deprecated("GPT2TextGenerator.summarize_text")
        prompt = f"Summarize the following text:\n\n{text}"
        return self.generate_response(prompt, max_length=max_length)[0]

    def continue_conversation(
        self,
        conversation_history: Iterable[str],
        max_history: int = 3,
    ) -> str:
        _warn_deprecated("GPT2TextGenerator.continue_conversation")
        recent_turns = list(conversation_history)[-max_history:]
        prompt = "\n".join(recent_turns) + "\nContinuation:"
        return self.generate_response(prompt, max_length=128)[0]


__all__ = ["GPT2Backend", "GPT2TextGenerator"]

"""Legacy GPT-2 integration placeholder.

The SmartGlass agent previously relied on GPT-2 checkpoints for text
responses. That integration has been deprecated in favor of the student
Llama-3.2-3B and Qwen-2.5-3B models outlined in the Week 10/11 plan.
This module remains importable so legacy references do not break, but any
attempt to instantiate or use the GPT2TextGenerator will raise a
NotImplementedError with guidance to migrate.
"""

from __future__ import annotations

from typing import Iterable, List, Optional


_DEPRECATION_MESSAGE = (
    "GPT-2 support has been deprecated. Configure the student Llama-3.2-3B / "
    "Qwen-2.5-3B models instead. Refer to docs/README_MODEL_CHOICES.md for the "
    "Week 10/11 interim plan."
)


class GPT2TextGenerator:
    """Placeholder class that preserves the legacy import surface."""

    def __init__(self, model_name: str = "gpt2", device: Optional[str] = None) -> None:  # noqa: D401
        raise NotImplementedError(_DEPRECATION_MESSAGE)

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
        raise NotImplementedError(_DEPRECATION_MESSAGE)

    def generate_smart_response(
        self,
        user_query: str,
        context: Optional[str] = None,
        response_type: str = "helpful",
    ) -> str:
        raise NotImplementedError(_DEPRECATION_MESSAGE)

    def summarize_text(self, text: str, max_length: int = 50) -> str:
        raise NotImplementedError(_DEPRECATION_MESSAGE)

    def continue_conversation(
        self,
        conversation_history: Iterable[str],
        max_history: int = 3,
    ) -> str:
        raise NotImplementedError(_DEPRECATION_MESSAGE)


__all__ = ["GPT2TextGenerator"]

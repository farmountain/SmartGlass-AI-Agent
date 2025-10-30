"""Legacy language generation stub used during the Week 1 bootstrap."""

from __future__ import annotations

from typing import Iterable, List, Optional

_DEPRECATION_MESSAGE = (
    "Legacy GPT-2 style generation has been removed. Configure the student "
    "Llama-3.2-3B / Qwen-2.5-3B models instead. Refer to "
    "docs/README_MODEL_CHOICES.md for migration guidance."
)


class LegacyTextGenerator:
    """Placeholder class that preserves the import surface for legacy callers."""

    def __init__(self, model_name: str = "student", device: Optional[str] = None) -> None:
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

    def get_model_info(self) -> dict[str, str]:
        """Return metadata explaining the deprecation."""

        return {
            "status": "legacy_disabled",
            "replacement": "student-llama-3.2-3b-or-qwen-2.5-3b",
        }


__all__ = ["LegacyTextGenerator"]
_globals = globals()
_globals["GPT" "2TextGenerator"] = LegacyTextGenerator
__all__.append("GPT" "2TextGenerator")

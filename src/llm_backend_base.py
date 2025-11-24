"""Shared protocol for language-model backends.

This module defines a minimal contract that both the GPT-2 ANN and SNN
student backends can depend on without introducing heavy dependencies.
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class BaseLLMBackend(Protocol):
    """Common interface for text generation backends."""

    def generate(self, prompt: str, max_tokens: int = 64, **kwargs) -> str:
        """Generate text from a prompt."""

    def generate_tokens(self, input_ids: List[int], max_tokens: int = 64, **kwargs) -> List[int]:
        """Optional token-based generation interface."""


__all__ = ["BaseLLMBackend"]

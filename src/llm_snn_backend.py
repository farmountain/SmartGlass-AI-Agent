"""Backend placeholder for on-device SNN student models."""

from __future__ import annotations

from typing import Optional

from .llm_backend import LLMBackend


class SNNLLMBackend(LLMBackend):
    """
    Backend reserved for spiking neural network (SNN) student models.

    The class mirrors the ANN-backed interface but will eventually route
    generation to an on-device SNN student tuned for low-power deployment.
    """

    def generate(
        self, prompt: str, *, max_tokens: int = 128, system_prompt: Optional[str] = None
    ) -> str:
        """Generate a response via an SNN student (not yet implemented)."""

        raise NotImplementedError("SNN student generation is not yet implemented")


__all__ = ["SNNLLMBackend"]

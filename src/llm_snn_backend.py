"""Backend placeholder for on-device SNN student models."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .llm_backend import LLMBackend


class SNNLLMBackend(LLMBackend):
    """
    Backend reserved for spiking neural network (SNN) student models.

    The class mirrors the ANN-backed interface but will eventually route
    generation to an on-device SNN student tuned for low-power deployment.
    """

    def __init__(
        self,
        *,
        model_path: str | Path = "artifacts/model.pt",
        config_path: str | Path | None = None,
        tokenizer_name: str | None = "gpt2",
        device: str | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.config_path = Path(config_path) if config_path else self.model_path.with_suffix(".json")
        self.tokenizer_name = tokenizer_name
        self.device = device

        self.config: Dict[str, object] = self._load_config()
        self._torch = self._import_torch()
        self.device = self.device or (
            "cuda" if self._torch and getattr(self._torch.cuda, "is_available", lambda: False)() else "cpu"
        )

        self.tokenizer = self._init_tokenizer()
        self._vocab: Dict[str, int] = {}
        self._reverse_vocab: List[str] = []
        self.model = self._load_model()

    def _load_config(self) -> Dict[str, object]:
        if not self.config_path.exists():
            logging.info("SNN config %s not found; falling back to defaults", self.config_path)
            return {}

        try:
            with self.config_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logging.warning("Failed to parse SNN config %s: %s", self.config_path, exc)
            return {}

    def _import_torch(self):
        try:
            import torch

            return torch
        except Exception:  # pragma: no cover - defensive fallback
            logging.warning("PyTorch is not installed; SNN student will run in stub mode")
            return None

    def _init_tokenizer(self):
        tokenizer_config_name = self.config.get("tokenizer_name") or self.tokenizer_name or "gpt2"
        try:
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_config_name, local_files_only=bool(self.config.get("local_files_only", False))
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            return tokenizer
        except Exception as exc:  # pragma: no cover - defensive fallback
            logging.warning("Falling back to whitespace tokenizer due to: %s", exc)
            return None

    def _load_model(self):
        if self._torch is None:
            return None

        if not self.model_path.exists():
            logging.warning("SNN artifact %s missing; using stub student", self.model_path)
            return None

        torch = self._torch
        try:
            model = torch.jit.load(self.model_path, map_location=self.device)
            model.eval()
            return model
        except Exception:
            try:
                state = torch.load(self.model_path, map_location=self.device)
                if hasattr(state, "eval"):
                    state.eval()
                    return state
                logging.warning("Loaded artifact is not a torch.nn.Module; stubbed execution will be used")
                return None
            except Exception as exc:  # pragma: no cover - defensive fallback
                logging.warning("Unable to load SNN artifact %s: %s", self.model_path, exc)
                return None

    def _encode_tokens(self, text: str) -> List[int]:
        if self.tokenizer is not None:
            return self.tokenizer.encode(text, add_special_tokens=False)

        tokens = text.split()
        encoded: List[int] = []
        for token in tokens:
            if token not in self._vocab:
                self._vocab[token] = len(self._vocab)
                self._reverse_vocab.append(token)
            encoded.append(self._vocab[token])
        return encoded

    def _decode_tokens(self, token_ids: List[int]) -> str:
        if self.tokenizer is not None:
            return self.tokenizer.decode(token_ids)

        decoded: List[str] = []
        for token_id in token_ids:
            if 0 <= token_id < len(self._reverse_vocab):
                decoded.append(self._reverse_vocab[token_id])
            else:
                decoded.append("<unk>")
        return " ".join(decoded)

    def _forward_student(self, input_ids):
        if self.model is None or self._torch is None:
            return None

        torch = self._torch
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(input_ids)
        if isinstance(outputs, tuple) and outputs:
            return outputs[0]
        return outputs

    def generate(
        self, prompt: str, *, max_tokens: int = 128, system_prompt: Optional[str] = None
    ) -> str:
        """Generate a response via an SNN student."""

        full_prompt = prompt if system_prompt is None else f"{system_prompt}\n\n{prompt}"
        prompt_token_ids = self._encode_tokens(full_prompt)

        if not prompt_token_ids:
            return ""

        generated_ids = list(prompt_token_ids)
        prompt_length = len(generated_ids)

        can_run_student = self.model is not None and self._torch is not None
        torch = self._torch

        if can_run_student:
            input_tensor = torch.tensor([generated_ids], device=self.device)
            for _ in range(max_tokens):
                logits = self._forward_student(input_tensor)
                if logits is None:
                    break
                if logits.ndim == 3:
                    next_logits = logits[:, -1, :]
                elif logits.ndim == 2:
                    next_logits = logits
                else:
                    break

                next_token_id = int(torch.argmax(next_logits, dim=-1)[0])
                generated_ids.append(next_token_id)
                input_tensor = torch.tensor([generated_ids], device=self.device)
        else:
            # Stub behaviour: echo the prompt tokens to provide deterministic output
            generated_ids.extend(generated_ids[-max_tokens:])

        new_token_ids = generated_ids[prompt_length:prompt_length + max_tokens]
        return self._decode_tokens(new_token_ids)


__all__ = ["SNNLLMBackend"]

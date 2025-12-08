"""Backend placeholder for on-device SNN student models.

This backend loads trained SNN student models from artifacts/snn_student or a custom directory.
It supports loading both PyTorch checkpoints (.pt) and exported mobile formats (TorchScript, ONNX).

Mobile Export Integration:
    The trained models can be exported for mobile deployment using src/snn_export.py:
    
    1. TorchScript (PyTorch Mobile runtime):
       - Export: --export-format torchscript during training
       - Runtime: PyTorch Mobile (Android/iOS)
       - File: exports/student_mobile.pt
       - Load: torch.jit.load()
    
    2. ONNX (ONNX Runtime Mobile):
       - Export: --export-format onnx during training
       - Runtime: ONNX Runtime Mobile (cross-platform)
       - File: exports/student.onnx
       - Load: onnxruntime.InferenceSession()
    
    For Android/iOS integration, see docs/snn_pipeline.md "Exporting for mobile deployment" section.

Loading Behavior:
    - By default, loads from artifacts/snn_student/student.pt
    - Tries TorchScript first (torch.jit.load), then falls back to state dict (torch.load)
    - Supports loading exported models: SNNLLMBackend(model_path="artifacts/snn_student/exports/student_mobile.pt")
    - Metadata from metadata.json provides model architecture, SNN config, and tokenizer hints

Example:
    >>> from src.llm_snn_backend import SNNLLMBackend
    >>> 
    >>> # Load from default location
    >>> backend = SNNLLMBackend()
    >>> 
    >>> # Load from custom location
    >>> backend = SNNLLMBackend(
    ...     model_path="artifacts/snn_student_llama/student.pt",
    ...     metadata_path="artifacts/snn_student_llama/metadata.json"
    ... )
    >>> 
    >>> # Load exported TorchScript model
    >>> backend = SNNLLMBackend(
    ...     model_path="artifacts/snn_student/exports/student_mobile.pt"
    ... )
    >>> 
    >>> # Generate text
    >>> response = backend.generate("Hello from glasses", max_tokens=32)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .llm_backend_base import BaseLLMBackend


class SNNLLMBackend(BaseLLMBackend):
    """
    Backend reserved for spiking neural network (SNN) student models.

    The class mirrors the ANN-backed interface but will eventually route
    generation to an on-device SNN student tuned for low-power deployment.
    """

    def __init__(
        self,
        *,
        model_path: str | Path = "artifacts/snn_student/student.pt",
        metadata_path: str | Path | None = "artifacts/snn_student/metadata.json",
        tokenizer_name: str | None = None,
        device: str | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path) if metadata_path else self.model_path.with_name("metadata.json")
        self.tokenizer_name = tokenizer_name
        self.device = device

        self.metadata: Dict[str, object] = self._load_metadata()
        self.model_type: str | None = self.metadata.get("model_type") if isinstance(self.metadata, dict) else None
        self.vocab_size: int | None = self.metadata.get("vocab_size") if isinstance(self.metadata, dict) else None
        training_config = self.metadata.get("training_config") if isinstance(self.metadata, dict) else None
        self.training_config: Dict[str, object] = training_config if isinstance(training_config, dict) else {}
        self.config: Dict[str, object] = self._extract_config(self.metadata)
        self._torch = self._import_torch()
        self.device = self.device or (
            "cuda" if self._torch and getattr(self._torch.cuda, "is_available", lambda: False)() else "cpu"
        )

        self.tokenizer = self._init_tokenizer()
        self._vocab: Dict[str, int] = {}
        self._reverse_vocab: List[str] = []
        self.model = self._load_model()
        self.stub_mode = self.model is None or self._torch is None
        if self.stub_mode:
            logging.warning(
                "SNNLLMBackend running in stub mode; student artifacts are missing or PyTorch is unavailable"
            )

    def _load_metadata(self) -> Dict[str, object]:
        if not self.metadata_path.exists():
            logging.info("SNN metadata %s not found; falling back to defaults", self.metadata_path)
            return {}

        try:
            with self.metadata_path.open("r", encoding="utf-8") as handle:
                metadata = json.load(handle)
            if isinstance(metadata, dict):
                if "vocab_size" in metadata:
                    logging.info("Loaded SNN metadata with vocab_size=%s", metadata.get("vocab_size"))
                if "model_type" in metadata:
                    logging.info("SNN model type: %s", metadata.get("model_type"))
                training_cfg = metadata.get("training_config")
                if isinstance(training_cfg, dict) and training_cfg:
                    logging.info("SNN training config keys: %s", ",".join(sorted(training_cfg.keys())))
                return metadata
            logging.warning("SNN metadata %s is not a mapping; ignoring", self.metadata_path)
            return {}
        except Exception as exc:  # pragma: no cover - defensive fallback
            logging.warning("Failed to parse SNN metadata %s: %s", self.metadata_path, exc)
            return {}

    def _extract_config(self, metadata: Dict[str, object]) -> Dict[str, object]:
        config = metadata.get("config", {}) if isinstance(metadata, dict) else {}
        if isinstance(config, dict):
            return config
        logging.warning("SNN metadata config field is not a mapping; ignoring")
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
        self, prompt: str, max_tokens: int = 64, system_prompt: Optional[str] = None, **_: object
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

"""Teacher heuristic discovery utilities for offline distillation."""
from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from typing import Callable

import torch
from torch import Tensor

LOGGER = logging.getLogger(__name__)

_CANDIDATE_ATTRS: tuple[str, ...] = (
    "teacher_forward",
    "teacher_heuristic",
    "teacher",
    "teacher_model",
    "solve",
    "score",
    "expected_value",
    "expected_gap",
    "predict",
    "forward",
    "_expected_gap",
)


def _call_teacher(func: Callable[[Tensor], Tensor | float], features: Tensor) -> Tensor:
    outputs = func(features)
    if not isinstance(outputs, Tensor):
        outputs = torch.as_tensor(outputs)
    if outputs.ndim == 1:
        outputs = outputs.unsqueeze(1)
    return outputs.to(dtype=features.dtype)


@lru_cache(maxsize=64)
def _resolve_teacher(skill: str) -> Callable[[Tensor], Tensor] | None:
    module_name = f"sdk_python.skills_impl.{skill}"
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        LOGGER.error("Unable to import skill module %s: %s", module_name, exc)
        return None

    for attr in _CANDIDATE_ATTRS:
        candidate = getattr(module, attr, None)
        if callable(candidate):
            LOGGER.debug("Teacher heuristic '%s' selected for %s", attr, skill)
            return lambda features, fn=candidate: _call_teacher(fn, features)

    LOGGER.debug("Falling back to empirical targets for %s; no teacher heuristic exported.", skill)
    return None


def get_teacher_outputs(skill: str, features: Tensor) -> Tensor | None:
    """Return teacher predictions for ``features`` if a heuristic is available."""

    teacher = _resolve_teacher(skill)
    if teacher is None:
        return None

    try:
        return teacher(features)
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.warning("Teacher heuristic for %s failed: %s", skill, exc)
        return None


__all__ = ["get_teacher_outputs"]

"""Template modules for building SmartGlass Ray skills."""

from __future__ import annotations

from .trainer import SkillTrainer, run as run_training
from .eval import MockEvaluator, run as run_eval

try:  # pragma: no cover - optional dependency shim
    from .export_onnx import Int8Exporter, export_int8, run as run_export
except ImportError:  # pragma: no cover
    Int8Exporter = None

    def export_int8(*_, **__):
        raise ImportError("onnxruntime is required to use export_int8")

    def run_export(*_, **__):
        raise ImportError("onnxruntime is required to export skills")

__all__ = [
    "SkillTrainer",
    "run_training",
    "Int8Exporter",
    "export_int8",
    "run_export",
    "MockEvaluator",
    "run_eval",
]

"""Template modules for building SmartGlass Ray skills."""

from .trainer import MockTrainer, run as run_training
from .export_onnx import MockExporter, run as run_export
from .eval import MockEvaluator, run as run_eval

__all__ = [
    "MockTrainer",
    "run_training",
    "MockExporter",
    "run_export",
    "MockEvaluator",
    "run_eval",
]

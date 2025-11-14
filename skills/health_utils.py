"""Shared utilities for health skills."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def export_to_onnx(model: Any, path: Path) -> None:
    """Export model to ONNX format (stub).
    
    This is a placeholder implementation that writes dummy ONNX bytes.
    In production, this would use actual ONNX export functionality.
    
    Args:
        model: Model object to export
        path: Output path for ONNX file
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"ONNX_BINARY_PLACEHOLDER")

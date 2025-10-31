"""Test configuration for ensuring the project package is importable."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def _ensure_project_on_path() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _ensure_perception_vad() -> None:
    if "perception.vad" in sys.modules:
        return

    vad_path = Path(__file__).resolve().parents[1] / "src" / "perception" / "vad.py"
    if not vad_path.exists():
        return

    spec = importlib.util.spec_from_file_location("perception.vad", vad_path)
    if spec is None or spec.loader is None:
        return

    module = importlib.util.module_from_spec(spec)
    perception_pkg = sys.modules.setdefault("perception", types.ModuleType("perception"))
    setattr(perception_pkg, "__path__", [str(vad_path.parent)])
    sys.modules["perception.vad"] = module
    spec.loader.exec_module(module)
    setattr(perception_pkg, "vad", module)


_ensure_project_on_path()
_ensure_perception_vad()


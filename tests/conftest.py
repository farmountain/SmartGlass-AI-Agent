"""Test configuration for ensuring the project package is importable."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_on_path() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_project_on_path()


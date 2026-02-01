"""Test configuration for the SDK Python package."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SRC = ROOT / "sdk_python"

for path in (str(ROOT), str(PACKAGE_SRC)):
    if path not in sys.path:
        sys.path.insert(0, path)

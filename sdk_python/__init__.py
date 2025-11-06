"""Namespace package that exposes the local SDK implementation."""
from __future__ import annotations

from pathlib import Path
import pkgutil

# Extend the package search path so modules defined in ``sdk-python/sdk_python``
# are importable without installing the package.
__path__ = pkgutil.extend_path(__path__, __name__)
_pkg_dir = Path(__file__).resolve().parent.parent / "sdk-python" / "sdk_python"
if _pkg_dir.is_dir():
    __path__.append(str(_pkg_dir))

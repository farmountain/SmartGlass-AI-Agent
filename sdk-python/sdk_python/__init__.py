"""SmartGlass SDK for building Ray-based skills."""

from importlib import import_module
from types import ModuleType
from typing import Any

__all__ = ["raycli", "distill"]


def __getattr__(name: str) -> Any:  # pragma: no cover - trivial passthrough
    if name in __all__:
        module: ModuleType = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

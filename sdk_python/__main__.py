"""Entry point for ``python -m sdk_python`` when using the namespace package."""
from __future__ import annotations

from importlib import import_module


def main() -> int:
    module = import_module("sdk_python.raycli")
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())

"""Test package marker and lightweight stubs for optional dependencies."""

from __future__ import annotations

import sys
import types


def _install_src_stub() -> None:
    if "src" in sys.modules:
        return

    src_module = types.ModuleType("src")
    io_module = types.ModuleType("src.io")
    telemetry_module = types.ModuleType("src.io.telemetry")

    def _log_metric(*args, **kwargs):  # noqa: D401 - simple stub
        return None

    telemetry_module.log_metric = _log_metric
    io_module.telemetry = telemetry_module
    src_module.io = io_module

    sys.modules["src"] = src_module
    sys.modules["src.io"] = io_module
    sys.modules["src.io.telemetry"] = telemetry_module


_install_src_stub()

"""Smoke tests ensuring CI runs never touch real audio integrations."""

from __future__ import annotations

import importlib
import os
import sys


def _reload_src_package() -> None:
    """Remove ``src`` modules from ``sys.modules`` so they import fresh."""

    to_clear = [name for name in sys.modules if name == "src" or name.startswith("src.")]
    for name in to_clear:
        sys.modules.pop(name, None)


def test_ci_env_forces_mock_provider(monkeypatch) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("PROVIDER", "meta")
    monkeypatch.setenv("USE_WHISPER_STREAMING", "1")

    _reload_src_package()
    importlib.import_module("src")

    assert os.getenv("PROVIDER") == "mock"
    assert "USE_WHISPER_STREAMING" not in os.environ


def test_non_ci_env_preserves_configuration(monkeypatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("PROVIDER", "meta")
    monkeypatch.setenv("USE_WHISPER_STREAMING", "1")

    _reload_src_package()
    importlib.import_module("src")

    assert os.getenv("PROVIDER") == "meta"
    assert os.getenv("USE_WHISPER_STREAMING") == "1"

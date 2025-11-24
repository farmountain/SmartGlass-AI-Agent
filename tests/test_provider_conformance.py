"""Provider conformance tests for the hero caption runtime."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from drivers.factory import get_provider
from drivers.providers.meta import MetaRayBanProvider
from drivers.providers.mock import MockAudioOut, MockDisplayOverlay
from examples.hero1_caption import run_hero_pipeline

PROVIDER_NAMES = ("mock", "meta", "vuzix", "xreal", "openxr", "visionos")


@pytest.fixture(autouse=True)
def isolate_metrics_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Write telemetry artifacts into a temporary directory during the test."""

    monkeypatch.setenv("SMARTGLASS_ARTIFACTS_DIR", str(tmp_path))


def _action_json(provider_name: str, monkeypatch: pytest.MonkeyPatch) -> str:
    """Return the JSON payload describing the caption action for ``provider_name``."""

    monkeypatch.setenv("PROVIDER", provider_name)
    provider = get_provider()

    if isinstance(provider, MetaRayBanProvider):
        provider.audio_out = MockAudioOut()
        provider.overlay = MockDisplayOverlay()

    result = run_hero_pipeline(log=False, provider=provider)
    action = {"type": "caption", "text": result["caption"]}
    return json.dumps(action, sort_keys=True)


@pytest.mark.parametrize("provider_name", PROVIDER_NAMES)
def test_runtime_actions_match_baseline(provider_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The caption action JSON must be identical across every provider name."""

    baseline = _action_json("mock", monkeypatch)
    candidate = _action_json(provider_name, monkeypatch)
    assert candidate == baseline

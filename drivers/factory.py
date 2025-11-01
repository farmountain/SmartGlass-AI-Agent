"""Factory helpers for selecting a driver provider implementation."""

from __future__ import annotations

import os
from typing import Union

from .providers.meta import MetaProvider
from .providers.mock import MockProvider
from src.io.telemetry import log_metric

Provider = Union[MockProvider, MetaProvider]


def get_provider() -> Provider:
    """Return a provider instance configured via the ``PROVIDER`` environment variable."""

    provider_name = os.getenv("PROVIDER", "mock").lower()
    if provider_name == "meta":
        provider: Provider = MetaProvider()
    else:
        provider = MockProvider()

    log_metric("sdk.provider", 1, tags={"name": provider_name})

    capability_tags = {
        "camera": bool(getattr(provider, "camera", None)),
        "mic": bool(getattr(provider, "microphone", None)),
        "display": bool(getattr(provider, "overlay", None)),
        "haptics": bool(getattr(provider, "haptics", None)),
    }
    log_metric("sdk.capabilities", 1, tags=capability_tags)

    return provider


__all__ = ["Provider", "get_provider"]

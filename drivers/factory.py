"""Factory helpers for selecting a driver provider implementation."""

from __future__ import annotations

import os

from .providers import BaseProvider, get_provider as _resolve_provider
from src.io.telemetry import log_metric

Provider = BaseProvider


def get_provider(name: str | None = None, **kwargs) -> Provider:
    """Return a provider instance configured via ``name`` or the ``PROVIDER`` env var."""

    provider_name = (name or os.getenv("PROVIDER", "mock") or "mock").lower()
    provider: Provider = _resolve_provider(provider_name, **kwargs)

    log_metric("sdk.provider", 1, tags={"name": provider_name})

    has_display_fn = getattr(provider, "has_display", None)
    display_available = has_display_fn() if callable(has_display_fn) else False

    capability_tags = {
        "camera": provider.open_video_stream() is not None,
        "mic": provider.open_audio_stream() is not None,
        "display": display_available,
        "haptics": provider.get_haptics() is not None,
    }
    log_metric("sdk.capabilities", 1, tags=capability_tags)

    return provider


__all__ = ["Provider", "get_provider"]

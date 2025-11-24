"""Factory helpers for selecting a driver provider implementation."""

from __future__ import annotations

import os
from typing import Callable

from .providers.base import BaseProvider
from .providers.meta import MetaProvider
from .providers.mock import MockProvider
from .providers.openxr_mock import OpenXRMockProvider
from .providers.visionos_mock import VisionOSMockProvider
from .providers.vuzix_mock import VuzixMockProvider
from .providers.xreal_mock import XrealMockProvider
from src.io.telemetry import log_metric

Provider = BaseProvider


def get_provider() -> Provider:
    """Return a provider instance configured via the ``PROVIDER`` environment variable."""

    provider_name = os.getenv("PROVIDER", "mock").lower()
    provider_map: dict[str, Callable[[], Provider]] = {
        "mock": MockProvider,
        "meta": MetaProvider,
        "vuzix": VuzixMockProvider,
        "xreal": XrealMockProvider,
        "openxr": OpenXRMockProvider,
        "visionos": VisionOSMockProvider,
    }
    provider_factory = provider_map.get(provider_name, MockProvider)
    provider: Provider = provider_factory()

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

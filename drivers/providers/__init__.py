"""Provider implementations for driver interfaces."""

from __future__ import annotations

import os
from typing import Callable

from .base import BaseProvider, ProviderBase
from .meta import (
    MetaRayBanAudioOut,
    MetaRayBanCameraIn,
    MetaRayBanDisplayOverlay,
    MetaRayBanHaptics,
    MetaRayBanMicIn,
    MetaRayBanPermissions,
    MetaRayBanProvider,
)
from .mock import (
    MockAudioOut,
    MockCameraIn,
    MockDisplayOverlay,
    MockHaptics,
    MockMicIn,
    MockPermissions,
    MockProvider,
)
from .openxr_mock import (
    OpenXRMockAudioOut,
    OpenXRMockCameraIn,
    OpenXRMockDisplayOverlay,
    OpenXRMockHaptics,
    OpenXRMockMicIn,
    OpenXRMockPermissions,
    OpenXRMockProvider,
)
from .visionos_mock import (
    VisionOSMockAudioOut,
    VisionOSMockCameraIn,
    VisionOSMockDisplayOverlay,
    VisionOSMockHaptics,
    VisionOSMockMicIn,
    VisionOSMockPermissions,
    VisionOSMockProvider,
)
from .vuzix_mock import (
    VuzixMockAudioOut,
    VuzixMockCameraIn,
    VuzixMockDisplayOverlay,
    VuzixMockHaptics,
    VuzixMockMicIn,
    VuzixMockPermissions,
    VuzixMockProvider,
)
from .xreal_mock import (
    XrealMockAudioOut,
    XrealMockCameraIn,
    XrealMockDisplayOverlay,
    XrealMockHaptics,
    XrealMockMicIn,
    XrealMockPermissions,
    XrealMockProvider,
)

Provider = BaseProvider


def get_provider(name: str | None = None, **kwargs) -> Provider:
    """Return a provider instance for the given ``name`` or ``PROVIDER`` env var.

    Supported provider names (case-insensitive): ``mock``, ``meta``, ``vuzix``,
    ``xreal``, ``openxr``, and ``visionos``. Unknown names fall back to the
    generic mock provider. When ``name`` is omitted, the ``PROVIDER``
    environment variable is used (default ``"mock"``).
    """

    provider_name = (name or os.getenv("PROVIDER", "mock") or "mock").lower()
    if provider_name == "meta":
        provider_kwargs = {
            "prefer_sdk": kwargs.pop("prefer_sdk", False),
            "api_key": kwargs.pop("api_key", None),
            "device_id": kwargs.pop("device_id", None),
            "transport": kwargs.pop("transport", "mock"),
        }
        provider_kwargs.update(kwargs)
        return MetaRayBanProvider(**provider_kwargs)

    provider_map: dict[str, Callable[..., Provider]] = {
        "mock": MockProvider,
        "vuzix": VuzixMockProvider,
        "xreal": XrealMockProvider,
        "openxr": OpenXRMockProvider,
        "visionos": VisionOSMockProvider,
    }

    provider_factory = provider_map.get(provider_name, MockProvider)
    return provider_factory(**kwargs)


__all__ = [
    "BaseProvider",
    "Provider",
    "ProviderBase",
    "get_provider",
    "MetaRayBanAudioOut",
    "MetaRayBanCameraIn",
    "MetaRayBanDisplayOverlay",
    "MetaRayBanHaptics",
    "MetaRayBanMicIn",
    "MetaRayBanPermissions",
    "MetaRayBanProvider",
    "MockAudioOut",
    "MockCameraIn",
    "MockDisplayOverlay",
    "MockHaptics",
    "MockMicIn",
    "MockPermissions",
    "MockProvider",
    "OpenXRMockAudioOut",
    "OpenXRMockCameraIn",
    "OpenXRMockDisplayOverlay",
    "OpenXRMockHaptics",
    "OpenXRMockMicIn",
    "OpenXRMockPermissions",
    "OpenXRMockProvider",
    "VisionOSMockAudioOut",
    "VisionOSMockCameraIn",
    "VisionOSMockDisplayOverlay",
    "VisionOSMockHaptics",
    "VisionOSMockMicIn",
    "VisionOSMockPermissions",
    "VisionOSMockProvider",
    "VuzixMockAudioOut",
    "VuzixMockCameraIn",
    "VuzixMockDisplayOverlay",
    "VuzixMockHaptics",
    "VuzixMockMicIn",
    "VuzixMockPermissions",
    "VuzixMockProvider",
    "XrealMockAudioOut",
    "XrealMockCameraIn",
    "XrealMockDisplayOverlay",
    "XrealMockHaptics",
    "XrealMockMicIn",
    "XrealMockPermissions",
    "XrealMockProvider",
]

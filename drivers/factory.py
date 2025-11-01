"""Factory helpers for selecting a driver provider implementation."""

from __future__ import annotations

import os
from typing import Union

from .providers.meta import MetaProvider
from .providers.mock import MockProvider

Provider = Union[MockProvider, MetaProvider]


def get_provider() -> Provider:
    """Return a provider instance configured via the ``PROVIDER`` environment variable."""

    provider_name = os.getenv("PROVIDER", "mock").lower()
    if provider_name == "meta":
        return MetaProvider()
    return MockProvider()


__all__ = ["Provider", "get_provider"]

"""Interface compliance tests for the driver abstraction layer."""

from __future__ import annotations

import inspect
from typing import Type

import pytest

from drivers.interfaces import (
    AudioOut,
    CameraIn,
    DisplayOverlay,
    Haptics,
    MicIn,
    Permissions,
)
from drivers.providers.meta import (
    MetaAudioOut,
    MetaCameraIn,
    MetaDisplayOverlay,
    MetaHaptics,
    MetaMicIn,
    MetaPermissions,
    MetaProvider,
)
from drivers.providers.mock import (
    MockAudioOut,
    MockCameraIn,
    MockDisplayOverlay,
    MockHaptics,
    MockMicIn,
    MockPermissions,
    MockProvider,
)


INTERFACE_METHODS = {
    CameraIn: ("camera", ["get_frame"]),
    MicIn: ("microphone", ["get_audio_chunk"]),
    AudioOut: ("audio_out", ["play_audio"]),
    DisplayOverlay: ("overlay", ["show_text"]),
    Haptics: ("haptics", ["pulse"]),
    Permissions: ("permissions", ["has_permission", "require"]),
}

MOCK_COMPONENT_TYPES = {
    "camera": MockCameraIn,
    "microphone": MockMicIn,
    "audio_out": MockAudioOut,
    "overlay": MockDisplayOverlay,
    "haptics": MockHaptics,
    "permissions": MockPermissions,
}

META_COMPONENT_TYPES = {
    "camera": MetaCameraIn,
    "microphone": MetaMicIn,
    "audio_out": MetaAudioOut,
    "overlay": MetaDisplayOverlay,
    "haptics": MetaHaptics,
    "permissions": MetaPermissions,
}


@pytest.mark.parametrize(
    "provider_cls, component_types",
    [
        (MockProvider, MOCK_COMPONENT_TYPES),
        (MetaProvider, META_COMPONENT_TYPES),
    ],
)
def test_provider_components_exist_and_have_required_methods(
    provider_cls: Type, component_types: dict[str, Type]
) -> None:
    provider = provider_cls()

    for interface, (attribute, methods) in INTERFACE_METHODS.items():
        component = getattr(provider, attribute)

        expected_type = component_types[attribute]
        assert isinstance(
            component, expected_type
        ), f"{attribute} should be an instance of {expected_type.__name__}"

        for method_name in methods:
            method = getattr(component, method_name, None)
            assert callable(method), (
                f"{component.__class__.__name__}.{method_name} must be callable"
            )


COMPONENT_PROTOCOLS = [
    (MockCameraIn, CameraIn),
    (MockMicIn, MicIn),
    (MockAudioOut, AudioOut),
    (MockDisplayOverlay, DisplayOverlay),
    (MockHaptics, Haptics),
    (MockPermissions, Permissions),
    (MetaCameraIn, CameraIn),
    (MetaMicIn, MicIn),
    (MetaAudioOut, AudioOut),
    (MetaDisplayOverlay, DisplayOverlay),
    (MetaHaptics, Haptics),
    (MetaPermissions, Permissions),
]


@pytest.mark.parametrize("component_cls, protocol_type", COMPONENT_PROTOCOLS)
def test_components_public_api_matches_protocol(
    component_cls: Type, protocol_type: Type
) -> None:
    _, expected_methods = INTERFACE_METHODS[protocol_type]

    public_methods = {
        name
        for name, member in inspect.getmembers(component_cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    missing = set(expected_methods) - public_methods
    assert not missing, f"{component_cls.__name__} missing methods: {sorted(missing)}"

    extra = public_methods - set(expected_methods)
    assert not extra, f"{component_cls.__name__} has unexpected public methods: {sorted(extra)}"

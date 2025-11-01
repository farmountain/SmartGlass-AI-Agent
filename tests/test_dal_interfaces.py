"""Tests for the device abstraction layer protocol definitions."""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from typing import get_args, get_origin, get_type_hints

import numpy as np

from drivers import AudioOut, CameraIn, DisplayOverlay, Haptics, MicIn, Permissions

def test_interfaces_are_importable() -> None:
    assert inspect.isclass(CameraIn)
    assert inspect.isclass(MicIn)
    assert inspect.isclass(AudioOut)
    assert inspect.isclass(DisplayOverlay)
    assert inspect.isclass(Haptics)
    assert inspect.isclass(Permissions)


def test_camera_protocol_method_signature() -> None:
    method = CameraIn.get_frames
    hints = get_type_hints(method)
    origin = get_origin(hints["return"])
    assert origin is Iterator
    (inner_type,) = get_args(hints["return"])
    assert inner_type is np.ndarray


def test_mic_protocol_method_signature() -> None:
    method = MicIn.get_frames
    hints = get_type_hints(method)
    origin = get_origin(hints["return"])
    assert origin is Iterator
    (inner_type,) = get_args(hints["return"])
    assert inner_type is np.ndarray


def test_audio_out_protocol_signature() -> None:
    method = AudioOut.speak
    hints = get_type_hints(method)
    assert hints["return"] is dict


def test_overlay_protocol_signature() -> None:
    method = DisplayOverlay.render
    hints = get_type_hints(method)
    assert hints["return"] is dict


def test_haptics_protocol_signature() -> None:
    method = Haptics.vibrate
    hints = get_type_hints(method)
    assert hints["return"] is type(None)


def test_permissions_protocol_signature() -> None:
    method = Permissions.request
    hints = get_type_hints(method)
    assert hints["return"] is dict

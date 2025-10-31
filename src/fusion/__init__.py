"""Fusion utilities for the SmartGlass agent."""

from __future__ import annotations

from .confidence import ConfidenceFusion as LegacyConfidenceFusion, FusionResult
from .gate_mi import (
    ConfidenceFusion as ConfidenceFusionMI,
    alpha_from_conf,
    clip01,
    sigmoid,
    smooth_alpha,
)

# Maintain backward compatibility with the legacy fusion class while exposing
# the mutual-information gate introduced in Week-4.
ConfidenceFusion = LegacyConfidenceFusion

__all__ = [
    "ConfidenceFusion",
    "FusionResult",
    "LegacyConfidenceFusion",
    "ConfidenceFusionMI",
    "sigmoid",
    "clip01",
    "alpha_from_conf",
    "smooth_alpha",
]

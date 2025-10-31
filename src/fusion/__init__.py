"""Lightweight fusion utilities for SmartGlass AI."""

from .gate_mi import (
    ConfidenceFusion,
    alpha_from_conf,
    clip01,
    sigmoid,
    smooth_alpha,
)

__all__ = [
    "ConfidenceFusion",
    "alpha_from_conf",
    "clip01",
    "sigmoid",
    "smooth_alpha",
]

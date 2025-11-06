"""Synthetic linear equation dataset for the education skill pack."""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 1, "test": 2}


def _sample_parameters(
    num_samples: int, *, generator: torch.Generator
) -> tuple[Tensor, Tensor, Tensor]:
    slope = torch.randint(-5, 6, (num_samples, 1), generator=generator, dtype=torch.float32)
    intercept = torch.randint(-10, 11, (num_samples, 1), generator=generator, dtype=torch.float32)
    x_value = torch.randint(-8, 9, (num_samples, 1), generator=generator, dtype=torch.float32)
    return slope, intercept, x_value


def load_synthesized_dataset(
    *, split: str, num_samples: int, seed: int
) -> SynthesizedDataset:
    """Generate a regression dataset for ``y = m * x + b`` style problems."""

    offset = _SPLIT_OFFSET.get(split, 0)
    generator = torch.Generator().manual_seed(seed + offset)

    slope, intercept, x_value = _sample_parameters(num_samples, generator=generator)
    features = torch.cat([slope, intercept, x_value], dim=1)

    noise_std = 0.05
    noise = torch.randn(num_samples, 1, generator=generator) * noise_std
    targets = slope * x_value + intercept + noise

    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def _format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-4:
        return str(int(round(value)))
    return f"{value:.2f}"


def features_to_y_form(features: Tensor) -> list[str]:
    """Convert feature rows into linear equation strings."""

    if features.ndim != 2 or features.shape[1] < 3:
        raise ValueError("features must be a 2D tensor with three columns")

    slopes = features[:, 0].tolist()
    intercepts = features[:, 1].tolist()
    inputs = features[:, 2].tolist()

    y_forms: list[str] = []
    for slope, intercept, x_value in zip(slopes, intercepts, inputs):
        slope_str = _format_number(slope)
        intercept_str = _format_number(intercept)
        x_str = _format_number(x_value)
        sign = "+" if intercept >= 0 else "-"
        intercept_display = intercept_str if intercept >= 0 else intercept_str.lstrip("-")
        y_forms.append(f"y = {slope_str}x {sign} {intercept_display} | x = {x_str}")
    return y_forms

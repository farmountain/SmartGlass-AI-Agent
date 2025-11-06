"""Synthetic ratio-to-percent dataset for the education skill pack."""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 1, "test": 2}


def _sample_components(
    num_samples: int, *, generator: torch.Generator
) -> tuple[Tensor, Tensor]:
    whole = torch.randint(20, 201, (num_samples, 1), generator=generator, dtype=torch.float32)
    percentages = torch.randint(5, 96, (num_samples, 1), generator=generator, dtype=torch.float32)
    part = torch.clamp(torch.round(whole * percentages / 100), min=1.0)
    return part, whole


def load_synthesized_dataset(
    *, split: str, num_samples: int, seed: int
) -> SynthesizedDataset:
    """Generate part/whole problems that map to percentage answers."""

    offset = _SPLIT_OFFSET.get(split, 0)
    generator = torch.Generator().manual_seed(seed + offset)

    part, whole = _sample_components(num_samples, generator=generator)
    features = torch.cat([part, whole], dim=1)

    noise_std = 0.1
    noise = torch.randn(num_samples, 1, generator=generator) * noise_std
    percent = (part / whole) * 100 + noise
    return SynthesizedDataset(features=features, targets=percent, noise_std=float(noise_std))


def _format_ratio_value(value: float) -> str:
    if abs(value - round(value)) < 1e-4:
        return str(int(round(value)))
    return f"{value:.1f}"


def features_to_y_form(features: Tensor) -> list[str]:
    """Render the ratio as a percentage statement."""

    if features.ndim != 2 or features.shape[1] < 2:
        raise ValueError("features must be a 2D tensor with two columns")

    parts = features[:, 0].tolist()
    wholes = features[:, 1].tolist()

    y_forms: list[str] = []
    for part, whole in zip(parts, wholes):
        percent = 100 * part / whole if whole != 0 else 0.0
        part_str = _format_ratio_value(part)
        whole_str = _format_ratio_value(whole)
        percent_str = (
            f"{percent:.1f}" if abs(percent - round(percent)) > 1e-4 else str(int(round(percent)))
        )
        y_forms.append(f"{part_str} of {whole_str} -> {percent_str}%")
    return y_forms

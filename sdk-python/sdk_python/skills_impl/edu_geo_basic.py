"""Synthetic geometry dataset focused on basic area computations."""
from __future__ import annotations

import math

import torch
import torch.nn.functional as F
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 1, "test": 2}
_SHAPES = ("rectangle", "triangle", "circle")


def _sample_shapes(num_samples: int, *, generator: torch.Generator) -> tuple[Tensor, Tensor]:
    shape_ids = torch.randint(0, len(_SHAPES), (num_samples,), generator=generator)
    dimensions = torch.randint(2, 13, (num_samples, 2), generator=generator, dtype=torch.float32)
    return shape_ids, dimensions


def load_synthesized_dataset(
    *, split: str, num_samples: int, seed: int
) -> SynthesizedDataset:
    """Generate area estimation problems for rectangles, triangles and circles."""

    offset = _SPLIT_OFFSET.get(split, 0)
    generator = torch.Generator().manual_seed(seed + offset)

    shape_ids, dims = _sample_shapes(num_samples, generator=generator)
    # Ensure circle samples only use the first dimension as radius.
    circle_mask = shape_ids == 2
    dims[circle_mask, 1] = 0.0

    one_hot = F.one_hot(shape_ids, num_classes=len(_SHAPES)).to(torch.float32)
    features = torch.cat([one_hot, dims], dim=1)

    areas = torch.empty(num_samples, 1, dtype=torch.float32)
    rectangle_mask = shape_ids == 0
    triangle_mask = shape_ids == 1

    areas[rectangle_mask] = (dims[rectangle_mask, 0] * dims[rectangle_mask, 1]).unsqueeze(-1)
    areas[triangle_mask] = (0.5 * dims[triangle_mask, 0] * dims[triangle_mask, 1]).unsqueeze(-1)
    radius = dims[circle_mask, 0]
    areas[circle_mask] = (math.pi * radius.pow(2)).unsqueeze(-1)

    noise_std = 0.2
    noise = torch.randn(num_samples, 1, generator=generator) * noise_std
    targets = areas + noise
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def _format_dimension(value: float) -> str:
    if abs(value - round(value)) < 1e-4:
        return str(int(round(value)))
    return f"{value:.1f}"


def features_to_y_form(features: Tensor) -> list[str]:
    """Produce natural language area descriptions for each feature row."""

    if features.ndim != 2 or features.shape[1] < len(_SHAPES) + 2:
        raise ValueError("features must include one-hot shape encoding and two dimensions")

    shape_tokens = features[:, : len(_SHAPES)]
    dims = features[:, len(_SHAPES) :]

    y_forms: list[str] = []
    for token, pair in zip(shape_tokens, dims):
        shape_id = int(torch.argmax(token).item())
        shape_name = _SHAPES[shape_id]
        a, b = pair.tolist()
        if shape_name == "rectangle":
            y_forms.append(
                f"rectangle area = {_format_dimension(a)} × {_format_dimension(b)}"
            )
        elif shape_name == "triangle":
            y_forms.append(
                f"triangle area = 0.5 × {_format_dimension(a)} × {_format_dimension(b)}"
            )
        else:
            y_forms.append(f"circle area = π × {_format_dimension(a)}²")
    return y_forms

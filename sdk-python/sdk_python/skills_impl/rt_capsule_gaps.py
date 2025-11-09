"""Synthetic dataset modeling wardrobe capsule gaps for retail recommendations.

Feature layout:
    [0] current_item_count (number of items in category)
    [1] season_match_score (0.0–1.0)
    [2] style_versatility_index (0.0–1.0)
    [3] color_palette_fit (0.0–1.0)
    [4] budget_remaining (USD)
"""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 31, "test": 59}


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    item_count = torch.randint(2, 25, (num_samples,), generator=generator, dtype=torch.float32)
    season_match = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    versatility = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    color_fit = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    budget = torch.rand((num_samples,), generator=generator, dtype=torch.float32) * 800 + 200
    return torch.stack(
        [item_count, season_match, versatility, color_fit, budget], dim=1
    )


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate capsule gap scores for wardrobe recommendations."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)

    item_count = features[:, 0]
    season_match = features[:, 1]
    versatility = features[:, 2]
    color_fit = features[:, 3]
    budget = features[:, 4]

    # Gap priority score: higher when few items, good seasonal match, versatile, and fits palette
    # Modulated by available budget
    scarcity_factor = 1.0 / (0.5 + item_count / 30.0)
    quality_score = (season_match + versatility + color_fit) / 3.0
    budget_enabler = torch.clamp(budget / 500.0, min=0.4, max=1.8)
    
    gap_priority = 50.0 * scarcity_factor * quality_score * budget_enabler

    noise_std = 3.2
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = gap_priority.unsqueeze(1) + noise
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    """Translate capsule gap features into natural language descriptions."""

    if features.ndim != 2 or features.shape[1] != 5:
        raise ValueError("features must be a (N, 5) tensor for rt_capsule_gaps")

    summaries: list[str] = []
    for count, season, versatility, color, budget in features.tolist():
        summaries.append(
            (
                f"Capsule Gaps input: {int(count)} items, season match {season:.2f}, "
                f"versatility {versatility:.2f}, color fit {color:.2f}, "
                f"budget ${budget:.2f}."
            )
        )
    return summaries

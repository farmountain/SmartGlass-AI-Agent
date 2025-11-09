"""Synthetic dataset modeling Willingness-to-Pay (WTP) for retail products.

Feature layout:
    [0] product_base_price (USD)
    [1] brand_reputation_score (0.0–1.0)
    [2] customer_income_percentile (0.0–1.0)
    [3] product_uniqueness_index (0.0–1.0)
    [4] competitor_price_ratio (0.7–1.5)
"""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 19, "test": 47}


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    base_price = torch.rand((num_samples,), generator=generator, dtype=torch.float32) * 450 + 50
    brand_score = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    income_percentile = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    uniqueness = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    competitor_ratio = torch.rand((num_samples,), generator=generator, dtype=torch.float32) * 0.8 + 0.7
    return torch.stack(
        [base_price, brand_score, income_percentile, uniqueness, competitor_ratio], dim=1
    )


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate WTP predictions for retail product pricing scenarios."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)

    base_price = features[:, 0]
    brand_score = features[:, 1]
    income = features[:, 2]
    uniqueness = features[:, 3]
    competitor_ratio = features[:, 4]

    # WTP model: customers willing to pay more for strong brands, unique products
    # and when they have higher income, but less when competitors are cheaper
    brand_premium = 1.0 + 0.35 * brand_score
    income_multiplier = 0.85 + 0.3 * income
    uniqueness_boost = 1.0 + 0.25 * uniqueness
    # Higher competitor_ratio means competitors are more expensive (good for us)
    # Lower competitor_ratio means competitors are cheaper (bad for us)
    competitive_adjustment = 0.7 + 0.5 * (competitor_ratio - 0.7) / 0.8
    
    wtp = base_price * brand_premium * income_multiplier * uniqueness_boost * competitive_adjustment

    noise_std = 12.5
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = wtp.unsqueeze(1) + noise
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    """Describe WTP scenarios in natural language."""

    if features.ndim != 2 or features.shape[1] != 5:
        raise ValueError("features must be a (N, 5) tensor for rt_wtp_radar")

    descriptions: list[str] = []
    for base, brand, income, unique, comp_ratio in features.tolist():
        descriptions.append(
            (
                f"WTP Radar input: base price ${base:.2f}, brand score {brand:.2f}, "
                f"income percentile {income:.2f}, uniqueness {unique:.2f}, "
                f"competitor ratio {comp_ratio:.2f}."
            )
        )
    return descriptions

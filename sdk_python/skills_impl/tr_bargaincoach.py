"""Synthetic dataset modeling BargainCoach airfare pricing scenarios.

Feature layout:
    [0] route_distance_km
    [1] demand_index (0.0–1.0)
    [2] days_until_departure
    [3] loyalty_tier_basic (1.0 if customer is Basic)
    [4] loyalty_tier_silver (1.0 if customer is Silver)
    [5] loyalty_tier_gold (1.0 if customer is Gold)
"""
from __future__ import annotations

import torch
from torch import Tensor
from torch.nn import functional as F

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 23, "test": 61}
_LOYALTY_NAMES = ("Basic", "Silver", "Gold")


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    distance = torch.randint(300, 4001, (num_samples,), generator=generator, dtype=torch.float32)
    demand = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    advance = torch.randint(5, 121, (num_samples,), generator=generator, dtype=torch.float32)
    loyalty_ids = torch.randint(0, len(_LOYALTY_NAMES), (num_samples,), generator=generator)
    loyalty_one_hot = F.one_hot(loyalty_ids, num_classes=len(_LOYALTY_NAMES)).to(torch.float32)
    return torch.cat([distance.unsqueeze(1), demand.unsqueeze(1), advance.unsqueeze(1), loyalty_one_hot], dim=1)


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate BargainCoach airfare predictions for given itinerary features."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)

    distance = features[:, 0]
    demand = features[:, 1]
    advance = features[:, 2]
    loyalty_matrix = features[:, 3:]

    base_price = 0.11 * distance + 32
    demand_multiplier = 1.0 + 0.9 * demand
    advance_discount = 1.0 - torch.clamp((advance - 21) * 0.004, min=-0.25, max=0.35)
    loyalty_discount = torch.tensor([0.0, 0.07, 0.12], dtype=torch.float32, device=features.device)
    loyalty_adjustment = 1.0 - loyalty_matrix @ loyalty_discount
    airfare = base_price * demand_multiplier * advance_discount * loyalty_adjustment

    noise_std = 8.0
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = airfare.unsqueeze(1) + noise
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    """Summarize BargainCoach airfare inputs as pricing prompts."""

    if features.ndim != 2 or features.shape[1] != 6:
        raise ValueError("features must be a (N, 6) tensor for tr_bargaincoach")

    statements: list[str] = []
    for row in features.tolist():
        distance, demand, advance, basic, silver, gold = row
        tier_index = max(range(len(_LOYALTY_NAMES)), key=lambda idx: row[3 + idx])
        tier_name = _LOYALTY_NAMES[tier_index]
        statements.append(
            (
                "BargainCoach fare input: "
                f"{distance:.0f} km route, demand index {demand:.2f}, {advance:.0f} days out, "
                f"loyalty tier {tier_name}."
            )
        )
    return statements

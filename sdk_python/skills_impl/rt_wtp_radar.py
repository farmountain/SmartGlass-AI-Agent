"""Synthetic dataset modelling retail willingness-to-pay (WTP) signals."""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 41, "test": 83}
MIN_WTP = 15.0
MAX_WTP = 240.0


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    price_anchor = torch.rand((num_samples,), generator=generator) * 140 + 20
    loyalty_index = torch.rand((num_samples,), generator=generator)
    brand_affinity = torch.rand((num_samples,), generator=generator)
    competitor_pressure = torch.rand((num_samples,), generator=generator)
    promo_visibility = torch.rand((num_samples,), generator=generator)
    inventory_pressure = torch.rand((num_samples,), generator=generator)

    return torch.stack(
        (
            price_anchor,
            loyalty_index,
            brand_affinity,
            competitor_pressure,
            promo_visibility,
            inventory_pressure,
        ),
        dim=1,
    )


def estimate_wtp(features: Tensor) -> Tensor:
    """Return the baseline WTP estimate (without stochastic noise)."""

    if features.ndim != 2 or features.shape[1] != 6:
        raise ValueError("features must be a (N, 6) tensor for rt_wtp_radar")

    price_anchor = features[:, 0]
    loyalty = features[:, 1]
    affinity = features[:, 2]
    competition = features[:, 3]
    promo = features[:, 4]
    inventory = features[:, 5]

    base_factor = 0.52 + 0.28 * loyalty + 0.18 * affinity
    promo_boost = 0.14 * promo
    competition_penalty = 0.33 * competition
    inventory_penalty = 0.18 * inventory

    raw_wtp = price_anchor * (base_factor + promo_boost - competition_penalty - inventory_penalty)
    loyalty_bonus = 9.0 * loyalty + 6.0 * affinity
    scarcity_bonus = torch.where(inventory < 0.25, 12.0 * (0.25 - inventory), torch.zeros_like(inventory))

    wtp = raw_wtp + loyalty_bonus + scarcity_bonus
    return wtp.clamp(min=MIN_WTP, max=MAX_WTP)


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate synthetic retail WTP survey outcomes."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)
    baseline = estimate_wtp(features)

    noise_std = 4.5
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = baseline.unsqueeze(1) + noise
    targets.clamp_(min=MIN_WTP, max=MAX_WTP)

    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    """Describe each WTP scenario in natural language."""

    if features.ndim != 2 or features.shape[1] != 6:
        raise ValueError("features must be a (N, 6) tensor for rt_wtp_radar")

    rows: list[str] = []
    for anchor, loyalty, affinity, competitor, promo, inventory in features.tolist():
        promo_state = "visible" if promo >= 0.5 else "hidden"
        loyalty_tier = "loyal" if loyalty >= 0.6 else "casual"
        competitor_status = "heavy" if competitor >= 0.6 else "light"
        inventory_state = "scarce" if inventory <= 0.25 else "plentiful"
        rows.append(
            (
                "WTP radar input: anchor price ${anchor:.0f}, {loyalty_tier} shopper, "
                "brand affinity {affinity:.2f}, competitor pressure {competitor_status}, "
                f"promo {promo_state}, inventory {inventory_state}."
            ).format(
                anchor=anchor, loyalty_tier=loyalty_tier, affinity=affinity, competitor_status=competitor_status
            )
        )
    return rows


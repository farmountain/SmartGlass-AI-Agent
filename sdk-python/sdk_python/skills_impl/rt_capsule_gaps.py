"""Synthetic dataset estimating capsule inventory gaps for retail planning."""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 3, "validation": 47, "test": 91}
MAX_GAP = 800.0


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    subscribers = torch.randint(200, 2001, (num_samples,), generator=generator, dtype=torch.float32)
    order_frequency = torch.randint(1, 13, (num_samples,), generator=generator, dtype=torch.float32)
    mix_diversity = torch.rand((num_samples,), generator=generator)
    promotion_intensity = torch.rand((num_samples,), generator=generator)
    logistics_delay = torch.rand((num_samples,), generator=generator) * 5.0

    return torch.stack(
        (
            subscribers,
            order_frequency,
            mix_diversity,
            promotion_intensity,
            logistics_delay,
        ),
        dim=1,
    )


def _expected_gap(features: Tensor) -> Tensor:
    if features.ndim != 2 or features.shape[1] != 5:
        raise ValueError("features must be a (N, 5) tensor for rt_capsule_gaps")

    subscribers = features[:, 0]
    order_frequency = features[:, 1]
    mix_diversity = features[:, 2]
    promotion = features[:, 3]
    delay_days = features[:, 4]

    monthly_orders = subscribers * (order_frequency / 12.0)
    promotion_lift = 1.0 + 0.35 * promotion
    diversity_cushion = 1.0 - 0.25 * mix_diversity
    delay_penalty = 1.0 + 0.18 * delay_days

    gap = monthly_orders * promotion_lift * diversity_cushion * delay_penalty
    return gap.clamp(min=0.0, max=MAX_GAP)


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate capsule assortment inventory gap estimates."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)
    baseline = _expected_gap(features)

    noise_std = 25.0
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = baseline.unsqueeze(1) + noise
    targets.clamp_(min=0.0, max=MAX_GAP)

    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    """Describe the capsule planning scenario in natural language."""

    if features.ndim != 2 or features.shape[1] != 5:
        raise ValueError("features must be a (N, 5) tensor for rt_capsule_gaps")

    rows: list[str] = []
    for subs, freq, diversity, promo, delay in features.tolist():
        promo_label = "strong" if promo >= 0.6 else "muted"
        diversity_label = "broad" if diversity >= 0.5 else "narrow"
        rows.append(
            (
                "Capsule gap input: {subs} subscribers, {freq:.0f} orders/mo, mix {diversity_label}, "
                "promotion {promo_label}, logistics delay {delay:.1f} days."
            ).format(
                subs=int(subs), freq=freq, diversity_label=diversity_label, promo_label=promo_label, delay=delay
            )
        )
    return rows


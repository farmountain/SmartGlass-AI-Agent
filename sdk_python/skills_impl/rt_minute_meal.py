"""Synthetic dataset forecasting throughput for quick-service meal prep."""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 5, "validation": 53, "test": 101}
MIN_CYCLE = 2.0
MAX_CYCLE = 18.0


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    orders_per_hour = torch.randint(50, 301, (num_samples,), generator=generator, dtype=torch.float32)
    staffing = torch.randint(5, 26, (num_samples,), generator=generator, dtype=torch.float32)
    prep_efficiency = torch.rand((num_samples,), generator=generator)
    ingredient_ready = torch.rand((num_samples,), generator=generator)
    packaging_latency = torch.rand((num_samples,), generator=generator) * 10.0

    return torch.stack(
        (
            orders_per_hour,
            staffing,
            prep_efficiency,
            ingredient_ready,
            packaging_latency,
        ),
        dim=1,
    )


def _cycle_time(features: Tensor) -> Tensor:
    if features.ndim != 2 or features.shape[1] != 5:
        raise ValueError("features must be a (N, 5) tensor for rt_minute_meal")

    orders = features[:, 0]
    staffing = features[:, 1].clamp(min=1.0)
    prep = features[:, 2]
    ready = features[:, 3]
    packaging = features[:, 4]

    load_per_staff = orders / staffing
    efficiency_factor = 1.35 - 0.55 * prep - 0.35 * ready
    packaging_factor = 1.0 + packaging / 12.0

    cycle = load_per_staff * 0.18 * efficiency_factor * packaging_factor
    cycle = torch.where(prep + ready > 1.6, cycle * 0.85, cycle)
    return cycle.clamp(min=MIN_CYCLE, max=MAX_CYCLE)


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate quick-service cycle time estimates."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)
    baseline = _cycle_time(features)

    noise_std = 0.75
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = baseline.unsqueeze(1) + noise
    targets.clamp_(min=MIN_CYCLE, max=MAX_CYCLE)

    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    """Describe the meal assembly scenario in natural language."""

    if features.ndim != 2 or features.shape[1] != 5:
        raise ValueError("features must be a (N, 5) tensor for rt_minute_meal")

    rows: list[str] = []
    for orders, staffing, prep, ready, latency in features.tolist():
        throughput_band = "rush" if orders >= 220 else "steady"
        staffing_label = "lean" if staffing < 12 else "well staffed"
        rows.append(
            (
                "Minute meal input: {orders:.0f} orders/hr ({throughput}), {staffing_label} crew of {staffing:.0f}, "
                "prep efficiency {prep:.2f}, ingredient readiness {ready:.2f}, packaging latency {latency:.1f} min."
            ).format(
                orders=orders,
                throughput=throughput_band,
                staffing_label=staffing_label,
                staffing=staffing,
                prep=prep,
                ready=ready,
                latency=latency,
            )
        )
    return rows


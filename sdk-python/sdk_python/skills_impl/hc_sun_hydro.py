"""Synthetic solar exposure and hydration coaching skill with sigma gating."""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 19, "validation": 61, "test": 107}


def _sigma_gate(values: Tensor, *, pivot: float, scale: float) -> Tensor:
    return torch.sigmoid((values - pivot) * scale)


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    uv_index = torch.rand((num_samples,), generator=generator) * 11  # 0-11 UV scale
    ambient_temp = torch.rand((num_samples,), generator=generator) * 25 + 18  # 18-43 C
    activity_level = torch.rand((num_samples,), generator=generator)
    hydration_level = torch.rand((num_samples,), generator=generator)
    sunscreen_factor = torch.rand((num_samples,), generator=generator) * 0.8 + 0.2
    exposure_minutes = torch.rand((num_samples,), generator=generator) * 160 + 20
    return torch.stack(
        (
            uv_index,
            ambient_temp,
            activity_level,
            hydration_level,
            sunscreen_factor,
            exposure_minutes,
        ),
        dim=1,
    )


def _stress_index(features: Tensor) -> Tensor:
    if features.ndim != 2 or features.shape[1] != 6:
        raise ValueError("features must be a (N, 6) tensor for hc_sun_hydro")

    uv_index, temp_c, activity, hydration, sunscreen, exposure = features.T

    uv_gate = _sigma_gate(uv_index, pivot=7.0, scale=0.9)
    temp_gate = _sigma_gate(temp_c, pivot=32.0, scale=0.4)
    activity_gate = _sigma_gate(activity, pivot=0.65, scale=6.0)
    hydration_relief = 0.55 * _sigma_gate(0.85 - hydration, pivot=0.0, scale=9.0)
    sunscreen_relief = 0.5 * _sigma_gate(0.55 - sunscreen, pivot=0.0, scale=8.0)
    duration_gate = _sigma_gate(exposure, pivot=75.0, scale=0.045)

    base = 15.0 + 40.0 * uv_gate + 28.0 * temp_gate + 24.0 * activity_gate + 18.0 * duration_gate
    mitigation = 1.0 + hydration_relief + sunscreen_relief
    risk = base * mitigation
    return risk.clamp(min=12.0, max=96.0)


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate sun-hydration stress scores."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)
    baseline = _stress_index(features)

    noise_std = 5.0
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = baseline.unsqueeze(1) + noise
    targets.clamp_(min=12.0, max=96.0)
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    if features.ndim != 2 or features.shape[1] != 6:
        raise ValueError("features must be a (N, 6) tensor for hc_sun_hydro")

    rows: list[str] = []
    for uv, temp_c, activity, hydration, sunscreen, exposure in features.tolist():
        rows.append(
            (
                "Sun Hydro input: UV index {uv:.1f}, temp {temp_c:.1f}C, activity {activity:.2f}, hydration {hydration:.2f}, "
                "sunscreen factor {sunscreen:.2f}, exposure {exposure:.0f} min."
            ).format(
                uv=uv,
                temp_c=temp_c,
                activity=activity,
                hydration=hydration,
                sunscreen=sunscreen,
                exposure=exposure,
            )
        )
    return rows

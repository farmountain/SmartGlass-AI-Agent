"""Synthetic dataset estimating in-flight exposure risk for SafeBubble."""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 13, "test": 37}

_FEATURE_LAYOUT = (
    "seat_spacing_cm",
    "mask_compliance_ratio",
    "hepa_filter_rating",
    "flight_duration_hours",
    "crowding_index",
)


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    seat_spacing = torch.randint(70, 101, (num_samples,), generator=generator, dtype=torch.float32)
    mask_compliance = torch.rand((num_samples,), generator=generator, dtype=torch.float32) * 0.4 + 0.6
    hepa_rating = torch.randint(3, 6, (num_samples,), generator=generator, dtype=torch.float32)
    flight_duration = torch.rand((num_samples,), generator=generator, dtype=torch.float32) * 10 + 2
    crowding = torch.rand((num_samples,), generator=generator, dtype=torch.float32) * 0.6 + 0.2
    return torch.stack(
        [seat_spacing, mask_compliance, hepa_rating, flight_duration, crowding], dim=1
    )


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate SafeBubble exposure scores for different flight conditions."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)

    seat_spacing = features[:, 0]
    mask_compliance = features[:, 1]
    hepa_rating = features[:, 2]
    flight_duration = features[:, 3]
    crowding = features[:, 4]

    baseline_risk = 0.12 * flight_duration + 2.1 * crowding
    mitigation = 0.015 * (seat_spacing - 70) + 1.7 * mask_compliance + 0.45 * hepa_rating
    exposure_risk = torch.clamp(baseline_risk - mitigation, min=0.05)

    noise_std = 0.18
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = exposure_risk.unsqueeze(1) + noise
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    """Translate feature rows into SafeBubble exposure descriptions."""

    if features.ndim != 2 or features.shape[1] != len(_FEATURE_LAYOUT):
        raise ValueError(
            f"features must be a (N, {len(_FEATURE_LAYOUT)}) tensor for tr_safebubble"
        )

    summaries: list[str] = []
    for spacing, mask, hepa, duration, crowd in features.tolist():
        summaries.append(
            (
                "SafeBubble exposure input: "
                f"{spacing:.0f}cm spacing, {mask:.0%} masks, HEPA {hepa:.0f}, "
                f"{duration:.1f}h flight, crowding index {crowd:.2f}."
            )
        )
    return summaries

"""Synthetic gait stability monitoring skill with sigma gating."""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 37, "test": 79}


def _sigma_gate(values: Tensor, *, pivot: float, scale: float) -> Tensor:
    """Logistic gate that emphasizes deviations around ``pivot``."""

    return torch.sigmoid((values - pivot) * scale)


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    stride_cadence = torch.rand((num_samples,), generator=generator) * 60 + 70  # 70-130 spm
    sway_variance = torch.rand((num_samples,), generator=generator)  # 0-1 unitless sway
    foot_clearance = torch.rand((num_samples,), generator=generator) * 3.5 + 0.5  # cm
    fatigue_index = torch.rand((num_samples,), generator=generator)
    assistive_flag = (torch.rand((num_samples,), generator=generator) < 0.32).to(torch.float32)
    sensor_confidence = torch.rand((num_samples,), generator=generator) * 0.4 + 0.6
    return torch.stack(
        (
            stride_cadence,
            sway_variance,
            foot_clearance,
            fatigue_index,
            assistive_flag,
            sensor_confidence,
        ),
        dim=1,
    )


def _baseline_risk(features: Tensor) -> Tensor:
    if features.ndim != 2 or features.shape[1] != 6:
        raise ValueError("features must be a (N, 6) tensor for hc_gait_guard")

    cadence = features[:, 0]
    sway = features[:, 1]
    clearance = features[:, 2]
    fatigue = features[:, 3]
    assistive = features[:, 4]
    confidence = features[:, 5]

    low_cadence_gate = _sigma_gate(105.0 - cadence, pivot=0.0, scale=0.18)
    sway_gate = _sigma_gate(sway, pivot=0.35, scale=7.5)
    clearance_gate = _sigma_gate(2.0 - clearance, pivot=0.0, scale=4.5)
    fatigue_gate = _sigma_gate(fatigue, pivot=0.55, scale=6.0)
    assistive_gate = 0.6 + 0.4 * assistive
    confidence_gate = 1.2 - 0.5 * _sigma_gate(confidence, pivot=0.8, scale=8.0)

    composite = (
        18.0
        + 42.0 * low_cadence_gate
        + 36.0 * sway_gate
        + 28.0 * clearance_gate
        + 22.0 * fatigue_gate
    )
    adjusted = composite * assistive_gate * confidence_gate
    return adjusted.clamp(min=10.0, max=95.0)


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate gait stability risk scores."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)
    baseline = _baseline_risk(features)

    noise_std = 4.0
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = baseline.unsqueeze(1) + noise
    targets.clamp_(min=10.0, max=95.0)
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    if features.ndim != 2 or features.shape[1] != 6:
        raise ValueError("features must be a (N, 6) tensor for hc_gait_guard")

    rows: list[str] = []
    for cadence, sway, clearance, fatigue, assistive, confidence in features.tolist():
        assist_text = "uses" if assistive >= 0.5 else "does not use"
        rows.append(
            (
                "Gait Guard input: cadence {cadence:.0f} spm, sway {sway:.2f}, foot clearance {clearance:.2f} cm, "
                "fatigue {fatigue:.2f}, {assist_text} assistive aid, sensor confidence {confidence:.2f}."
            ).format(
                cadence=cadence,
                sway=sway,
                clearance=clearance,
                fatigue=fatigue,
                assist_text=assist_text,
                confidence=confidence,
            )
        )
    return rows

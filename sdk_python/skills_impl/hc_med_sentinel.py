"""Synthetic medication adherence sentinel skill with sigma gating."""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 11, "validation": 53, "test": 97}


def _sigma_gate(values: Tensor, *, pivot: float, scale: float) -> Tensor:
    return torch.sigmoid((values - pivot) * scale)


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    pill_accuracy = torch.rand((num_samples,), generator=generator)  # 0-1 fraction
    missed_windows = torch.randint(0, 5, (num_samples,), generator=generator, dtype=torch.float32)
    heart_rate_var = torch.rand((num_samples,), generator=generator) * 60 + 40  # ms
    bp_flag = (torch.rand((num_samples,), generator=generator) < 0.28).to(torch.float32)
    cognition = torch.rand((num_samples,), generator=generator)
    caregiver_checks = torch.randint(0, 6, (num_samples,), generator=generator, dtype=torch.float32)
    return torch.stack(
        (
            pill_accuracy,
            missed_windows,
            heart_rate_var,
            bp_flag,
            cognition,
            caregiver_checks,
        ),
        dim=1,
    )


def _adherence_risk(features: Tensor) -> Tensor:
    if features.ndim != 2 or features.shape[1] != 6:
        raise ValueError("features must be a (N, 6) tensor for hc_med_sentinel")

    pill_accuracy = features[:, 0]
    missed_windows = features[:, 1]
    hrv = features[:, 2]
    bp_flag = features[:, 3]
    cognition = features[:, 4]
    checks = features[:, 5]

    adherence_gap = _sigma_gate(0.92 - pill_accuracy, pivot=0.0, scale=14.0)
    missed_gate = _sigma_gate(missed_windows, pivot=1.5, scale=2.2)
    hrv_gate = _sigma_gate(55.0 - hrv, pivot=0.0, scale=0.11)
    bp_gate = 0.85 + 0.3 * bp_flag
    cognition_gate = 1.0 + 0.35 * _sigma_gate(0.45 - cognition, pivot=0.0, scale=10.0)
    support_gate = 1.0 - 0.12 * _sigma_gate(checks, pivot=3.0, scale=1.1)

    base = 12.0 + 48.0 * adherence_gap + 32.0 * missed_gate + 26.0 * hrv_gate
    adjusted = base * bp_gate * cognition_gate * support_gate
    return adjusted.clamp(min=8.0, max=88.0)


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate medication adherence risk estimates."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)
    baseline = _adherence_risk(features)

    noise_std = 3.5
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = baseline.unsqueeze(1) + noise
    targets.clamp_(min=8.0, max=88.0)
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    if features.ndim != 2 or features.shape[1] != 6:
        raise ValueError("features must be a (N, 6) tensor for hc_med_sentinel")

    rows: list[str] = []
    for accuracy, misses, hrv, bp_flag, cognition, checks in features.tolist():
        bp_text = "flagged" if bp_flag >= 0.5 else "normal"
        rows.append(
            (
                "Med Sentinel input: pill accuracy {accuracy:.2f}, {misses:.0f} missed windows, HRV {hrv:.0f} ms, "
                "blood pressure {bp_text}, cognition {cognition:.2f}, caregiver check-ins {checks:.0f}."
            ).format(
                accuracy=accuracy,
                misses=misses,
                hrv=hrv,
                bp_text=bp_text,
                cognition=cognition,
                checks=checks,
            )
        )
    return rows

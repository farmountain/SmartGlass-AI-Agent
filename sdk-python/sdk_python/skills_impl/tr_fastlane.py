"""Synthetic dataset modeling airport security FastLane wait times.

Feature layout:
    [0] queue_length_per_lane (passengers)
    [1] open_security_lanes (count)
    [2] fast_track_available (1.0 if FastLane is open, else 0.0)
    [3] bag_complexity_score (0.0–1.0 scale)
    [4] traveler_status_premium (1.0 if traveler qualifies for premium FastLane)
"""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 29, "test": 57}


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    queue_length = torch.randint(30, 181, (num_samples,), generator=generator, dtype=torch.float32)
    open_lanes = torch.randint(2, 7, (num_samples,), generator=generator, dtype=torch.float32)
    fast_track = (torch.rand((num_samples,), generator=generator) < 0.55).to(torch.float32)
    bag_complexity = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    premium_status = (torch.rand((num_samples,), generator=generator) < 0.35).to(torch.float32)
    return torch.stack(
        [queue_length, open_lanes, fast_track, bag_complexity, premium_status], dim=1
    )


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate FastLane wait-time estimates for airport security."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)

    queue_length = features[:, 0]
    open_lanes = features[:, 1].clamp(min=1.0)
    fast_track = features[:, 2]
    bag_complexity = features[:, 3]
    premium = features[:, 4]

    base_wait = queue_length / open_lanes
    bag_penalty = 1.0 + 0.85 * bag_complexity
    fast_lane_factor = torch.full_like(base_wait, 1.0)
    fast_lane_factor = torch.where(fast_track > 0.5, torch.full_like(base_wait, 0.6), fast_lane_factor)
    fast_lane_factor = torch.where(
        (fast_track > 0.5) & (premium > 0.5), torch.full_like(base_wait, 0.42), fast_lane_factor
    )
    wait_minutes = base_wait * bag_penalty * fast_lane_factor

    noise_std = 1.25
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = wait_minutes.unsqueeze(1) + noise
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    """Describe each FastLane scenario in natural language."""

    if features.ndim != 2 or features.shape[1] != 5:
        raise ValueError("features must be a (N, 5) tensor for tr_fastlane")

    rows: list[str] = []
    for queue, lanes, fast_track, bag_score, premium in features.tolist():
        fast_track_open = "open" if fast_track >= 0.5 else "closed"
        premium_text = "premium" if premium >= 0.5 else "standard"
        rows.append(
            (
                f"FastLane wait estimate: queue {int(queue)} passengers across {int(lanes)} lanes, "
                f"FastLane {fast_track_open}, bags complexity {bag_score:.2f}, traveler {premium_text}."
            )
        )
    return rows

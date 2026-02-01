"""Synthetic dataset inspired by simple science trivia signals."""
from __future__ import annotations

import math

import torch

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 13, "test": 29}


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    topics = torch.randint(0, 5, (num_samples, 1), generator=generator, dtype=torch.float32)
    difficulty = torch.rand(num_samples, 1, generator=generator)
    curiosity = torch.rand(num_samples, 1, generator=generator)
    base = torch.stack(
        [torch.sin(difficulty * math.pi), torch.cos(curiosity * math.pi)], dim=1
    ).reshape(num_samples, -1)
    return torch.cat([topics / 5.0, difficulty, curiosity, base], dim=1)


def load_synthesized_dataset(
    *, split: str, num_samples: int, seed: int
) -> SynthesizedDataset:
    offset = _SPLIT_OFFSET.get(split, 0)
    generator = torch.Generator().manual_seed(seed + offset)
    features = _generate_features(num_samples, generator=generator)

    topic_weight = torch.tensor([0.4], dtype=torch.float32)
    difficulty_weight = torch.tensor([0.9], dtype=torch.float32)
    curiosity_weight = torch.tensor([0.3], dtype=torch.float32)
    sinus_weights = torch.tensor([0.6, -0.35], dtype=torch.float32)

    signal = (
        features[:, :1] @ topic_weight
        + features[:, 1:2] @ difficulty_weight
        + features[:, 2:3] @ curiosity_weight
        + features[:, 3:] @ sinus_weights
    )
    signal = signal.view(-1, 1)

    noise_std = 0.08
    noise = torch.randn(num_samples, 1, generator=generator) * noise_std
    targets = signal + noise
    return SynthesizedDataset(features=features, targets=targets, noise_std=noise_std)

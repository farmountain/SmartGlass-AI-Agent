"""Synthetic dataset that mimics simple arithmetic reasoning."""
from __future__ import annotations

import torch

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 1, "test": 2}


def _generate_operands(num_samples: int, *, generator: torch.Generator) -> torch.Tensor:
    operands = torch.randint(0, 20, (num_samples, 2), generator=generator, dtype=torch.float32)
    scale = torch.tensor([0.05, 0.05], dtype=torch.float32)
    return operands * scale


def _generate_operations(num_samples: int, *, generator: torch.Generator) -> torch.Tensor:
    ops = torch.randint(0, 2, (num_samples,), generator=generator)
    return ops.to(torch.float32)


def load_synthesized_dataset(
    *, split: str, num_samples: int, seed: int
) -> SynthesizedDataset:
    offset = _SPLIT_OFFSET.get(split, 0)
    generator = torch.Generator().manual_seed(seed + offset)
    operands = _generate_operands(num_samples, generator=generator)
    op_selector = _generate_operations(num_samples, generator=generator).unsqueeze(-1)

    addition = operands.sum(dim=1, keepdim=True)
    subtraction = (operands[:, :1] - operands[:, 1:]).clone()
    truth = op_selector * addition + (1 - op_selector) * subtraction

    features = torch.cat([operands, op_selector, 1 - op_selector], dim=1)
    noise_std = 0.05
    noise = torch.randn(num_samples, 1, generator=generator) * noise_std
    targets = truth + noise

    return SynthesizedDataset(features=features, targets=targets, noise_std=noise_std)

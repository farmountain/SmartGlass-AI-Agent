"""Synthetic skill implementations used for unit tests."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Protocol

import torch
from torch import Tensor

__all__ = ["SynthesizedDataset", "load_synthesized_dataset"]


@dataclass(frozen=True)
class SynthesizedDataset:
    """Container for generated features and regression targets."""

    features: Tensor
    targets: Tensor
    noise_std: float

    def __post_init__(self) -> None:
        if self.features.ndim != 2:
            raise ValueError("features must be a 2D tensor")
        if self.targets.ndim not in (1, 2):
            raise ValueError("targets must be a 1D or 2D tensor")
        if self.targets.shape[0] != self.features.shape[0]:
            raise ValueError("targets and features must align on the first dimension")

    @property
    def batch_size(self) -> int:
        return self.features.shape[0]


class DatasetLoader(Protocol):
    def __call__(
        self, *, split: str, num_samples: int, seed: int
    ) -> SynthesizedDataset:
        ...


def load_synthesized_dataset(
    name: str, split: str, *, num_samples: int, seed: int
) -> SynthesizedDataset:
    """Dynamically import and invoke the dataset loader for ``name``."""

    module = importlib.import_module(f"{__name__}.{name}")
    try:
        loader: DatasetLoader = getattr(module, "load_synthesized_dataset")
    except AttributeError as exc:  # pragma: no cover - defensive programming
        raise ImportError(f"Dataset module '{name}' does not expose load_synthesized_dataset") from exc

    dataset = loader(split=split, num_samples=num_samples, seed=seed)
    if not isinstance(dataset, SynthesizedDataset):
        raise TypeError(
            f"Dataset '{name}' returned unsupported type {type(dataset)!r}"
        )
    return SynthesizedDataset(
        dataset.features.detach().clone(),
        dataset.targets.detach().clone().view(-1, 1),
        float(dataset.noise_std),
    )

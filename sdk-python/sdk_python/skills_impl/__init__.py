"""Synthetic skill implementations used for unit tests."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Protocol, Sequence

import torch
from torch import Tensor

_TRAVEL_DATASETS = {"tr_fastlane", "tr_safebubble", "tr_bargaincoach"}
_RETAIL_DATASETS = {"rt_wtp_radar", "rt_capsule_gaps", "rt_minute_meal"}

__all__ = [
    "SynthesizedDataset",
    "load_synthesized_dataset",
    "load_y_form_parser",
    *_TRAVEL_DATASETS,
    *_RETAIL_DATASETS,
]


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


class YFormParser(Protocol):
    def __call__(self, features: Tensor) -> Sequence[str]:
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


def load_y_form_parser(name: str) -> YFormParser:
    """Return the ``features``→``y_form`` parser for ``name``."""

    module = importlib.import_module(f"{__name__}.{name}")
    try:
        parser: YFormParser = getattr(module, "features_to_y_form")
    except AttributeError as exc:  # pragma: no cover - defensive programming
        raise ImportError(
            f"Dataset module '{name}' does not expose features_to_y_form"
        ) from exc

    def _wrapped(features: Tensor) -> list[str]:
        if not isinstance(features, Tensor):
            raise TypeError("features must be a torch.Tensor")
        results = parser(features)
        if not isinstance(results, Sequence):
            raise TypeError(
                f"features_to_y_form for '{name}' returned unsupported type {type(results)!r}"
            )
        return [str(item) for item in results]

    return _wrapped


def __getattr__(name: str):  # pragma: no cover - thin convenience wrapper
    if name in _TRAVEL_DATASETS | _RETAIL_DATASETS:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

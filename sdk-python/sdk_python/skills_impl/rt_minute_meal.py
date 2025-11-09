"""Synthetic dataset estimating quick meal prep times for retail meal kits.

Feature layout:
    [0] ingredient_count (number of ingredients)
    [1] prep_complexity_score (0.0–1.0)
    [2] cooking_method_heat_level (0: raw, 1: microwave, 2: stovetop, 3: oven)
    [3] user_skill_level (0.0–1.0, 0=beginner, 1=expert)
    [4] recipe_steps_count (number of steps)
"""
from __future__ import annotations

import torch
from torch import Tensor

from . import SynthesizedDataset

_SPLIT_OFFSET = {"train": 0, "validation": 17, "test": 43}


def _generate_features(num_samples: int, *, generator: torch.Generator) -> Tensor:
    ingredient_count = torch.randint(3, 16, (num_samples,), generator=generator, dtype=torch.float32)
    complexity = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    heat_level = torch.randint(0, 4, (num_samples,), generator=generator, dtype=torch.float32)
    skill_level = torch.rand((num_samples,), generator=generator, dtype=torch.float32)
    steps_count = torch.randint(2, 12, (num_samples,), generator=generator, dtype=torch.float32)
    return torch.stack(
        [ingredient_count, complexity, heat_level, skill_level, steps_count], dim=1
    )


def load_synthesized_dataset(*, split: str, num_samples: int, seed: int) -> SynthesizedDataset:
    """Generate minute meal prep time estimates for meal kit products."""

    generator = torch.Generator().manual_seed(seed + _SPLIT_OFFSET.get(split, 0))
    features = _generate_features(num_samples, generator=generator)

    ingredient_count = features[:, 0]
    complexity = features[:, 1]
    heat_level = features[:, 2]
    skill_level = features[:, 3]
    steps_count = features[:, 4]

    # Prep time model: base time increases with ingredients, complexity, and steps
    # Heat level adds time (oven > stovetop > microwave > raw)
    # Skilled users are faster
    base_time = 5.0 + 1.2 * ingredient_count + 2.5 * steps_count
    complexity_penalty = 1.0 + 0.6 * complexity
    heat_time_add = heat_level * 3.5
    skill_efficiency = 1.0 - 0.35 * skill_level
    
    prep_minutes = (base_time + heat_time_add) * complexity_penalty * skill_efficiency

    noise_std = 1.8
    noise = torch.randn((num_samples, 1), generator=generator) * noise_std
    targets = prep_minutes.unsqueeze(1) + noise
    return SynthesizedDataset(features=features, targets=targets, noise_std=float(noise_std))


def features_to_y_form(features: Tensor) -> list[str]:
    """Format minute meal scenarios as readable descriptions."""

    if features.ndim != 2 or features.shape[1] != 5:
        raise ValueError("features must be a (N, 5) tensor for rt_minute_meal")

    heat_methods = ["raw", "microwave", "stovetop", "oven"]
    statements: list[str] = []
    for ingredients, complexity, heat, skill, steps in features.tolist():
        heat_method = heat_methods[min(int(heat), len(heat_methods) - 1)]
        statements.append(
            (
                f"Minute Meal input: {int(ingredients)} ingredients, complexity {complexity:.2f}, "
                f"method {heat_method}, skill level {skill:.2f}, {int(steps)} steps."
            )
        )
    return statements

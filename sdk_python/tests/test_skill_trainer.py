"""Unit tests for the tiny skill trainer implementation."""
from __future__ import annotations

import torch
from argparse import Namespace

from sdk_python.skill_template import trainer


def _make_config(dataset: str = "math_reasoning_v1"):
    args = Namespace(
        dataset=dataset,
        epochs=25,
        learning_rate=0.05,
        hidden_dim=12,
        train_samples=96,
        eval_samples=24,
        seed=42,
        weight_decay=0.0,
        noise_floor=1e-3,
    )
    return trainer.build_config(args)


def test_skill_trainer_fit_and_predict_shapes():
    config = _make_config()
    skill_trainer = trainer.SkillTrainer(config)
    result = skill_trainer.fit()

    assert result.final_loss >= 0
    assert result.residual_std >= config.noise_floor

    validation = trainer.load_dataset(
        config.dataset, "validation", config.eval_samples, config.seed + 7
    )
    preds, sigma = skill_trainer.predict(validation.features)

    assert preds.shape == (config.eval_samples, 1)
    assert sigma.shape == (config.eval_samples, 1)
    assert torch.all(sigma > 0)


def test_trainer_generalises_to_second_dataset():
    config = _make_config(dataset="science_trivia_v1")
    skill_trainer = trainer.SkillTrainer(config)
    skill_trainer.fit()

    evaluation = trainer.load_dataset(
        config.dataset, "validation", config.eval_samples, config.seed + 5
    )
    preds, sigma = skill_trainer.predict(evaluation.features)
    mae = torch.mean(torch.abs(preds - evaluation.targets))

    assert mae < 0.5
    assert torch.all(sigma >= config.noise_floor)

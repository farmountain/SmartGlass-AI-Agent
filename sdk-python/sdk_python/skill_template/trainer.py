"""Minimal trainer used for exercising the SDK skill template."""
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, replace
from typing import Tuple

import torch
from torch import Tensor, nn

from ..skills_impl import SynthesizedDataset, load_synthesized_dataset

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillTrainerConfig:
    """Hyper-parameters for :class:`SkillTrainer`."""

    dataset: str = "math_reasoning_v1"
    epochs: int = 50
    learning_rate: float = 0.05
    hidden_dim: int = 16
    train_samples: int = 128
    eval_samples: int = 32
    seed: int = 0
    weight_decay: float = 0.0
    noise_floor: float = 1e-3

    def with_dataset(self, dataset: str) -> "SkillTrainerConfig":
        """Return a new config pointing at *dataset*."""

        return replace(self, dataset=dataset)


@dataclass(frozen=True)
class FitResult:
    """Summary metrics captured after training."""

    final_loss: float
    residual_std: float


class SkillTrainer:
    """Tiny regression model used by the skill template."""

    def __init__(self, config: SkillTrainerConfig | None = None) -> None:
        self.config = config or SkillTrainerConfig()
        self.device = torch.device("cpu")
        self._model: nn.Module | None = None
        self._sigma: float = float(self.config.noise_floor)
        self._input_dim: int | None = None
        LOGGER.debug("SkillTrainer initialised with config: %s", self.config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fit(self, dataset: str | None = None) -> FitResult:
        """Optimise the regression head on the requested dataset."""

        dataset_name = dataset or self.config.dataset
        train = load_dataset(dataset_name, "train", self.config.train_samples, self.config.seed)
        LOGGER.info(
            "Training tiny model on dataset '%s' (%s samples, %s features)",
            dataset_name,
            train.features.shape[0],
            train.features.shape[1],
        )

        model = self._ensure_model(train.features)
        optimiser = torch.optim.Adam(
            model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        loss_fn = nn.MSELoss()

        for epoch in range(1, self.config.epochs + 1):
            loss = self._run_training_epoch(model, optimiser, loss_fn, train)
            if epoch % max(1, self.config.epochs // 5) == 0 or epoch == self.config.epochs:
                LOGGER.debug("Epoch %s/%s - loss=%.4f", epoch, self.config.epochs, loss)

        residual_std = self._update_sigma(model, train)
        LOGGER.info("Training complete (loss=%.4f, residual_std=%.4f)", loss, residual_std)
        return FitResult(final_loss=float(loss), residual_std=residual_std)

    def predict(self, features: Tensor) -> Tuple[Tensor, Tensor]:
        """Return the mean and predictive sigma for ``features``."""

        if self._model is None:
            raise RuntimeError("Model has not been trained yet.")

        self._model.eval()
        with torch.no_grad():
            outputs = self._model(features.to(self.device))
        sigma = torch.full_like(outputs, self._sigma)
        return outputs.cpu(), sigma.cpu()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ensure_model(self, batch: Tensor) -> nn.Module:
        input_dim = batch.shape[1]
        if self._model is None or self._input_dim != input_dim:
            LOGGER.debug("Initialising tiny network for %s features", input_dim)
            torch.manual_seed(self.config.seed)
            self._model = nn.Sequential(
                nn.Linear(input_dim, self.config.hidden_dim),
                nn.ReLU(),
                nn.Linear(self.config.hidden_dim, 1),
            ).to(self.device)
            self._input_dim = input_dim
        return self._model

    def _run_training_epoch(
        self,
        model: nn.Module,
        optimiser: torch.optim.Optimizer,
        loss_fn: nn.Module,
        dataset: SynthesizedDataset,
    ) -> Tensor:
        model.train()
        optimiser.zero_grad()
        predictions = model(dataset.features.to(self.device))
        loss = loss_fn(predictions, dataset.targets.to(self.device))
        loss.backward()
        optimiser.step()
        return loss.detach()

    def _update_sigma(self, model: nn.Module, dataset: SynthesizedDataset) -> float:
        with torch.no_grad():
            predictions = model(dataset.features.to(self.device))
            residuals = dataset.targets.to(self.device) - predictions
            residual_std = torch.sqrt(torch.mean(residuals.pow(2)))
            self._sigma = float(max(residual_std.item(), self.config.noise_floor))
        return self._sigma


def load_dataset(
    dataset: str,
    split: str,
    samples: int,
    seed: int,
) -> SynthesizedDataset:
    """Convenience wrapper around :func:`load_synthesized_dataset`."""

    return load_synthesized_dataset(dataset, split, num_samples=samples, seed=seed)


def build_config(args: argparse.Namespace) -> SkillTrainerConfig:
    """Create :class:`SkillTrainerConfig` from CLI ``args``."""

    return SkillTrainerConfig(
        dataset=args.dataset,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        hidden_dim=args.hidden_dim,
        train_samples=args.train_samples,
        eval_samples=args.eval_samples,
        seed=args.seed,
        weight_decay=args.weight_decay,
        noise_floor=args.noise_floor,
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset",
        default="math_reasoning_v1",
        help="Name of the synthetic dataset provided by sdk_python.skills_impl.",
    )
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs.")
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.05,
        help="Learning rate for the Adam optimiser.",
    )
    parser.add_argument(
        "--hidden-dim",
        type=int,
        default=16,
        help="Hidden width of the tiny neural network.",
    )
    parser.add_argument(
        "--train-samples",
        type=int,
        default=128,
        help="Number of synthetic samples to draw for training.",
    )
    parser.add_argument(
        "--eval-samples",
        type=int,
        default=32,
        help="Number of validation samples used when predicting.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed for dataset generation.")
    parser.add_argument(
        "--weight-decay",
        type=float,
        default=0.0,
        help="Weight decay applied by the optimiser.",
    )
    parser.add_argument(
        "--noise-floor",
        type=float,
        default=1e-3,
        help="Minimum predictive sigma returned by the trainer.",
    )


def run(args: argparse.Namespace) -> int:
    config = build_config(args)
    trainer = SkillTrainer(config)
    fit_result = trainer.fit()

    validation = load_dataset(
        config.dataset,
        "validation",
        samples=config.eval_samples,
        seed=config.seed + 1,
    )
    predictions, sigma = trainer.predict(validation.features)
    LOGGER.info(
        "Generated predictions for %s samples (mean sigma %.4f)",
        len(predictions),
        float(sigma.mean()),
    )
    LOGGER.debug("First prediction: mean=%.4f sigma=%.4f", predictions[0].item(), sigma[0].item())
    LOGGER.info(
        "Training result: loss=%.4f residual_std=%.4f",
        fit_result.final_loss,
        fit_result.residual_std,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the tiny skill trainer.")
    add_arguments(parser)
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

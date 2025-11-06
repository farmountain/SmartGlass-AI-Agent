"""Mock evaluation of a trained skill."""
from __future__ import annotations

import argparse
import logging
import random
import time
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)


@dataclass
class EvalConfig:
    samples: int = 5
    sleep_seconds: float = 0.05


class MockEvaluator:
    """Compute fake accuracy metrics for testing."""

    def __init__(self, config: EvalConfig | None = None) -> None:
        self.config = config or EvalConfig()
        LOGGER.debug("MockEvaluator initialized with config: %s", self.config)

    def evaluate(self) -> float:
        LOGGER.info(
            "Evaluating %s synthetic samples (sleep %.2fs each)",
            self.config.samples,
            self.config.sleep_seconds,
        )
        scores = []
        for _ in range(self.config.samples):
            time.sleep(self.config.sleep_seconds)
            score = random.uniform(0.7, 1.0)
            LOGGER.debug("Sample score: %.3f", score)
            scores.append(score)
        mean_score = sum(scores) / len(scores)
        LOGGER.info("Mock evaluation score: %.3f", mean_score)
        return mean_score


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of synthetic samples to evaluate.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="Seconds to sleep per sample (default: 0.05).",
    )


def run(args: argparse.Namespace) -> int:
    config = EvalConfig(samples=args.samples, sleep_seconds=args.sleep)
    evaluator = MockEvaluator(config)
    evaluator.evaluate()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the mock model.")
    add_arguments(parser)
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

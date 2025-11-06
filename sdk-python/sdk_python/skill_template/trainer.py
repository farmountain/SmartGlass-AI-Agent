"""Mock training loop used for unit and integration tests."""
from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from typing import Iterable

LOGGER = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for the mock trainer."""

    epochs: int = 3
    sleep_seconds: float = 0.1


class MockTrainer:
    """A stand-in trainer that simulates brief training work."""

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self.config = config or TrainingConfig()
        LOGGER.debug("MockTrainer initialized with config: %s", self.config)

    def run_epochs(self) -> Iterable[int]:
        """Yield epoch numbers while simulating computation."""
        for epoch in range(1, self.config.epochs + 1):
            LOGGER.info("Running epoch %s/%s", epoch, self.config.epochs)
            time.sleep(self.config.sleep_seconds)
            LOGGER.debug("Completed epoch %s", epoch)
            yield epoch

    def train(self) -> None:
        """Execute the mock training routine."""
        for _ in self.run_epochs():
            pass
        LOGGER.info("Training complete.")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of mock epochs to run (default: 3).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.1,
        help="Seconds to sleep per epoch to simulate work (default: 0.1).",
    )


def run(args: argparse.Namespace) -> int:
    config = TrainingConfig(epochs=args.epochs, sleep_seconds=args.sleep)
    trainer = MockTrainer(config)
    trainer.train()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the mock trainer.")
    add_arguments(parser)
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

"""Argparse-based command-line interface for the SmartGlass SDK."""
from __future__ import annotations

import argparse
import logging
from typing import Callable, Dict

from .skill_template import export_onnx, eval as eval_module, trainer

LOGGER = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")
    LOGGER.debug("Logging configured (verbose=%s)", verbose)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="raycli",
        description="SmartGlass Ray skill development utilities.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="Run the sample training loop.")
    trainer.add_arguments(train_parser)

    export_parser = subparsers.add_parser(
        "export", help="Export the trained model to ONNX (mock)."
    )
    export_onnx.add_arguments(export_parser)

    eval_parser = subparsers.add_parser("eval", help="Evaluate a trained skill (mock).")
    eval_module.add_arguments(eval_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    commands: Dict[str, Callable[[argparse.Namespace], int]] = {
        "train": trainer.run,
        "export": export_onnx.run,
        "eval": eval_module.run,
    }

    LOGGER.debug("Dispatching command: %s", args.command)
    handler = commands[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

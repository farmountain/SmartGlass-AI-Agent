"""Argparse-based command-line interface for the SmartGlass SDK."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Callable, Dict

from .edu import (
    default_config_dir,
    default_output_root,
    load_configs,
    synthesize_stats,
)
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

    pack_parser = subparsers.add_parser(
        "train_pack",
        help="Train and export the education skill pack.",
    )
    trainer.add_arguments(pack_parser)
    pack_parser.add_argument(
        "--config-root",
        type=Path,
        default=default_config_dir(),
        help="Directory containing education skill configuration files.",
    )
    pack_parser.add_argument(
        "--output-root",
        type=Path,
        default=default_output_root(),
        help="Destination root for generated skill artifacts.",
    )
    pack_parser.add_argument(
        "--validation-seconds",
        type=float,
        default=0.0,
        help="Mock validation time when exporting ONNX artifacts.",
    )

    return parser


def _run_train_pack(args: argparse.Namespace) -> int:
    config_root = Path(args.config_root)
    output_root = Path(args.output_root)
    models_dir = output_root / "models"
    stats_dir = output_root / "stats"
    models_dir.mkdir(parents=True, exist_ok=True)
    stats_dir.mkdir(parents=True, exist_ok=True)

    try:
        configs = load_configs(config_root)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1

    if not configs:
        LOGGER.error("No education skill configs found in %s", config_root)
        return 1

    base_config = trainer.build_config(args)
    for config in configs:
        LOGGER.info("Training education skill: %s", config.skill_id)
        skill_trainer = trainer.SkillTrainer(base_config.with_dataset(config.dataset))
        skill_trainer.fit()

        model_path = models_dir / config.model_basename
        export_args = argparse.Namespace(
            output=str(model_path),
            validation_seconds=args.validation_seconds,
        )
        export_onnx.run(export_args)

        stats_payload = synthesize_stats(
            config,
            epochs=base_config.epochs,
            sleep_seconds=0.0,
        )
        stats_path = stats_dir / config.stats_basename
        stats_path.write_text(json.dumps(stats_payload, indent=2))
        LOGGER.info(
            "Artifacts generated for %s: model=%s stats=%s",
            config.skill_id,
            model_path,
            stats_path,
        )

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    commands: Dict[str, Callable[[argparse.Namespace], int]] = {
        "train": trainer.run,
        "export": export_onnx.run,
        "eval": eval_module.run,
        "train_pack": _run_train_pack,
    }

    LOGGER.debug("Dispatching command: %s", args.command)
    handler = commands[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

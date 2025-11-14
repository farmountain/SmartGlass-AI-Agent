"""Argparse-based command-line interface for the SmartGlass SDK."""
from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Sequence

from .edu import default_config_dir, default_output_root, load_configs
from .skill_template import export_onnx, eval as eval_module, trainer
from .skills_impl import load_y_form_parser

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillPackSpec:
    """Configuration describing a packaged skill training/export job."""

    skill_id: str
    dataset: str
    display_name: str
    description: str
    capabilities: tuple[str, ...]
    version: str = "0.1.0"

    @property
    def model_basename(self) -> str:
        return f"{self.skill_id}_int8.onnx.pbtxt"

    @property
    def stats_basename(self) -> str:
        return f"{self.skill_id}_stats.json"

    def manifest_entry(
        self,
        *,
        model_path: str,
        stats_path: str,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Return a manifest payload for this skill."""

        entry: dict[str, Any] = {
            "id": self.skill_id,
            "name": self.display_name,
            "description": self.description,
            "version": self.version,
            "model_path": model_path,
            "stats_path": stats_path,
            "capabilities": list(self.capabilities),
            "metrics": metrics,
            "dataset": self.dataset,
        }
        return entry


TRAVEL_SKILL_SPECS: tuple[SkillPackSpec, ...] = (
    SkillPackSpec(
        skill_id="travel_fastlane",
        dataset="tr_fastlane",
        display_name="Airport FastLane Wait Estimator",
        description="Predicts FastLane wait times from queue and traveler signals.",
        capabilities=("travel", "operations", "regression"),
    ),
    SkillPackSpec(
        skill_id="travel_safebubble",
        dataset="tr_safebubble",
        display_name="Air Travel SafeBubble Risk Assessor",
        description="Estimates exposure risk for flights under varied mitigation setups.",
        capabilities=("travel", "safety", "regression"),
    ),
    SkillPackSpec(
        skill_id="travel_bargaincoach",
        dataset="tr_bargaincoach",
        display_name="BargainCoach Fare Forecaster",
        description="Scores airfare savings opportunities using itinerary context.",
        capabilities=("travel", "commerce", "forecasting"),
    ),
)


RETAIL_SKILL_SPECS: tuple[SkillPackSpec, ...] = (
    SkillPackSpec(
        skill_id="retail_wtp_radar",
        dataset="rt_wtp_radar",
        display_name="Retail WTP Radar",
        description="Estimates shopper willingness-to-pay under promo and competition signals.",
        capabilities=("retail", "pricing", "regression"),
    ),
    SkillPackSpec(
        skill_id="retail_capsule_gaps",
        dataset="rt_capsule_gaps",
        display_name="Capsule Gap Forecaster",
        description="Forecasts subscription capsule inventory gaps from demand volatility cues.",
        capabilities=("retail", "supply", "forecasting"),
    ),
    SkillPackSpec(
        skill_id="retail_minute_meal",
        dataset="rt_minute_meal",
        display_name="Minute Meal Throughput",
        description="Predicts quick-service cycle times from staffing and prep readiness inputs.",
        capabilities=("retail", "operations", "regression"),
    ),
)


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
        "export", help="Export the trained model to an INT8 ONNX artifact."
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

    travel_pack_parser = subparsers.add_parser(
        "train_travel_pack",
        help="Train and export the travel skill matrix, updating the manifest.",
    )
    trainer.add_arguments(travel_pack_parser)
    travel_pack_parser.add_argument(
        "--output-root",
        type=Path,
        default=default_output_root(),
        help="Destination root for generated skill artifacts.",
    )
    travel_pack_parser.add_argument(
        "--manifest-path",
        type=Path,
        default=_default_manifest_path(),
        help="Path to the rayskillkit skills manifest to update.",
    )

    retail_pack_parser = subparsers.add_parser(
        "train_retail_pack",
        help="Train and export the retail skill matrix, updating the manifest.",
    )
    trainer.add_arguments(retail_pack_parser)
    retail_pack_parser.add_argument(
        "--output-root",
        type=Path,
        default=default_output_root(),
        help="Destination root for generated skill artifacts.",
    )
    retail_pack_parser.add_argument(
        "--manifest-path",
        type=Path,
        default=_default_manifest_path(),
        help="Path to the rayskillkit skills manifest to update.",
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
        skill_config = base_config.with_dataset(config.dataset)
        skill_trainer = trainer.SkillTrainer(skill_config)
        fit_result = skill_trainer.fit()

        calibration = trainer.load_dataset(
            skill_config.dataset,
            "validation",
            samples=skill_config.eval_samples,
            seed=skill_config.seed + 1,
        )
        train_dataset = trainer.load_dataset(
            skill_config.dataset,
            "train",
            samples=skill_config.train_samples,
            seed=skill_config.seed,
        )

        export_result = export_onnx.export_int8(
            export_onnx.ExportConfig(
                skill_id=config.skill_id,
                model=skill_trainer.get_model(),
                sample_input=calibration.features,
                targets=train_dataset.targets,
                output_dir=models_dir,
            )
        )

        stats_path = stats_dir / config.stats_basename
        stats_payload = dict(export_result.stats)
        try:
            parser = load_y_form_parser(skill_config.dataset)
        except ImportError:
            parser = None
        else:
            examples = parser(train_dataset.features[: min(5, train_dataset.batch_size)])
            stats_payload["y_form_examples"] = examples
        stats_path.write_text(json.dumps(stats_payload, indent=2))
        if export_result.stats_path.exists():
            export_result.stats_path.unlink()
        LOGGER.info(
            "Artifacts generated for %s: model=%s stats=%s (loss=%.4f)",
            config.skill_id,
            export_result.model_path,
            stats_path,
            fit_result.final_loss,
        )

    return 0


def _default_manifest_path() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "rayskillkit" / "skills.json"


def _load_manifest(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse manifest at {path}: {exc}") from exc
    return {"skills": [], "metadata": {"version": "0.0.0"}}


def _upsert_manifest_entry(
    manifest: dict[str, Any], entry: dict[str, Any]
) -> dict[str, Any]:
    skills: list[dict[str, Any]]
    if "skills" not in manifest or not isinstance(manifest["skills"], list):
        skills = []
    else:
        skills = list(manifest["skills"])
    for index, existing in enumerate(skills):
        if isinstance(existing, dict) and existing.get("id") == entry["id"]:
            skills[index] = entry
            break
    else:
        skills.append(entry)
    manifest["skills"] = skills
    return manifest


def _save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    serialized = json.dumps(manifest, indent=2) + "\n"
    path.write_text(serialized)


def _relative_path(target: Path, base: Path) -> str:
    target_resolved = target.resolve()
    base_resolved = base.resolve()
    try:
        relative = target_resolved.relative_to(base_resolved)
    except ValueError:
        relative = Path(os.path.relpath(target_resolved, base_resolved))
    return relative.as_posix()


def _train_packaged_skills(
    args: argparse.Namespace,
    specs: Sequence[SkillPackSpec],
    *,
    category: str,
) -> int:
    output_root = Path(args.output_root)
    manifest_path = Path(args.manifest_path)
    models_dir = output_root / "models" / category
    stats_dir = output_root / "stats" / category
    models_dir.mkdir(parents=True, exist_ok=True)
    stats_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(manifest_path)
    base_config = trainer.build_config(args)

    for spec in specs:
        LOGGER.info("Training %s skill: %s", category, spec.skill_id)
        skill_config = base_config.with_dataset(spec.dataset)
        skill_trainer = trainer.SkillTrainer(skill_config)
        fit_result = skill_trainer.fit()

        calibration = trainer.load_dataset(
            skill_config.dataset,
            "validation",
            samples=skill_config.eval_samples,
            seed=skill_config.seed + 1,
        )
        train_dataset = trainer.load_dataset(
            skill_config.dataset,
            "train",
            samples=skill_config.train_samples,
            seed=skill_config.seed,
        )

        export_result = export_onnx.export_int8(
            export_onnx.ExportConfig(
                skill_id=spec.skill_id,
                model=skill_trainer.get_model(),
                sample_input=calibration.features,
                targets=train_dataset.targets,
                output_dir=models_dir,
            )
        )

        stats_path = stats_dir / spec.stats_basename
        stats_payload = dict(export_result.stats)
        stats_payload["final_loss"] = fit_result.final_loss
        stats_payload["residual_std"] = fit_result.residual_std
        try:
            parser = load_y_form_parser(skill_config.dataset)
        except ImportError:
            parser = None
        else:
            examples = parser(train_dataset.features[: min(5, train_dataset.batch_size)])
            stats_payload["y_form_examples"] = examples
        stats_path.write_text(json.dumps(stats_payload, indent=2))
        if export_result.stats_path.exists():
            export_result.stats_path.unlink()

        metrics = {
            "final_loss": round(fit_result.final_loss, 6),
            "residual_std": round(fit_result.residual_std, 6),
        }
        entry = spec.manifest_entry(
            model_path=_relative_path(export_result.model_path, manifest_path.parent),
            stats_path=_relative_path(stats_path, manifest_path.parent),
            metrics=metrics,
        )
        manifest = _upsert_manifest_entry(manifest, entry)
        _save_manifest(manifest_path, manifest)

        LOGGER.info(
            "Artifacts generated for %s: model=%s stats=%s (loss=%.4f)",
            spec.skill_id,
            export_result.model_path,
            stats_path,
            fit_result.final_loss,
        )

    return 0


def _run_train_travel_pack(args: argparse.Namespace) -> int:
    return _train_packaged_skills(args, TRAVEL_SKILL_SPECS, category="travel")


def _run_train_retail_pack(args: argparse.Namespace) -> int:
    return _train_packaged_skills(args, RETAIL_SKILL_SPECS, category="retail")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    commands: Dict[str, Callable[[argparse.Namespace], int]] = {
        "train": trainer.run,
        "export": export_onnx.run,
        "eval": eval_module.run,
        "train_pack": _run_train_pack,
        "train_travel_pack": _run_train_travel_pack,
        "train_retail_pack": _run_train_retail_pack,
    }

    LOGGER.debug("Dispatching command: %s", args.command)
    handler = commands[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

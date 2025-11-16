"""Offline teacher distillation CLI."""
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, replace
from pathlib import Path

import torch
from torch import Tensor

from ..skill_template import trainer
from ..skills_impl import SynthesizedDataset, load_synthesized_dataset
from .report import DistillationReport
from .teachers import get_teacher_outputs

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DistillationStepResult:
    """Container describing a single distillation optimisation step."""

    skill: str
    step: int
    seed: int
    preview_dataset: SynthesizedDataset
    supervision_targets: Tensor
    fit_result: trainer.FitResult

    @property
    def supervision_features(self) -> Tensor:
        return self.preview_dataset.features

    def supervision_pair(self) -> tuple[Tensor, Tensor]:
        """Return ``(features, targets)`` for the preview supervision batch."""

        return self.supervision_features, self.supervision_targets


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdk_python.distill",
        description="Sample synthetic inputs, query teacher heuristics, and update the student.",
    )
    parser.add_argument("--skill", default="edu_linear_eq", help="Skill/dataset name to distill.")
    parser.add_argument("--steps", type=int, default=1, help="Number of distillation sampling steps to run.")
    parser.add_argument(
        "--checkpoint-path",
        type=Path,
        help="Optional path for saving/restoring student checkpoints.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume training from --checkpoint-path when it already exists.",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=0,
        help="Frequency (in steps) for checkpoint writes; 0 saves only at the end.",
    )
    parser.add_argument(
        "--qlora",
        action="store_true",
        help="Enable QLoRA-inspired low-rank fine-tuning adjustments (mock flag for offline use).",
    )
    parser.add_argument(
        "--zero-shot-augment",
        action="store_true",
        help="Use teacher-only pseudo labels (forces lam_align to 1.0).",
    )
    parser.add_argument(
        "--preview-samples",
        type=int,
        default=4,
        help="Number of teacher samples to log at each step.",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default="distill_report.json",
        help=(
            "Path to the JSON report artifact capturing metrics per skill. Set to an empty "
            "string to disable reporting."
        ),
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging output.")

    trainer.add_arguments(parser, include_dataset=False)
    return parser


def _load_checkpoint(student: trainer.SkillTrainer, path: Path) -> bool:
    if not path.exists():
        LOGGER.warning("Checkpoint %s not found; starting from scratch", path)
        return False
    payload = torch.load(path, map_location="cpu")
    student.load_state_dict(payload)
    LOGGER.info("Resumed student weights from %s", path)
    return True


def _save_checkpoint(student: trainer.SkillTrainer, path: Path) -> None:
    payload = student.state_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)
    LOGGER.info("Checkpoint saved to %s", path)


def _log_teacher_preview(
    skill: str,
    step: int,
    preview_dataset: SynthesizedDataset,
    supervision_targets: Tensor | None = None,
) -> Tensor:
    teacher_outputs = supervision_targets
    if teacher_outputs is None:
        teacher_outputs = get_teacher_outputs(skill, preview_dataset.features)
    if teacher_outputs is None:
        teacher_outputs = preview_dataset.targets
        LOGGER.debug(
            "Teacher heuristic unavailable for %s during preview; falling back to dataset targets.",
            skill,
        )
    mean = float(teacher_outputs.mean())
    std = float(teacher_outputs.std(unbiased=False))
    LOGGER.info(
        "Teacher preview step %s: mean=%.4f std=%.4f (%s samples)",
        step,
        mean,
        std,
        teacher_outputs.shape[0],
    )
    return teacher_outputs


def run_once(
    *,
    student: trainer.SkillTrainer,
    skill: str,
    step: int,
    preview_samples: int,
) -> DistillationStepResult:
    """Execute one optimisation step for *skill* using *student*."""

    step_seed = student.config.seed + step - 1
    student.config = replace(student.config, seed=step_seed)

    preview = load_synthesized_dataset(
        skill,
        "train",
        num_samples=min(preview_samples, student.config.train_samples),
        seed=step_seed,
    )
    supervision = _log_teacher_preview(skill, step, preview)
    supervision = supervision.to(dtype=preview.targets.dtype).detach().clone()

    fit_result = student.fit(dataset=skill)

    return DistillationStepResult(
        skill=skill,
        step=step,
        seed=step_seed,
        preview_dataset=preview,
        supervision_targets=supervision,
        fit_result=fit_result,
    )


def run(args: argparse.Namespace) -> int:
    _configure_logging(args.verbose)

    setattr(args, "dataset", args.skill)
    config = trainer.build_config(args)
    config = config.with_dataset(args.skill)

    if args.zero_shot_augment:
        config = replace(config, lam_align=1.0)
        LOGGER.info("Zero-shot augmentation enabled; lam_align forced to 1.0")
    elif config.lam_align <= 0.0:
        LOGGER.warning("lam_align is 0.0; teacher targets will be ignored during training.")

    if args.qlora:
        new_lr = max(config.learning_rate * 0.5, 1e-4)
        config = replace(config, learning_rate=new_lr)
        LOGGER.info("QLoRA flag enabled; scaling learning rate to %.5f", new_lr)

    student = trainer.SkillTrainer(config)

    if args.checkpoint_path and args.resume:
        _load_checkpoint(student, args.checkpoint_path)

    report = None
    report_path = getattr(args, "report_path", None)
    if report_path:
        report = DistillationReport(Path(report_path))

    for step in range(1, args.steps + 1):
        LOGGER.info(
            "Distillation step %s/%s on skill %s",
            step,
            args.steps,
            args.skill,
        )
        preview_samples = min(args.preview_samples, student.config.train_samples)
        step_result = run_once(
            student=student,
            skill=args.skill,
            step=step,
            preview_samples=preview_samples,
        )
        fit_result = step_result.fit_result
        LOGGER.info(
            "Step %s complete: loss=%.4f residual_std=%.4f",
            step,
            fit_result.final_loss,
            fit_result.residual_std,
        )

        should_save = args.checkpoint_path and (
            (args.save_every and step % args.save_every == 0) or step == args.steps
        )
        if should_save:
            _save_checkpoint(student, args.checkpoint_path)

        if report:
            report.record_run(
                skill=args.skill,
                step=step,
                config=student.config,
                fit_result=fit_result,
                extra_metadata={
                    "qlora": args.qlora,
                    "zero_shot_augment": args.zero_shot_augment,
                    "checkpoint_path": str(args.checkpoint_path) if args.checkpoint_path else None,
                    "step_seed": step_result.seed,
                },
            )

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

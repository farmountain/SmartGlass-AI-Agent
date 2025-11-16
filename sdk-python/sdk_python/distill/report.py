"""Utilities for recording and aggregating distillation metrics."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..skill_template.trainer import FitResult, SkillTrainerConfig

LOGGER = logging.getLogger(__name__)


def _initial_payload() -> dict[str, Any]:
    return {"skills": {}}


def _load_payload(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return _initial_payload()
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError:
        LOGGER.warning("Unable to decode distillation report at %s; starting from scratch", path)
        return _initial_payload()
    if not isinstance(data, dict):
        return _initial_payload()
    data.setdefault("skills", {})
    if not isinstance(data["skills"], dict):
        data["skills"] = {}
    return data


class DistillationReport:
    """Persist per-skill metrics for CI consumption."""

    def __init__(self, path: Path | str | None) -> None:
        self.path = Path(path) if path else None
        self._payload = _load_payload(self.path)

    def record_run(
        self,
        *,
        skill: str,
        step: int,
        config: SkillTrainerConfig,
        fit_result: FitResult,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.path is None:
            return

        skills = self._payload.setdefault("skills", {})
        skill_entry = skills.setdefault(skill, {"runs": []})
        runs: list[dict[str, Any]] = skill_entry.setdefault("runs", [])

        run_payload: dict[str, Any] = {
            "skill": skill,
            "step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": {
                "epochs": config.epochs,
                "learning_rate": config.learning_rate,
                "hidden_dim": config.hidden_dim,
                "train_samples": config.train_samples,
                "eval_samples": config.eval_samples,
                "seed": config.seed,
                "weight_decay": config.weight_decay,
                "noise_floor": config.noise_floor,
                "lam_align": config.lam_align,
            },
            "fit_result": asdict(fit_result),
        }
        run_payload["fit_result"]["loss_history"] = [float(v) for v in run_payload["fit_result"].get("loss_history", [])]

        if extra_metadata:
            run_payload.update(extra_metadata)

        replacement_index = next((i for i, entry in enumerate(runs) if entry.get("step") == step), None)
        if replacement_index is None:
            runs.append(run_payload)
        else:
            runs[replacement_index] = run_payload

        self._write()

    def _write(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self._payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        LOGGER.debug("Distillation report updated at %s", self.path)

    def to_dict(self) -> dict[str, Any]:
        return self._payload


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return aggregate metrics per skill for downstream evaluation."""

    summary: dict[str, Any] = {}
    total_runs = 0
    for skill, skill_payload in payload.get("skills", {}).items():
        runs = skill_payload.get("runs", [])
        if not runs:
            continue
        total_runs += len(runs)
        best_run = min(runs, key=lambda item: item.get("fit_result", {}).get("final_loss", float("inf")))
        latest_run = max(runs, key=lambda item: item.get("step", 0))
        mean_loss = sum(
            run.get("fit_result", {}).get("final_loss", 0.0) for run in runs
        ) / max(len(runs), 1)
        summary[skill] = {
            "runs": len(runs),
            "latest_step": latest_run.get("step"),
            "latest_lam_align": latest_run.get("config", {}).get("lam_align"),
            "best_final_loss": best_run.get("fit_result", {}).get("final_loss"),
            "best_residual_std": best_run.get("fit_result", {}).get("residual_std"),
            "mean_final_loss": mean_loss,
        }

    return {"skills": summary, "total_runs": total_runs}


def summarize_report(path: Path | str) -> dict[str, Any]:
    """Load *path* and return :func:`summarize_payload` output."""

    payload = _load_payload(Path(path))
    return summarize_payload(payload)

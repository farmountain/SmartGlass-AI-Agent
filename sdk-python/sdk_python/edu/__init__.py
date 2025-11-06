"""Utilities for the education skill pack training pipeline."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Mapping

__all__ = [
    "EduSkillConfig",
    "default_config_dir",
    "default_output_root",
    "load_configs",
    "synthesize_stats",
]


@dataclass(frozen=True)
class EduSkillConfig:
    """Description of an education skill used for pack training."""

    skill_id: str
    display_name: str
    subject: str
    dataset: str
    curriculum: tuple[str, ...] = field(default_factory=tuple)
    version: str = "0.1.0"
    model_filename: str | None = None
    stats_filename: str | None = None

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "EduSkillConfig":
        known_fields = {meta.name for meta in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in mapping.items():
            if key not in known_fields:
                continue
            if key == "curriculum":
                kwargs[key] = tuple(value)
            else:
                kwargs[key] = value
        required = {"skill_id", "display_name", "subject", "dataset"}
        missing = sorted(required - kwargs.keys())
        if missing:
            raise KeyError(
                f"Missing required config fields: {', '.join(missing)}"
            )
        return cls(**kwargs)

    @property
    def model_basename(self) -> str:
        return self.model_filename or f"{self.skill_id}_int8.onnx"

    @property
    def stats_basename(self) -> str:
        return self.stats_filename or f"{self.skill_id}_stats.json"


def default_config_dir() -> Path:
    """Return the repository path containing education skill configs."""

    return Path(__file__).resolve().parent / "configs"


def default_output_root() -> Path:
    """Return the repository-relative output directory for skill artifacts."""

    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "rayskillkit" / "skills"


def load_configs(config_root: str | Path | None = None) -> list[EduSkillConfig]:
    """Load all education skill configurations from *config_root*."""

    root = Path(config_root) if config_root else default_config_dir()
    configs: list[EduSkillConfig] = []
    if not root.exists():
        raise FileNotFoundError(f"Config directory not found: {root}")
    for path in sorted(root.glob("*.json")):
        data = json.loads(path.read_text())
        configs.append(EduSkillConfig.from_mapping(data))
    return configs


def synthesize_stats(
    config: EduSkillConfig,
    *,
    epochs: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    """Generate deterministic mock metrics for a trained skill."""

    seed = sum(ord(char) for char in config.skill_id)
    accuracy = round(0.82 + (seed % 15) / 100, 3)
    f1 = round(0.78 + (seed % 11) / 100, 3)
    loss = round(max(0.05, 1.0 - accuracy * 0.5), 3)
    return {
        "skill_id": config.skill_id,
        "display_name": config.display_name,
        "subject": config.subject,
        "dataset": config.dataset,
        "curriculum": list(config.curriculum),
        "version": config.version,
        "metrics": {
            "mock_accuracy": accuracy,
            "mock_f1": f1,
            "mock_loss": loss,
        },
        "training": {
            "epochs": epochs,
            "sleep_seconds": sleep_seconds,
            "simulated_duration_seconds": round(epochs * sleep_seconds, 3),
        },
        "notes": "Synthetic metrics generated for testing the education skill pack.",
    }

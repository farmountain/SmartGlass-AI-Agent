"""Utilities for exporting trained skills to quantized ONNX artifacts."""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from torch import Tensor, nn

try:  # pragma: no cover - import guard makes testing easier on minimal envs
    from onnxruntime.quantization import QuantType, quantize_dynamic
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "onnxruntime is required to run the export utilities"
    ) from exc

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportConfig:
    """Configuration describing how to export a trained skill."""

    skill_id: str
    model: nn.Module
    sample_input: Tensor
    targets: Tensor
    output_dir: Path
    opset_version: int = 17


@dataclass(frozen=True)
class ExportResult:
    """Artifact paths and metadata produced during export."""

    model_path: Path
    stats_path: Path
    stats: dict[str, Any]


class Int8Exporter:
    """Handle exporting a PyTorch module to an INT8 ONNX artifact."""

    def __init__(self, config: ExportConfig) -> None:
        self.config = config
        self.output_dir = config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.debug("Int8Exporter initialised with config: %s", self.config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def export(self) -> ExportResult:
        float_model_path = self._export_float_model()
        quantized_model_path = self._quantize_model(float_model_path)
        stats_path, stats = self._persist_stats(quantized_model_path)
        float_model_path.unlink(missing_ok=True)
        LOGGER.info(
            "Exported INT8 model for %s -> %s", self.config.skill_id, quantized_model_path
        )
        return ExportResult(quantized_model_path, stats_path, stats)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _export_float_model(self) -> Path:
        model = self.config.model.eval().cpu()
        dummy_input = self.config.sample_input.detach().cpu()
        if dummy_input.ndim == 1:
            dummy_input = dummy_input.unsqueeze(0)
        float_model_path = self.output_dir / f"{self.config.skill_id}.onnx"
        LOGGER.debug("Exporting float ONNX model to %s", float_model_path)
        torch.onnx.export(
            model,
            dummy_input,
            float_model_path,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
            opset_version=self.config.opset_version,
            dynamo=False,
        )
        return float_model_path

    def _quantize_model(self, float_model_path: Path) -> Path:
        quantized_path = self.output_dir / f"{self.config.skill_id}_int8.onnx"
        LOGGER.debug("Quantising %s -> %s", float_model_path, quantized_path)
        quantize_dynamic(
            model_input=str(float_model_path),
            model_output=str(quantized_path),
            weight_type=QuantType.QInt8,
        )
        return quantized_path

    def _persist_stats(self, model_path: Path) -> tuple[Path, dict[str, Any]]:
        targets = self.config.targets.detach().cpu()
        y_mean = float(targets.mean())
        y_std = float(targets.std(unbiased=False))
        stats = {
            "skill_id": self.config.skill_id,
            "model_path": model_path.name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "y_mean": y_mean,
            "y_std": y_std,
            "num_targets": int(targets.shape[0]),
            "opset_version": self.config.opset_version,
        }
        stats_path = self.output_dir / f"{self.config.skill_id}_stats.json"
        LOGGER.debug("Writing stats to %s", stats_path)
        stats_path.write_text(json.dumps(stats, indent=2))
        return stats_path, stats


def export_int8(config: ExportConfig) -> ExportResult:
    """Convenience wrapper around :class:`Int8Exporter`."""

    exporter = Int8Exporter(config)
    return exporter.export()


def add_arguments(parser: argparse.ArgumentParser) -> None:
    from . import trainer  # Local import to avoid circular dependency

    trainer.add_arguments(parser)
    parser.add_argument(
        "--skill-id",
        default="demo_skill",
        help="Identifier used when naming the exported artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory where the exported ONNX and stats artifacts will be written.",
    )
    parser.add_argument(
        "--opset-version",
        type=int,
        default=17,
        help="ONNX opset version used when tracing the PyTorch module.",
    )


def run(args: argparse.Namespace) -> int:
    from . import trainer

    config = trainer.build_config(args)
    skill_trainer = trainer.SkillTrainer(config)
    fit_result = skill_trainer.fit()

    calibration = trainer.load_dataset(
        config.dataset,
        "validation",
        samples=config.eval_samples,
        seed=config.seed + 1,
    )
    train_dataset = trainer.load_dataset(
        config.dataset,
        "train",
        samples=config.train_samples,
        seed=config.seed,
    )

    model = skill_trainer.get_model()
    export_config = ExportConfig(
        skill_id=args.skill_id,
        model=model,
        sample_input=calibration.features,
        targets=train_dataset.targets,
        output_dir=Path(args.output_dir),
        opset_version=args.opset_version,
    )
    export_result = export_int8(export_config)
    LOGGER.info(
        "Export completed for %s (loss=%.4f, residual_std=%.4f)",
        args.skill_id,
        fit_result.final_loss,
        fit_result.residual_std,
    )
    LOGGER.info(
        "Artifacts written to %s (stats: %s)",
        export_result.model_path,
        export_result.stats_path,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a trained skill to INT8 ONNX.")
    add_arguments(parser)
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

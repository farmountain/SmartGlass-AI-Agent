"""Utilities for calibrating CLIP logits using temperature or isotonic scaling."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import numpy as np
import yaml


@dataclass
class CalibrationResult:
    """Container for calibration outputs."""

    method: str
    ece: float
    probabilities: np.ndarray
    tau: Optional[float]
    artifact: Path

    def as_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "ece": self.ece,
            "probabilities": self.probabilities,
            "tau": self.tau,
            "artifact": str(self.artifact),
        }


class ClipCalibrator:
    """Calibrate CLIP logits via temperature or isotonic regression."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        artifact_root: Optional[Path] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        if config_path is None:
            config_path = base_dir.parent / "config" / "calibration.yaml"
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Calibration config not found: {self.config_path}")

        with self.config_path.open("r", encoding="utf-8") as fh:
            self.config: Dict[str, Any] = yaml.safe_load(fh) or {}

        if "targets" not in self.config:
            raise KeyError("Calibration config must define 'targets'.")

        artifact_root = artifact_root or self.config.get("artifact_root")
        if artifact_root is None:
            artifact_root = base_dir / "artifacts"
        self.artifact_root = Path(artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def calibrate(
        self,
        logits: np.ndarray,
        labels: Iterable[int],
        *,
        target: str = "clip",
        method: Optional[str] = None,
        force: bool = False,
    ) -> CalibrationResult:
        """Calibrate logits for the provided target/method configuration."""

        logits = np.asarray(logits, dtype=np.float64)
        labels = np.asarray(list(labels), dtype=np.int64)
        if logits.ndim != 2:
            raise ValueError("logits must be a 2D array")
        if labels.shape[0] != logits.shape[0]:
            raise ValueError("labels must have same length as logits")

        target_conf = self._get_target_config(target)
        bins = int(target_conf.get("bins", 15))
        methods_conf = target_conf.get("methods", {})
        if not methods_conf:
            raise KeyError(f"No methods defined for target '{target}'.")

        if method is None:
            method = next(iter(methods_conf))
        if method not in methods_conf:
            raise KeyError(f"Method '{method}' not configured for target '{target}'.")

        threshold = float(target_conf.get("ece_threshold", 0.05))
        artifact_path = self._artifact_path(methods_conf[method], target, method)

        if not force and artifact_path.exists():
            loaded = self._load_artifact(artifact_path)
            probabilities = self._apply_artifact(loaded, logits)
            ece = self.compute_ece(probabilities, labels, bins=bins)
            if ece <= threshold:
                return CalibrationResult(method, ece, probabilities, loaded.get("tau"), artifact_path)

        if method == "temperature":
            tau, probabilities = self._fit_temperature_scaling(logits, labels, bins)
            payload = {
                "method": method,
                "tau": tau,
            }
        elif method == "isotonic":
            mapping, probabilities = self._fit_isotonic_scaling(logits, labels, bins)
            payload = {
                "method": method,
                "mapping": mapping,
            }
            tau = None
        else:
            raise ValueError(f"Unsupported calibration method '{method}'.")

        ece = self.compute_ece(probabilities, labels, bins=bins)
        if ece > threshold:
            raise RuntimeError(
                f"Calibration ECE {ece:.4f} exceeds threshold {threshold:.4f} for method '{method}'."
            )

        payload.update(
            {
                "target": target,
                "ece": ece,
                "bins": bins,
            }
        )
        self._save_artifact(artifact_path, payload)
        return CalibrationResult(method, ece, probabilities, payload.get("tau"), artifact_path)

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def compute_ece(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
        *,
        bins: int = 15,
    ) -> float:
        """Compute the expected calibration error."""

        probs = np.asarray(probabilities, dtype=np.float64)
        if probs.ndim != 2:
            raise ValueError("probabilities must be 2D")
        if probs.shape[0] != labels.shape[0]:
            raise ValueError("labels must align with probabilities")

        confidences = probs.max(axis=1)
        predictions = probs.argmax(axis=1)
        correctness = (predictions == labels).astype(np.float64)

        bin_boundaries = np.linspace(0.0, 1.0, bins + 1)
        ece = 0.0
        total = len(confidences)
        for lower, upper in zip(bin_boundaries[:-1], bin_boundaries[1:]):
            in_bin = (confidences >= lower) & (confidences < upper)
            if math.isclose(upper, 1.0):
                in_bin |= confidences == 1.0
            count = int(np.sum(in_bin))
            if count == 0:
                continue
            acc = float(np.mean(correctness[in_bin]))
            conf = float(np.mean(confidences[in_bin]))
            ece += (count / total) * abs(acc - conf)
        return float(ece)

    @staticmethod
    def softmax(logits: np.ndarray) -> np.ndarray:
        """Compute softmax probabilities from logits."""

        logits = np.asarray(logits, dtype=np.float64)
        shifted = logits - np.max(logits, axis=1, keepdims=True)
        exp = np.exp(shifted)
        sums = np.sum(exp, axis=1, keepdims=True)
        return exp / sums

    # Internal helpers -------------------------------------------------
    def _get_target_config(self, target: str) -> Mapping[str, Any]:
        try:
            return self.config["targets"][target]
        except KeyError as exc:  # pragma: no cover - simple config error
            raise KeyError(f"Target '{target}' missing from calibration config") from exc

    def _artifact_path(self, method_conf: Mapping[str, Any], target: str, method: str) -> Path:
        filename = method_conf.get("artifact") or f"{target}_{method}.json"
        return self.artifact_root / filename

    def _load_artifact(self, path: Path) -> Mapping[str, Any]:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save_artifact(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)

    def _apply_artifact(self, artifact: Mapping[str, Any], logits: np.ndarray) -> np.ndarray:
        method = artifact.get("method")
        if method == "temperature":
            tau = float(artifact["tau"])
            return self._apply_temperature(logits, tau)
        if method == "isotonic":
            mapping = artifact["mapping"]
            return self._apply_isotonic(logits, mapping)
        raise ValueError(f"Unsupported artifact method '{method}'.")

    def _apply_temperature(self, logits: np.ndarray, tau: float) -> np.ndarray:
        scaled = logits / float(tau)
        return self.softmax(scaled)

    def _fit_temperature_scaling(
        self, logits: np.ndarray, labels: np.ndarray, bins: int
    ) -> Tuple[float, np.ndarray]:
        candidates = np.concatenate(
            [
                np.linspace(0.2, 2.0, num=25, dtype=np.float64),
                np.linspace(2.0, 12.0, num=250, dtype=np.float64),
            ]
        )
        best_tau = 1.0
        best_ece = float("inf")
        best_probs = self.softmax(logits)
        for tau in candidates:
            probs = self._apply_temperature(logits, tau)
            ece = self.compute_ece(probs, labels, bins=bins)
            if ece < best_ece:
                best_tau = float(tau)
                best_ece = ece
                best_probs = probs
        fine_candidates = np.linspace(
            max(0.1, best_tau - 0.5), best_tau + 0.5, num=50, dtype=np.float64
        )
        for tau in fine_candidates:
            probs = self._apply_temperature(logits, tau)
            ece = self.compute_ece(probs, labels, bins=bins)
            if ece < best_ece:
                best_tau = float(tau)
                best_ece = ece
                best_probs = probs
        return best_tau, best_probs

    def _fit_isotonic_scaling(
        self, logits: np.ndarray, labels: np.ndarray, bins: int
    ) -> Tuple[Mapping[str, List[float]], np.ndarray]:
        base_probs = self.softmax(logits)
        predictions = base_probs.argmax(axis=1)
        confidences = base_probs[np.arange(len(base_probs)), predictions]
        correctness = (predictions == labels).astype(np.float64)

        sorted_idx = np.argsort(confidences)
        sorted_conf = confidences[sorted_idx]
        sorted_corr = correctness[sorted_idx]

        block_values, block_sizes = self._pav(sorted_corr)
        block_maxes: List[float] = []
        expanded: List[float] = []
        start = 0
        for value, size in zip(block_values, block_sizes):
            end = start + size
            block_max = float(np.max(sorted_conf[start:end]))
            block_maxes.append(block_max)
            expanded.extend([value] * size)
            start = end
        calibrated_sorted = np.array(expanded, dtype=np.float64)

        calibrated = np.empty_like(calibrated_sorted)
        calibrated[sorted_idx] = calibrated_sorted

        calibrated_conf = np.clip(calibrated, 0.0, 1.0)

        calibrated_probs = base_probs.copy()
        rows = np.arange(len(base_probs))
        calibrated_probs[rows, predictions] = calibrated_conf
        other_sum = np.sum(calibrated_probs, axis=1) - calibrated_conf
        mask = other_sum > 0
        if np.any(mask):
            scale = (1.0 - calibrated_conf[mask]) / other_sum[mask]
            calibrated_probs[mask] *= scale[:, None]
            calibrated_probs[mask, predictions[mask]] = calibrated_conf[mask]
        zero_mask = ~mask
        if np.any(zero_mask):
            calibrated_probs[zero_mask, :] = 0.0
            calibrated_probs[zero_mask, predictions[zero_mask]] = 1.0

        mapping = {
            "maxes": block_maxes,
            "values": [float(v) for v in block_values],
            "sizes": [int(s) for s in block_sizes],
        }
        return mapping, calibrated_probs

    def _apply_isotonic(self, logits: np.ndarray, mapping: Mapping[str, Any]) -> np.ndarray:
        base_probs = self.softmax(logits)
        predictions = base_probs.argmax(axis=1)
        confidences = base_probs[np.arange(len(base_probs)), predictions]
        calibrated_conf = self._evaluate_mapping(confidences, mapping)

        calibrated_probs = base_probs.copy()
        rows = np.arange(len(base_probs))
        calibrated_probs[rows, predictions] = calibrated_conf
        other_sum = np.sum(calibrated_probs, axis=1) - calibrated_conf
        mask = other_sum > 0
        if np.any(mask):
            scale = (1.0 - calibrated_conf[mask]) / other_sum[mask]
            calibrated_probs[mask] *= scale[:, None]
            calibrated_probs[mask, predictions[mask]] = calibrated_conf[mask]
        zero_mask = ~mask
        if np.any(zero_mask):
            calibrated_probs[zero_mask, :] = 0.0
            calibrated_probs[zero_mask, predictions[zero_mask]] = 1.0
        return calibrated_probs

    def _evaluate_mapping(
        self, confidences: np.ndarray, mapping: Mapping[str, Any]
    ) -> np.ndarray:
        maxes = np.array(mapping["maxes"], dtype=np.float64)
        values = np.array(mapping["values"], dtype=np.float64)
        calibrated = np.empty_like(confidences, dtype=np.float64)
        for idx, conf in enumerate(confidences):
            pos = np.searchsorted(maxes, conf, side="right")
            pos = min(max(pos - 1, 0), len(values) - 1)
            calibrated[idx] = values[pos]
        return np.clip(calibrated, 0.0, 1.0)

    def _pav(self, y: np.ndarray) -> Tuple[List[float], List[int]]:
        values: List[float] = y.astype(np.float64).tolist()
        weights: List[int] = [1] * len(values)
        i = 0
        while i < len(values) - 1:
            if values[i] > values[i + 1]:
                total_weight = weights[i] + weights[i + 1]
                avg = (values[i] * weights[i] + values[i + 1] * weights[i + 1]) / total_weight
                values[i] = avg
                weights[i] = total_weight
                del values[i + 1]
                del weights[i + 1]
                if i > 0:
                    i -= 1
            else:
                i += 1
        return values, weights


__all__ = ["ClipCalibrator", "CalibrationResult"]

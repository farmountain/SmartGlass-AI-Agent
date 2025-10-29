import json
import sys
from pathlib import Path
from unittest import mock

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calibration.clip_calibrate import ClipCalibrator


CONFIG_PATH = ROOT / "config" / "calibration.yaml"


def make_temperature_dataset(num_samples: int = 200):
    rng = np.random.default_rng(1234)
    confidence = 0.9
    actual_accuracy = 0.6
    logits = np.tile([0.0, np.log(confidence / (1 - confidence))], (num_samples, 1))
    labels = rng.binomial(1, actual_accuracy, size=num_samples)
    return logits, labels


def make_isotonic_dataset():
    rng = np.random.default_rng(4321)
    logits_parts = []
    labels_parts = []

    def group(prob, correct_prob, pred_class, n):
        base = np.array([prob, 1 - prob])
        if pred_class == 1:
            distribution = np.array([1 - prob, prob])
        else:
            distribution = base
        logits = np.log(distribution)
        logits_parts.append(np.tile(logits, (n, 1)))
        outcomes = rng.binomial(1, correct_prob, size=n)
        if pred_class == 0:
            labels = np.where(outcomes == 1, 0, 1)
        else:
            labels = np.where(outcomes == 1, 1, 0)
        labels_parts.append(labels)

    group(0.8, 0.55, pred_class=0, n=120)
    group(0.85, 0.65, pred_class=1, n=80)

    logits = np.vstack(logits_parts)
    labels = np.concatenate(labels_parts)
    return logits, labels


def test_temperature_calibration_meets_threshold(tmp_path):
    calibrator = ClipCalibrator(config_path=CONFIG_PATH, artifact_root=tmp_path)
    logits, labels = make_temperature_dataset()
    base_probs = calibrator.softmax(logits)
    ece_before = calibrator.compute_ece(base_probs, labels)

    result = calibrator.calibrate(logits, labels, method="temperature")
    tau_expected = np.log(0.9 / 0.1) / np.log(0.6 / 0.4)

    assert result.tau == pytest.approx(tau_expected, rel=0.35)
    assert result.ece <= 0.05
    assert result.ece < ece_before
    assert Path(result.artifact).exists()

    with Path(result.artifact).open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    assert payload["tau"] == pytest.approx(result.tau)


def test_temperature_artifact_reuse(tmp_path):
    calibrator_first = ClipCalibrator(config_path=CONFIG_PATH, artifact_root=tmp_path)
    logits, labels = make_temperature_dataset()
    first = calibrator_first.calibrate(logits, labels, method="temperature")

    calibrator_second = ClipCalibrator(config_path=CONFIG_PATH, artifact_root=tmp_path)
    with mock.patch.object(
        calibrator_second, "_fit_temperature_scaling", side_effect=AssertionError("should not refit")
    ):
        reused = calibrator_second.calibrate(logits, labels, method="temperature")
    assert reused.tau == pytest.approx(first.tau)
    assert reused.ece == pytest.approx(first.ece)


def test_isotonic_calibration_reduces_ece(tmp_path):
    calibrator = ClipCalibrator(config_path=CONFIG_PATH, artifact_root=tmp_path)
    logits, labels = make_isotonic_dataset()
    base_probs = calibrator.softmax(logits)
    ece_before = calibrator.compute_ece(base_probs, labels)

    result = calibrator.calibrate(logits, labels, method="isotonic")

    assert result.ece <= 0.05
    assert result.ece < ece_before
    assert result.tau is None

    artifacts = list(tmp_path.glob("*.json"))
    assert artifacts

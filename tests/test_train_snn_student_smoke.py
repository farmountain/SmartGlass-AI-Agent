from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "train_snn_student.py"
REQUIRED_MODULES = ("torch", "transformers")


def _has_required_dependencies() -> bool:
    missing = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    if missing:
        pytest.skip(f"Missing dependencies for SNN student smoke test: {', '.join(missing)}")
    return True


@pytest.mark.skipif(not SCRIPT.exists(), reason="Training script is not available")
def test_train_snn_student_smoke(tmp_path):
    """Test basic training with default configuration (backward compatibility)."""
    _has_required_dependencies()

    output_dir = tmp_path / "artifacts" / "snn_student_smoke"
    output_dir.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--teacher-model",
            "sshleifer/tiny-gpt2",
            "--dataset",
            "synthetic",
            "--num-steps",
            "2",
            "--batch-size",
            "1",
            "--output-dir",
            str(output_dir),
            "--device",
            "cpu",
            "--log-interval",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        pytest.fail(
            "train_snn_student.py failed:\n"
            f"STDOUT:\n{completed.stdout}\n"
            f"STDERR:\n{completed.stderr}"
        )

    assert (output_dir / "student.pt").exists(), "Expected student.pt artifact was not created"
    assert (output_dir / "metadata.json").exists(), "Expected metadata.json artifact was not created"
    
    # Validate metadata structure
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    
    # Check core fields
    assert "model_type" in metadata
    assert "architecture_version" in metadata
    assert "vocab_size" in metadata
    assert "student_params" in metadata
    
    # Check nested structures
    assert "architecture" in metadata
    assert "snn_config" in metadata
    assert "training_config" in metadata
    assert "training_results" in metadata
    assert "metadata" in metadata
    
    # Verify SNN config defaults
    snn_config = metadata["snn_config"]
    assert snn_config["num_timesteps"] == 4
    assert snn_config["surrogate_type"] == "sigmoid"
    assert snn_config["spike_threshold"] == 1.0


@pytest.mark.skipif(not SCRIPT.exists(), reason="Training script is not available")
def test_train_snn_student_with_scheduler(tmp_path):
    """Test training with learning rate scheduler."""
    _has_required_dependencies()

    output_dir = tmp_path / "artifacts" / "snn_student_scheduler"
    output_dir.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--teacher-model",
            "sshleifer/tiny-gpt2",
            "--dataset",
            "synthetic",
            "--num-steps",
            "2",
            "--batch-size",
            "1",
            "--output-dir",
            str(output_dir),
            "--device",
            "cpu",
            "--scheduler",
            "cosine",
            "--warmup-steps",
            "1",
            "--log-interval",
            "0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        pytest.fail(
            "train_snn_student.py with scheduler failed:\n"
            f"STDOUT:\n{completed.stdout}\n"
            f"STDERR:\n{completed.stderr}"
        )

    assert (output_dir / "student.pt").exists()
    assert (output_dir / "metadata.json").exists()
    
    # Validate scheduler config in metadata
    with open(output_dir / "metadata.json", "r") as f:
        metadata = json.load(f)
    
    training_config = metadata["training_config"]
    assert training_config["scheduler"] == "cosine"
    assert training_config["warmup_steps"] == 1


@pytest.mark.skipif(not SCRIPT.exists(), reason="Training script is not available")
def test_train_snn_student_with_custom_snn_config(tmp_path):
    """Test training with custom SNN hyperparameters."""
    _has_required_dependencies()

    output_dir = tmp_path / "artifacts" / "snn_student_custom"
    output_dir.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--teacher-model",
            "sshleifer/tiny-gpt2",
            "--dataset",
            "synthetic",
            "--num-steps",
            "2",
            "--batch-size",
            "1",
            "--output-dir",
            str(output_dir),
            "--device",
            "cpu",
            "--snn-timesteps",
            "8",
            "--snn-surrogate",
            "fast_sigmoid",
            "--snn-threshold",
            "0.5",
            "--log-interval",
            "0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        pytest.fail(
            "train_snn_student.py with custom SNN config failed:\n"
            f"STDOUT:\n{completed.stdout}\n"
            f"STDERR:\n{completed.stderr}"
        )

    assert (output_dir / "student.pt").exists()
    assert (output_dir / "metadata.json").exists()
    
    # Validate custom SNN config in metadata
    with open(output_dir / "metadata.json", "r") as f:
        metadata = json.load(f)
    
    snn_config = metadata["snn_config"]
    assert snn_config["num_timesteps"] == 8
    assert snn_config["surrogate_type"] == "fast_sigmoid"
    assert snn_config["spike_threshold"] == 0.5

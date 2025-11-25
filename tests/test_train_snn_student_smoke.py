from __future__ import annotations

import importlib.util
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

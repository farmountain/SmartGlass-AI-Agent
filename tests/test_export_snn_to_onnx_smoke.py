import json
import subprocess
import sys
from pathlib import Path

import onnx
import torch

from scripts.train_snn_student import SpikingStudentLM



def test_export_snn_to_onnx_smoke(tmp_path: Path) -> None:
    """Build a minimal model, export to ONNX, and verify it loads."""

    vocab_size = 8

    model = SpikingStudentLM(vocab_size=vocab_size)
    model_path = tmp_path / "student.pt"
    torch.save(model.state_dict(), model_path)

    metadata = {"vocab_size": vocab_size}
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata))

    repo_root = Path(__file__).resolve().parents[1]
    onnx_path = tmp_path / "student.onnx"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.export_snn_to_onnx",
            "--model-path",
            str(model_path),
            "--metadata-path",
            str(metadata_path),
            "--output-path",
            str(onnx_path),
        ],
        check=True,
        cwd=repo_root,
    )

    assert onnx_path.exists(), "ONNX export did not produce a file"
    onnx_model = onnx.load(str(onnx_path))
    assert onnx_model is not None

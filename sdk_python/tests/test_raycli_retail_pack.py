"""CLI integration tests for the retail pack command."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("onnxruntime")

from sdk_python import raycli


@pytest.mark.slow
def test_train_retail_pack_updates_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "skills.json"
    manifest_path.write_text(
        json.dumps(
            {
                "skills": [
                    {
                        "id": "retail_stub",
                        "name": "Stub Retail",
                        "description": "Placeholder entry that should be preserved.",
                        "version": "0.0.1",
                        "model_path": "stub/model.bin",
                        "stats_path": "stub/stats.json",
                        "capabilities": ["retail"],
                    }
                ],
                "metadata": {"version": "test"},
            }
        )
    )

    output_root = tmp_path / "artifacts"
    argv = [
        "train_retail_pack",
        "--output-root",
        str(output_root),
        "--manifest-path",
        str(manifest_path),
        "--epochs",
        "1",
        "--train-samples",
        "16",
        "--eval-samples",
        "8",
        "--hidden-dim",
        "8",
        "--seed",
        "11",
    ]

    exit_code = raycli.main(argv)
    assert exit_code == 0

    manifest_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text())

    assert any(entry["id"] == "retail_stub" for entry in manifest["skills"])

    retail_ids = {
        "retail_wtp_radar",
        "retail_capsule_gaps",
        "retail_minute_meal",
    }
    entries = {entry["id"]: entry for entry in manifest["skills"] if entry["id"] in retail_ids}
    assert retail_ids == set(entries)

    for skill_id, entry in entries.items():
        model_path = manifest_dir / entry["model_path"]
        stats_path = manifest_dir / entry["stats_path"]
        assert model_path.exists(), f"model missing for {skill_id}"
        assert stats_path.exists(), f"stats missing for {skill_id}"

        stats = json.loads(stats_path.read_text())
        assert stats.get("skill_id") == skill_id
        assert "y_form_examples" in stats
        assert len(stats["y_form_examples"]) > 0

        metrics = entry.get("metrics")
        assert metrics is not None
        assert metrics["final_loss"] >= 0
        assert metrics["residual_std"] >= 0


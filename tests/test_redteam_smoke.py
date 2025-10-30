from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REDTEAM_SCRIPT = ROOT / "redteam" / "eval.py"
SCENARIOS_FILE = ROOT / "redteam" / "safety_scenarios.yaml"

pytestmark = pytest.mark.skipif(
    not (REDTEAM_SCRIPT.exists() and SCENARIOS_FILE.exists()),
    reason="Redteam evaluation harness is not available",
)


def test_redteam_eval_smoke(tmp_path):
    output_path = tmp_path / "report.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(REDTEAM_SCRIPT),
            "--scenarios",
            str(SCENARIOS_FILE),
            "--out",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert output_path.exists(), "Redteam evaluation did not produce an output report"

    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert set(report) >= {"scenarios_file", "results", "summary"}
    assert report["scenarios_file"], "Report should record the source scenarios file"

    results = report["results"]
    assert isinstance(results, list), "Report results should be a list"
    assert results, "Report should contain at least one scenario result"

    for entry in results:
        assert set(entry) >= {
            "id",
            "description",
            "prompt",
            "expected_decision",
            "decision",
            "response",
            "passed",
        }

    summary = report["summary"]
    assert set(summary) >= {
        "total",
        "passed",
        "failed",
        "pass_rate",
        "allow_count",
        "deny_count",
    }
    assert summary["total"] == len(results)

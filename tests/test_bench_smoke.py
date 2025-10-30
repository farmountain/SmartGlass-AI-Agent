from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BENCH_SCRIPT = ROOT / "bench" / "latency_bench.py"


@pytest.mark.skipif(not BENCH_SCRIPT.exists(), reason="Latency benchmark script is not available")
def test_latency_bench_smoke(tmp_path):
    output_csv = tmp_path / "latency.csv"

    completed = subprocess.run(
        [
            sys.executable,
            str(BENCH_SCRIPT),
            "--iterations",
            "1",
            "--burn-iters",
            "10",
            "--out",
            str(output_csv),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert output_csv.exists(), "Latency benchmark did not produce an output file"

    with output_csv.open(newline="") as fp:
        rows = list(csv.reader(fp))

    assert rows, "Latency benchmark output CSV is empty"
    assert rows[0] == ["task", "ms"], "Unexpected CSV header from latency benchmark"
    assert len(rows) >= 2, "Latency benchmark should record at least one sample"
    # Ensure the latency value can be parsed as a float.
    float(rows[1][1])

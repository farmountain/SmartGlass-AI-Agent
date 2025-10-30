"""Lightweight latency benchmark for SmartGlass components."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import sys
import time
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
_TELEMETRY_PATH = ROOT / "src" / "io" / "telemetry.py"
_SPEC = importlib.util.spec_from_file_location("smartglass.telemetry", _TELEMETRY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load telemetry module from {_TELEMETRY_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)

sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

MetricTimer = _MODULE.MetricTimer
log_metric = _MODULE.log_metric


def cpu_burn(iterations: int) -> float:
    """Perform a deterministic CPU-bound workload."""

    total = 0.0
    for i in range(iterations):
        total += math.sin(i % 256) * math.cos((i // 3) % 256)
    return total


def run_latency_bench(
    *,
    iterations: int,
    burn_iterations: int,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    log_metric("bench.iterations", iterations, unit="count")
    log_metric("bench.burn_iterations", burn_iterations, unit="count")

    with output_path.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["task", "ms"])

        for idx in range(1, iterations + 1):
            task_name = f"cpu_burn_{idx}"
            tags = {"iteration": str(idx)}
            with MetricTimer("bench.cpu_burn", unit="ms", tags=tags) as timer:
                cpu_burn(burn_iterations)
            assert timer.elapsed is not None
            writer.writerow([task_name, f"{timer.elapsed:.6f}"])
            log_metric(
                "bench.latency_sample",
                timer.elapsed,
                unit="ms",
                tags={"task": task_name},
            )


def _parse_args(args: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of benchmark iterations to perform.",
    )
    parser.add_argument(
        "--burn-iters",
        type=int,
        default=200_000,
        help="Number of loop iterations for the CPU burn workload.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/latency.csv"),
        help="Destination CSV file for latency samples.",
    )
    return parser.parse_args(args=args)


def main(args: Iterable[str] | None = None) -> None:
    ns = _parse_args(args)
    start = time.perf_counter()
    run_latency_bench(
        iterations=ns.iterations,
        burn_iterations=ns.burn_iters,
        output_path=ns.out,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    log_metric(
        "bench.total_runtime",
        elapsed_ms,
        unit="ms",
        tags={"output": str(ns.out)},
    )


if __name__ == "__main__":
    main()

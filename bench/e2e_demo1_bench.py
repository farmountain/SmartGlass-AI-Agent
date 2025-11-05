"""Benchmark the hero caption pipeline end-to-end."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import types
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Set

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC_PATH = ROOT / "src"
if "src" not in sys.modules:
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(SRC_PATH)]
    sys.modules["src"] = src_pkg

EXAMPLES_PATH = ROOT / "examples"
if str(EXAMPLES_PATH) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_PATH))

from examples.hero1_caption import HERO_STAGE_ORDER, run_hero_pipeline  # noqa: E402
from src.io.telemetry import log_metric  # noqa: E402


def _percentile(samples: List[float], percentile: float) -> float:
    if not samples:
        return 0.0
    if percentile <= 0:
        return min(samples)
    if percentile >= 100:
        return max(samples)
    ordered = sorted(samples)
    position = (len(ordered) - 1) * (percentile / 100.0)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[int(position)])
    lower_value = ordered[lower]
    upper_value = ordered[upper]
    fraction = position - lower
    return float(lower_value + (upper_value - lower_value) * fraction)


def run_benchmark(*, runs: int, output_csv: Path, summary_path: Path) -> Dict[str, object]:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    stage_samples: Dict[str, List[float]] = {stage: [] for stage in HERO_STAGE_ORDER}
    fusion_audio_conf: List[float] = []
    fusion_vision_conf: List[float] = []
    fusion_scores: List[float] = []
    fusion_audio_lat: List[float] = []
    fusion_vision_lat: List[float] = []
    totals: List[float] = []
    final_states: Counter[str] = Counter()
    providers: Set[str] = set()

    rows: List[Dict[str, object]] = []

    for run_idx in range(1, runs + 1):
        result = run_hero_pipeline(log=False)
        latencies = result["latencies"]
        metadata = result["metadata"]

        provider_name = str(result.get("provider", {}).get("name", "unknown"))
        providers.add(provider_name)

        row: Dict[str, object] = {"run": run_idx, "provider": provider_name}
        total = 0.0
        for stage in HERO_STAGE_ORDER:
            value = float(latencies.get(stage, 0.0))
            stage_samples[stage].append(value)
            row[stage] = f"{value:.6f}"
            total += value
        totals.append(total)
        row["total_ms"] = f"{total:.6f}"

        fusion_meta = metadata["fusion"]
        fusion_audio_conf.append(float(fusion_meta["audio_conf"]))
        fusion_vision_conf.append(float(fusion_meta["vision_conf"]))
        fusion_scores.append(float(fusion_meta["score"]))
        fusion_audio_lat.append(float(fusion_meta["audio_ms"]))
        fusion_vision_lat.append(float(fusion_meta["vision_ms"]))

        final_state = str(metadata["fsm"]["state"])
        final_states[final_state] += 1

        row["fusion_score"] = f"{fusion_meta['score']:.6f}"
        row["fusion_decision"] = str(bool(fusion_meta["decision"]))
        row["fsm_state"] = final_state
        row["caption_length"] = str(len(result["caption"]))
        rows.append(row)

    with output_csv.open("w", newline="") as fp:
        fieldnames = [
            "run",
            "provider",
            *HERO_STAGE_ORDER,
            "total_ms",
            "fusion_score",
            "fusion_decision",
            "fsm_state",
            "caption_length",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    summary = {
        "runs": runs,
        "stages": {
            stage: {
                "p50_ms": _percentile(stage_samples[stage], 50.0),
                "p95_ms": _percentile(stage_samples[stage], 95.0),
            }
            for stage in HERO_STAGE_ORDER
        },
        "totals": {
            "p50_ms": _percentile(totals, 50.0),
            "p95_ms": _percentile(totals, 95.0),
        },
        "fusion": {
            "audio_p50_ms": _percentile(fusion_audio_lat, 50.0),
            "vision_p50_ms": _percentile(fusion_vision_lat, 50.0),
            "combined_p50_ms": _percentile(fusion_audio_lat, 50.0) + _percentile(fusion_vision_lat, 50.0),
            "score_mean": mean(fusion_scores) if fusion_scores else 0.0,
            "audio_conf_mean": mean(fusion_audio_conf) if fusion_audio_conf else 0.0,
            "vision_conf_mean": mean(fusion_vision_conf) if fusion_vision_conf else 0.0,
        },
        "fsm": {
            "final_state_counts": dict(sorted(final_states.items())),
        },
        "providers": sorted(providers),
    }

    caption_p50 = summary["stages"].get("caption_ms", {}).get("p50_ms", 0.0)
    fusion_audio_p50 = summary["stages"].get("fusion_audio_ms", {}).get("p50_ms", 0.0)
    fusion_vision_p50 = summary["stages"].get("fusion_vision_ms", {}).get("p50_ms", 0.0)
    vision_audio_p50 = fusion_audio_p50 + fusion_vision_p50

    summary["aggregates"] = {
        "caption_p50_ms": caption_p50,
        "vision_audio_p50_ms": vision_audio_p50,
        "providers": summary["providers"],
        "total_p50_ms": summary["totals"].get("p50_ms", 0.0),
        "total_p95_ms": summary["totals"].get("p95_ms", 0.0),
    }

    if providers:
        primary_provider = sorted(providers)[0]
    else:
        primary_provider = "unknown"

    log_metric("hero1.p50", summary["totals"].get("p50_ms", 0.0), unit="ms", tags={"provider": primary_provider})
    log_metric("hero1.p95", summary["totals"].get("p95_ms", 0.0), unit="ms", tags={"provider": primary_provider})
    log_metric("hero1.va_p50", vision_audio_p50, unit="ms", tags={"provider": primary_provider})

    p50_row = {"run": "p50", "provider": ",".join(sorted(providers)) or primary_provider}
    p95_row = {"run": "p95", "provider": ",".join(sorted(providers)) or primary_provider}

    for stage in HERO_STAGE_ORDER:
        p50_row[stage] = f"{summary['stages'][stage]['p50_ms']:.6f}"
        p95_row[stage] = f"{summary['stages'][stage]['p95_ms']:.6f}"

    p50_row["total_ms"] = f"{summary['totals']['p50_ms']:.6f}"
    p95_row["total_ms"] = f"{summary['totals']['p95_ms']:.6f}"

    with output_csv.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writerow(p50_row)
        writer.writerow(p95_row)

    with summary_path.open("w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    return summary


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=30, help="Number of benchmark runs to execute")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("artifacts/e2e_hero1.csv"),
        help="Destination CSV path for per-run metrics",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("artifacts/e2e_hero1_summary.json"),
        help="Path for the aggregate summary JSON",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    args = _parse_args(argv)
    summary = run_benchmark(runs=args.runs, output_csv=args.csv, summary_path=args.summary)

    print(f"Hero benchmark executed {summary['runs']} runs")
    print("| Stage | p50 (ms) | p95 (ms) |")
    print("| --- | --- | --- |")
    for stage, stats in summary["stages"].items():
        print(f"| {stage} | {stats['p50_ms']:.3f} | {stats['p95_ms']:.3f} |")
    print("| total | {0:.3f} | {1:.3f} |".format(summary["totals"]["p50_ms"], summary["totals"]["p95_ms"]))

    fusion = summary["fusion"]
    print()
    print("Fusion combined p50: {0:.3f} ms".format(fusion["combined_p50_ms"]))
    print("Mean fusion score: {0:.3f}".format(fusion["score_mean"]))

    fsm = summary["fsm"]["final_state_counts"]
    print("FSM final state distribution:")
    for state, count in fsm.items():
        print(f"  - {state}: {count}")


if __name__ == "__main__":
    main()

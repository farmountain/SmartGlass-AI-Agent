"""Benchmark RaySkillKit runtime performance with duty-cycle controls."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # pragma: no cover - import side effect
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:  # pragma: no cover - import side effect
    sys.path.insert(0, str(SRC))

import numpy as np

from controls.duty_cycle import DutyCycleScheduler
from fsm import HandshakeFSM, load_handshake_budgets
from fsm.handshake import TimerDriver, TimerHandle
from rayskillkit import RaySkillKitRuntime
from src.io.telemetry import MetricTimer, log_metric
from bench.phone_perf_timeline import (
    DUTY_CYCLE_TIMELINE,
    TIMELINE_REQUEST_INTERVAL_S,
)


class PassiveTimerHandle(TimerHandle):
    """Timer handle that satisfies :class:`TimerDriver` but never fires."""

    def cancel(self) -> None:  # pragma: no cover - trivial
        return None


class PassiveTimerDriver(TimerDriver):
    """Timer driver that keeps the FSM READY without scheduling callbacks."""

    def now(self) -> float:
        return time.perf_counter()

    def call_later(self, delay: float, callback: Callable[[], None]) -> TimerHandle:  # pragma: no cover - deterministic
        return PassiveTimerHandle()


class SyntheticOrt:
    """Light-weight ONNX Runtime stub that burns measurable CPU cycles."""

    def __init__(self, feature_size: int, hidden_size: int = 128) -> None:
        self.calls = 0
        base = np.linspace(0.5, 1.5, feature_size * hidden_size, dtype=np.float32)
        self._weights = base.reshape(feature_size, hidden_size)

    def infer(self, model_name: str, features: np.ndarray) -> np.ndarray:
        self.calls += 1
        projection = features @ self._weights
        activated = np.tanh(projection)
        return activated


@dataclass
class ScenarioResult:
    scenario: str
    duty_cycle_enabled: bool
    wall_time_s: float
    cpu_time_s: float
    battery_proxy: float
    total_calls: int
    inference_rate_hz: float

    def to_row(self) -> Dict[str, str]:
        return {
            "scenario": self.scenario,
            "duty_cycle": "1" if self.duty_cycle_enabled else "0",
            "wall_time_s": f"{self.wall_time_s:.6f}",
            "cpu_time_s": f"{self.cpu_time_s:.6f}",
            "battery_proxy": f"{self.battery_proxy:.6f}",
            "total_calls": str(self.total_calls),
            "inference_rate_hz": f"{self.inference_rate_hz:.6f}",
        }


def _build_runtime(use_duty_cycle: bool, idle_hz: float) -> RaySkillKitRuntime:
    budgets = load_handshake_budgets(Path("config/ux_budgets.yaml"))
    timer = PassiveTimerDriver()
    fsm = HandshakeFSM(timer=timer, budgets=budgets)
    scheduler = DutyCycleScheduler(timer, idle_hz=idle_hz if use_duty_cycle else 0.0, active_hz=0.0)
    runtime = RaySkillKitRuntime(handshake=fsm, scheduler=scheduler)
    fsm.pair()
    if use_duty_cycle:
        fsm.mark_user_idle()
    else:
        fsm.mark_user_active()
    return runtime


def _simulate_workload(
    runtime: RaySkillKitRuntime,
    ort: SyntheticOrt,
    *,
    duration: float,
    work_interval: float,
    feature_size: int,
    scenario: str,
    duty_cycle_enabled: bool,
) -> ScenarioResult:
    tags = {"scenario": scenario, "duty_cycle": str(duty_cycle_enabled).lower()}
    total_calls = 0
    start_cpu = time.process_time()
    with MetricTimer("phone_perf.wall_time", unit="ms", tags=tags) as timer:
        deadline = time.perf_counter() + duration
        while time.perf_counter() < deadline:
            features = np.random.rand(feature_size).astype(np.float32)
            result = runtime.run_inference(ort, "synthetic_skill", features)
            if result is not None:
                total_calls += 1
            if work_interval > 0:
                time.sleep(work_interval)
    wall_time_s = (timer.elapsed or 0.0) / 1000.0
    cpu_time_s = time.process_time() - start_cpu
    battery_proxy = (cpu_time_s / wall_time_s) if wall_time_s else 0.0
    inference_rate = (total_calls / wall_time_s) if wall_time_s else 0.0

    log_metric("phone_perf.cpu_time", cpu_time_s, unit="s", tags=tags)
    log_metric("phone_perf.battery_proxy", battery_proxy, unit="ratio", tags=tags)
    log_metric("phone_perf.inference_rate", inference_rate, unit="hz", tags=tags)
    log_metric("phone_perf.inference_calls", total_calls, unit="count", tags=tags)

    return ScenarioResult(
        scenario=scenario,
        duty_cycle_enabled=duty_cycle_enabled,
        wall_time_s=wall_time_s,
        cpu_time_s=cpu_time_s,
        battery_proxy=battery_proxy,
        total_calls=total_calls,
        inference_rate_hz=inference_rate,
    )


def _write_csv(result: ScenarioResult, artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / f"phone_perf_{result.scenario}.csv"
    fieldnames = [
        "scenario",
        "duty_cycle",
        "wall_time_s",
        "cpu_time_s",
        "battery_proxy",
        "total_calls",
        "inference_rate_hz",
    ]
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(result.to_row())
    return path


def _write_timeline_csv(artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / "phone_perf_timeline.csv"
    fieldnames = [
        "segment",
        "start_s",
        "end_s",
        "duration_s",
        "engagement",
        "request_interval_s",
    ]
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for idx, slice_ in enumerate(DUTY_CYCLE_TIMELINE):
            writer.writerow(
                {
                    "segment": idx,
                    "start_s": f"{slice_.start_s:.3f}",
                    "end_s": f"{slice_.end_s:.3f}",
                    "duration_s": f"{slice_.duration_s:.3f}",
                    "engagement": slice_.engagement,
                    "request_interval_s": f"{TIMELINE_REQUEST_INTERVAL_S:.3f}",
                }
            )
    return path


def _log_summary(result: ScenarioResult) -> None:
    payload = {
        "scenario": result.scenario,
        "duty_cycle": result.duty_cycle_enabled,
        "wall_time_s": round(result.wall_time_s, 6),
        "cpu_time_s": round(result.cpu_time_s, 6),
        "battery_proxy": round(result.battery_proxy, 6),
        "inference_rate_hz": round(result.inference_rate_hz, 6),
        "total_calls": result.total_calls,
    }
    print(f"PHONE_PERF_SUMMARY {json.dumps(payload, sort_keys=True)}")


def _scenario_names(mode: str) -> list[str]:
    if mode == "both":
        return ["baseline", "duty_cycle"]
    return [mode]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=5.0, help="Benchmark duration per scenario in seconds")
    parser.add_argument(
        "--feature-size",
        type=int,
        default=1024,
        help="Number of synthetic features per RaySkillKit inference",
    )
    parser.add_argument(
        "--work-interval",
        type=float,
        default=0.01,
        help="Sleep interval between inference attempts to simulate frame cadence",
    )
    parser.add_argument(
        "--idle-hz",
        type=float,
        default=2.0,
        help="Duty-cycle frequency when the wearable is idle",
    )
    parser.add_argument(
        "--mode",
        choices=("baseline", "duty_cycle", "both"),
        default="both",
        help="Select which scenario(s) to run",
    )
    args = parser.parse_args()

    artifacts_root = Path(os.environ.get("SMARTGLASS_ARTIFACTS_DIR", "artifacts"))
    ort = SyntheticOrt(args.feature_size)
    results: list[ScenarioResult] = []

    for scenario in _scenario_names(args.mode):
        duty_cycle_enabled = scenario == "duty_cycle"
        runtime = _build_runtime(duty_cycle_enabled, args.idle_hz)
        result = _simulate_workload(
            runtime,
            ort,
            duration=args.duration,
            work_interval=args.work_interval,
            feature_size=args.feature_size,
            scenario=scenario,
            duty_cycle_enabled=duty_cycle_enabled,
        )
        _write_csv(result, artifacts_root)
        _log_summary(result)
        results.append(result)

    timeline_path = _write_timeline_csv(artifacts_root)
    print(f"Exported deterministic engagement timeline to {timeline_path}")

    if len(results) > 1:
        combined = artifacts_root / "phone_perf_summary.csv"
        with combined.open("w", newline="") as fp:
            fieldnames = list(results[0].to_row().keys())
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(result.to_row())
        print(f"Wrote consolidated summary to {combined}")


if __name__ == "__main__":
    main()

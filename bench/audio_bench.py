"""Benchmark EnergyVAD and ASRStream components on synthetic signals."""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio import ASRStream, EnergyVAD, MockASR  # noqa: E402  (import after sys.path patch)
from src.io.telemetry import log_metric  # noqa: E402


@dataclass(frozen=True)
class SignalSpec:
    """Container describing a synthetic audio benchmark case."""

    name: str
    samples: np.ndarray
    partials: Sequence[Dict[str, object]]


def _tone(duration_s: float, *, freq_hz: float, sample_rate: int, amplitude: float = 0.4) -> np.ndarray:
    """Return a Hann-windowed tone burst."""

    total = max(1, int(round(duration_s * sample_rate)))
    t = np.arange(total, dtype=np.float32) / float(sample_rate)
    carrier = np.sin(2.0 * math.pi * freq_hz * t)
    window = np.hanning(total)
    return (amplitude * carrier * window).astype(np.float32)


def _silence(duration_s: float, *, sample_rate: int) -> np.ndarray:
    total = max(1, int(round(duration_s * sample_rate)))
    return np.zeros(total, dtype=np.float32)


def _noise(duration_s: float, *, sample_rate: int, scale: float, rng: np.random.Generator) -> np.ndarray:
    total = max(1, int(round(duration_s * sample_rate)))
    return rng.normal(loc=0.0, scale=scale, size=total).astype(np.float32)


def _synth_signals(*, sample_rate: int) -> Sequence[SignalSpec]:
    """Generate three deterministic one-second benchmark signals."""

    if sample_rate != 16_000:
        raise ValueError("audio bench expects a 16 kHz sample rate")

    duration_s = 1.0
    rng = np.random.default_rng(12345)

    silence = _silence(duration_s, sample_rate=sample_rate)
    silence_partials: Sequence[Dict[str, object]] = (
        {"text": "", "timestamp": (0.0, 0.5)},
        {"text": "", "timestamp": (0.5, 1.0)},
    )

    tone = _tone(duration_s, freq_hz=440.0, sample_rate=sample_rate, amplitude=0.5)
    tone_partials: Sequence[Dict[str, object]] = (
        {"text": "han", "timestamp": (0.0, 0.33)},
        {"text": "hann", "timestamp": (0.33, 0.66)},
        {"text": "hann tone", "timestamp": (0.66, 1.0)},
    )

    noise = _noise(duration_s, sample_rate=sample_rate, scale=0.1, rng=rng)
    noise_partials: Sequence[Dict[str, object]] = (
        {"text": "static", "timestamp": (0.0, 0.4)},
        {"text": "static noise", "timestamp": (0.4, 0.8)},
        {"text": "static", "timestamp": (0.8, 1.0)},
    )

    return (
        SignalSpec("silence", silence, silence_partials),
        SignalSpec("hann_sine", tone, tone_partials),
        SignalSpec("white_noise", noise, noise_partials),
    )


def _count_reversals(transcripts: Iterable[str]) -> int:
    """Count the number of times a transcript loses stable tokens."""

    previous_tokens: List[str] = []
    reversals = 0
    for text in transcripts:
        tokens = text.split()
        prefix_len = 0
        for before, after in zip(previous_tokens, tokens):
            if before == after:
                prefix_len += 1
            else:
                break
        if previous_tokens and prefix_len < len(previous_tokens):
            reversals += 1
        previous_tokens = tokens
    return reversals


def _analyse_signal(
    spec: SignalSpec,
    *,
    vad: EnergyVAD,
    stability_window: int,
    stability_delta: float,
) -> Dict[str, object]:
    """Run a benchmark signal through EnergyVAD and ASRStream."""

    frames_processed = 0
    for frame in vad.frames(spec.samples):
        frames_processed += 1
        # Exercise the VAD decision path so timing in production stays relevant.
        vad.is_speech(frame)

    stream = ASRStream(
        asr=MockASR(spec.partials),
        stability_window=stability_window,
        stability_delta=stability_delta,
    )

    first_partial_ms: float = 0.0
    partials_count = 0
    partial_texts: List[str] = []

    for event in stream.run():
        if event.get("is_final"):
            continue
        partials_count += 1
        partial_text = str(event.get("text", ""))
        partial_texts.append(partial_text)
        if first_partial_ms == 0.0:
            first_partial_ms = float(event.get("t_first_ms", 0.0))

    reversal_count = _count_reversals(partial_texts)
    reversal_rate = reversal_count / max(1, partials_count)

    tags = {"signal": spec.name}
    log_metric("audio_bench.first_partial_ms", first_partial_ms, unit="ms", tags=tags)
    log_metric("audio_bench.partials_count", partials_count, unit="count", tags=tags)
    log_metric("audio_bench.reversal_rate", reversal_rate, unit="ratio", tags=tags)
    log_metric("audio_bench.frames_processed", frames_processed, unit="count", tags=tags)

    return {
        "signal": spec.name,
        "first_partial_ms": first_partial_ms,
        "partials_count": partials_count,
        "reversal_rate": reversal_rate,
        "frames_processed": frames_processed,
    }


def run_audio_bench(
    *,
    output_path: Path,
    sample_rate: int,
    frame_ms: float,
    threshold: float,
    stability_window: int,
    stability_delta: float,
) -> Sequence[Dict[str, object]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    vad = EnergyVAD(frame_ms=frame_ms, sample_rate=sample_rate, threshold=threshold)
    signals = _synth_signals(sample_rate=sample_rate)

    results = [
        _analyse_signal(signal, vad=vad, stability_window=stability_window, stability_delta=stability_delta)
        for signal in signals
    ]

    with output_path.open("w", newline="") as fp:
        fieldnames = [
            "signal",
            "first_partial_ms",
            "partials_count",
            "reversal_rate",
            "frames_processed",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    return results


def _parse_args(args: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("artifacts/audio_latency.csv"), help="Destination CSV path.")
    parser.add_argument("--sample-rate", type=int, default=16_000, help="Sample rate for synthetic signals.")
    parser.add_argument("--frame-ms", type=float, default=2.0, help="Frame size passed to EnergyVAD.")
    parser.add_argument("--threshold", type=float, default=1e-3, help="Energy threshold for VAD decisions.")
    parser.add_argument(
        "--stability-window",
        type=int,
        default=4,
        help="Number of partials considered when stabilising ASR output.",
    )
    parser.add_argument(
        "--stability-delta",
        type=float,
        default=0.25,
        help="Instability tolerance used by the ASRStream delta gate.",
    )
    return parser.parse_args(args=args)


def main(args: Iterable[str] | None = None) -> None:
    ns = _parse_args(args)
    start = time.perf_counter()
    results = run_audio_bench(
        output_path=ns.out,
        sample_rate=ns.sample_rate,
        frame_ms=ns.frame_ms,
        threshold=ns.threshold,
        stability_window=ns.stability_window,
        stability_delta=ns.stability_delta,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    log_metric(
        "audio_bench.total_runtime",
        elapsed_ms,
        unit="ms",
        tags={"output": str(ns.out), "cases": str(len(results))},
    )


if __name__ == "__main__":
    main()

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
    """Generate deterministic audio buffers and scripted ASR partials."""

    rng = np.random.default_rng(12345)

    # 1) Baseline silence measurement.
    silence = _silence(1.0, sample_rate=sample_rate)
    silence_partials: Sequence[Dict[str, object]] = (
        {"text": "", "timestamp": (0.0, 0.5)},
        {"text": "", "timestamp": (0.5, 1.0)},
    )

    # 2) Tone burst simulating a wake-word like signal.
    burst = np.concatenate(
        [
            _silence(0.15, sample_rate=sample_rate),
            _tone(0.7, freq_hz=440.0, sample_rate=sample_rate, amplitude=0.35),
            _silence(0.15, sample_rate=sample_rate),
        ]
    )
    burst_partials: Sequence[Dict[str, object]] = (
        {"text": "wake", "timestamp": (0.0, 0.3)},
        {"text": "wake word", "timestamp": (0.0, 0.6)},
        {"text": "wake wrd", "timestamp": (0.0, 0.9)},
        {"text": "wake word", "timestamp": (0.0, 1.2)},
    )

    # 3) Speech-like pattern with modulated tones and low noise.
    words = [
        ("the", 210.0),
        ("smart", 260.0),
        ("glasses", 310.0),
        ("detect", 360.0),
        ("motion", 410.0),
        ("quickly", 460.0),
    ]
    segments: List[np.ndarray] = []
    for idx, (token, freq) in enumerate(words):
        duration = 0.28 + 0.02 * idx
        envelope = _tone(duration, freq_hz=freq, sample_rate=sample_rate, amplitude=0.45)
        noise = _noise(duration, sample_rate=sample_rate, scale=0.015, rng=rng)
        segments.append(envelope + noise)
        segments.append(_silence(0.06, sample_rate=sample_rate))
    phrase = np.concatenate(segments[:-1])  # drop trailing silence to keep length tidy
    phrase_partials: Sequence[Dict[str, object]] = (
        {"text": "the smart", "timestamp": (0.0, 0.5)},
        {"text": "the smart glasses", "timestamp": (0.0, 0.8)},
        {"text": "the smart glasses detect", "timestamp": (0.0, 1.1)},
        {"text": "the smart glasses detect motion", "timestamp": (0.0, 1.4)},
        {"text": "the smart glasses detect motion quickly", "timestamp": (0.0, 1.7)},
    )

    return (
        SignalSpec("silence", silence, silence_partials),
        SignalSpec("tone_burst", burst, burst_partials),
        SignalSpec("noisy_phrase", phrase, phrase_partials),
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
    """Measure VAD and ASR behaviour for a given benchmark signal."""

    start = time.perf_counter()
    frames = list(vad.frames(spec.samples))
    frame_runtime_ms = (time.perf_counter() - start) * 1000.0

    speech_frames = sum(1 for frame in frames if vad.is_speech(frame))

    partial_reversals = _count_reversals(partial["text"] for partial in spec.partials)

    stream = ASRStream(
        asr=MockASR(spec.partials),
        stability_window=stability_window,
        stability_delta=stability_delta,
    )

    start = time.perf_counter()
    events = list(stream.run())
    asr_runtime_ms = (time.perf_counter() - start) * 1000.0

    finals = [event["text"] for event in events if event.get("is_final")]
    final_reversals = _count_reversals(finals)
    final_transcript = finals[-1] if finals else ""

    result: Dict[str, object] = {
        "signal": spec.name,
        "sample_rate": vad.sample_rate,
        "frame_ms": vad.frame_ms,
        "frames": len(frames),
        "speech_frames": speech_frames,
        "vad_latency_ms": frame_runtime_ms,
        "asr_events": len(events),
        "asr_latency_ms": asr_runtime_ms,
        "partial_reversals": partial_reversals,
        "final_reversals": final_reversals,
        "final_transcript": final_transcript,
    }

    tags = {"signal": spec.name}
    log_metric("audio_bench.vad_frames", len(frames), unit="count", tags=tags)
    log_metric("audio_bench.vad_speech_frames", speech_frames, unit="count", tags=tags)
    log_metric("audio_bench.vad_latency", frame_runtime_ms, unit="ms", tags=tags)
    log_metric("audio_bench.asr_events", len(events), unit="count", tags=tags)
    log_metric("audio_bench.asr_latency", asr_runtime_ms, unit="ms", tags=tags)
    log_metric("audio_bench.partial_reversals", partial_reversals, unit="count", tags=tags)
    log_metric("audio_bench.final_reversals", final_reversals, unit="count", tags=tags)

    return result


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
        fieldnames = list(results[0].keys()) if results else [
            "signal",
            "sample_rate",
            "frame_ms",
            "frames",
            "speech_frames",
            "vad_latency_ms",
            "asr_events",
            "asr_latency_ms",
            "partial_reversals",
            "final_reversals",
            "final_transcript",
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

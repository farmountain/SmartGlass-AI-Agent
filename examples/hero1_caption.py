"""End-to-end hero caption pipeline demo with deterministic mocks.

The pipeline synthesises a simple moving-square video clip alongside a
corresponding synthetic audio stream. The clip is passed through the
energy-based VAD, streaming ASR mock, keyframe selector, fusion gate,
FSM router, caption skill, and TTS stub. Each stage records its latency
so that downstream tooling (for example the hero benchmark) can report
aggregate performance metrics.

Running this module directly prints a concise summary of the generated
caption together with per-stage latencies.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence
import types

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC_PATH = ROOT / "src"
if "src" not in sys.modules:
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(SRC_PATH)]
    sys.modules["src"] = src_pkg

from src.audio import ASRStream, EnergyVAD, MockASR  # noqa: E402
from src.io.tts import speak  # noqa: E402
from src.perception import get_default_keyframer  # noqa: E402
from src.policy.fsm import Event, FSMRouter, State  # noqa: E402
from src.skills import MockCaptioner  # noqa: E402

__all__ = [
    "FusionGate",
    "HERO_STAGE_ORDER",
    "generate_moving_square_clip",
    "run_hero_pipeline",
]


# Ordered list of latency keys emitted by :func:`run_hero_pipeline`.
HERO_STAGE_ORDER = [
    "synth_clip_ms",
    "synth_audio_ms",
    "vad_ms",
    "asr_ms",
    "keyframe_ms",
    "fusion_audio_ms",
    "fusion_vision_ms",
    "fusion_gate_ms",
    "fsm_ms",
    "caption_ms",
    "tts_ms",
]


@dataclass(frozen=True)
class FusionResult:
    """Container describing the fusion gate decision."""

    audio_conf: float
    vision_conf: float
    score: float
    decision: bool
    audio_ms: float
    vision_ms: float
    total_ms: float


class FusionGate:
    """Soft fusion gate that blends audio and vision confidences."""

    def __init__(self, *, audio_weight: float = 0.45, vision_weight: float = 0.55, threshold: float = 0.35) -> None:
        if not 0.0 <= audio_weight <= 1.0:
            raise ValueError("audio_weight must lie within [0, 1]")
        if not 0.0 <= vision_weight <= 1.0:
            raise ValueError("vision_weight must lie within [0, 1]")
        if math.isclose(audio_weight + vision_weight, 0.0):
            raise ValueError("audio_weight + vision_weight must be > 0")
        if threshold <= 0.0:
            raise ValueError("threshold must be positive")

        total = audio_weight + vision_weight
        self.audio_weight = audio_weight / total
        self.vision_weight = vision_weight / total
        self.threshold = threshold

    @staticmethod
    def _squash(value: float) -> float:
        """Deterministically squash scores to ``[0, 1]`` via a sigmoid."""

        return 1.0 / (1.0 + math.exp(-float(value)))

    def evaluate(self, audio_signal: float, vision_signal: float) -> FusionResult:
        """Blend audio and vision signals into a gate decision."""

        audio_start = time.perf_counter()
        audio_conf = self._squash(audio_signal)
        audio_ms = (time.perf_counter() - audio_start) * 1000.0

        vision_start = time.perf_counter()
        vision_conf = self._squash(vision_signal)
        vision_ms = (time.perf_counter() - vision_start) * 1000.0

        score = self.audio_weight * audio_conf + self.vision_weight * vision_conf
        decision = score >= self.threshold

        return FusionResult(
            audio_conf=audio_conf,
            vision_conf=vision_conf,
            score=score,
            decision=decision,
            audio_ms=audio_ms,
            vision_ms=vision_ms,
            total_ms=audio_ms + vision_ms,
        )


def generate_moving_square_clip(*, num_frames: int = 24, frame_size: int = 48, square_size: int = 12) -> np.ndarray:
    """Return a ``(T, H, W)`` array depicting a square translating rightwards."""

    frames: List[np.ndarray] = []
    limit = frame_size - square_size
    for idx in range(num_frames):
        frame = np.zeros((frame_size, frame_size), dtype=np.float32)
        top = frame_size // 3
        left = min(limit, int(round(idx * (limit / max(1, num_frames - 1)))))
        frame[top : top + square_size, left : left + square_size] = 1.0
        frames.append(frame)
    return np.stack(frames, axis=0)


def _synth_audio_buffer(*, duration_s: float = 1.0, sample_rate: int = 16_000, tone_freq: float = 440.0) -> np.ndarray:
    """Synthesize a mono waveform with a voiced centre segment."""

    total_samples = int(round(duration_s * sample_rate))
    t = np.linspace(0.0, duration_s, num=total_samples, endpoint=False, dtype=np.float32)
    waveform = 0.15 * np.sin(2.0 * math.pi * tone_freq * t)
    envelope = np.zeros_like(waveform)
    start = int(total_samples * 0.2)
    end = int(total_samples * 0.8)
    envelope[start:end] = 1.0
    return waveform * envelope


def _run_vad(vad: EnergyVAD, audio: np.ndarray) -> Dict[str, float]:
    frames = list(vad.frames(audio))
    speech_frames = sum(1 for frame in frames if vad.is_speech(frame))
    total_frames = max(1, len(frames))
    speech_ratio = speech_frames / total_frames
    return {
        "frames": frames,
        "speech_frames": speech_frames,
        "speech_ratio": speech_ratio,
    }


def _run_asr(asr_stream: ASRStream) -> Dict[str, object]:
    final_text = ""
    partials: List[Dict[str, object]] = []
    for chunk in asr_stream.run():
        partials.append(chunk)
        if chunk.get("is_final"):
            final_text = str(chunk.get("text", ""))
    return {
        "partials": partials,
        "transcript": final_text,
    }


def _build_router() -> FSMRouter:
    states = [
        State("IDLE"),
        State("LISTENING"),
        State("ANALYSING"),
        State("RESPONDING", irreversible=True),
    ]
    events = [
        Event("activate", source="IDLE", target="LISTENING"),
        Event("observe", source="LISTENING", target="ANALYSING"),
        Event("respond", source="ANALYSING", target="RESPONDING"),
    ]
    return FSMRouter(states, events, initial_state="IDLE")


def _format_stage(stage: str, ms: float) -> str:
    return f"  - {stage}: {ms:.3f} ms"


def run_hero_pipeline(*, log: bool = True) -> Dict[str, object]:
    """Execute the hero caption pipeline and return structured results."""

    latencies: Dict[str, float] = {}
    metadata: Dict[str, object] = {}

    start = time.perf_counter()
    frames = generate_moving_square_clip()
    latencies["synth_clip_ms"] = (time.perf_counter() - start) * 1000.0

    start = time.perf_counter()
    audio = _synth_audio_buffer()
    latencies["synth_audio_ms"] = (time.perf_counter() - start) * 1000.0

    vad = EnergyVAD(frame_ms=2.0, sample_rate=16_000, threshold=1e-4)
    start = time.perf_counter()
    vad_info = _run_vad(vad, audio)
    latencies["vad_ms"] = (time.perf_counter() - start) * 1000.0

    transcript = "a bright square glides across the frame"
    partials = MockASR.from_transcript(transcript, splits=[3, 6, 10, len(transcript.split())])
    asr_stream = ASRStream(asr=partials, stability_window=4, stability_delta=0.15)
    start = time.perf_counter()
    asr_info = _run_asr(asr_stream)
    latencies["asr_ms"] = (time.perf_counter() - start) * 1000.0

    keyframer = get_default_keyframer()
    start = time.perf_counter()
    key_indices = keyframer(frames, min_gap=3)
    latencies["keyframe_ms"] = (time.perf_counter() - start) * 1000.0

    gate = FusionGate()
    audio_signal = vad_info["speech_ratio"] * 2.0 - 0.5
    vision_signal = (len(key_indices) / max(1, frames.shape[0])) * 3.0 - 0.5
    start = time.perf_counter()
    fusion = gate.evaluate(audio_signal, vision_signal)
    fusion_total_ms = (time.perf_counter() - start) * 1000.0
    latencies["fusion_audio_ms"] = fusion.audio_ms
    latencies["fusion_vision_ms"] = fusion.vision_ms
    latencies["fusion_gate_ms"] = fusion_total_ms

    router = _build_router()
    start = time.perf_counter()
    router.transition("activate")
    router.transition("observe")
    router.transition("respond", confirm=True)
    latencies["fsm_ms"] = (time.perf_counter() - start) * 1000.0

    captioner = MockCaptioner()
    start = time.perf_counter()
    caption = captioner.generate(frames, ocr_text="Exit")
    latencies["caption_ms"] = (time.perf_counter() - start) * 1000.0

    start = time.perf_counter()
    tts_result = speak(caption)
    latencies["tts_ms"] = (time.perf_counter() - start) * 1000.0

    total_ms = sum(latencies.values())

    metadata["fusion"] = {
        "audio_conf": fusion.audio_conf,
        "vision_conf": fusion.vision_conf,
        "score": fusion.score,
        "decision": fusion.decision,
        "audio_ms": fusion.audio_ms,
        "vision_ms": fusion.vision_ms,
    }
    metadata["fsm"] = {
        "state": router.state.name,
    }
    metadata["vad"] = {
        "speech_frames": vad_info["speech_frames"],
        "speech_ratio": vad_info["speech_ratio"],
    }
    metadata["asr"] = {
        "transcript": asr_info["transcript"],
        "partials": len(asr_info["partials"]),
    }
    metadata["keyframes"] = {
        "count": len(key_indices),
        "indices": key_indices,
    }
    metadata["tts"] = {
        "char_count": tts_result.char_count,
        "duration": tts_result.duration,
    }

    result = {
        "frames": frames,
        "audio": audio,
        "caption": caption,
        "latencies": latencies,
        "metadata": metadata,
        "total_ms": total_ms,
    }

    if log:
        print("Hero caption pipeline summary:")
        for stage in HERO_STAGE_ORDER:
            value = latencies.get(stage)
            if value is not None:
                print(_format_stage(stage, value))
        print(_format_stage("total", total_ms))
        print(f"  - caption: {caption}")
        print(f"  - transcript: {metadata['asr']['transcript']}")
        print(
            f"  - fusion score {fusion.score:.3f} (audio={fusion.audio_conf:.3f}, "
            f"vision={fusion.vision_conf:.3f})"
        )
        print(f"  - final state: {router.state.name}")

    return result


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="Suppress per-stage logging")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    run_hero_pipeline(log=not args.quiet)


if __name__ == "__main__":
    main()

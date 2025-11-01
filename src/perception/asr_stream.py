"""Streaming automatic-speech-recognition utilities."""
from __future__ import annotations

import os
from typing import Any, Iterator, Sequence

import numpy as np

from src.io.telemetry import log_metric

from src.perception.vad import frames_from_mic

__all__ = ["ASRStream", "MockASR", "WhisperASRStream"]


class MockASR:
    """Deterministic ASR stub used for unit testing.

    The mock converts incoming audio *frames* into synthetic lexical tokens. Each
    frame is decoded into tokens, which are appended to an internal buffer. The
    joined buffer is returned as the partial transcript, emulating the behaviour
    of streaming ASR engines that repeatedly surface the best-effort transcript
    so far. Because the mapping is purely deterministic, unit tests can reason
    about the expected partial outputs without relying on external ASR models.
    """

    def __init__(self, token_prefix: str = "tok") -> None:
        self.token_prefix = token_prefix
        self._tokens: list[str] = []

    def reset(self) -> None:
        """Clear any buffered tokens."""

        self._tokens.clear()

    def process(self, frame: bytes | np.ndarray | str | None) -> str:
        """Convert ``frame`` into a deterministic partial transcript."""

        tokens = self._frame_to_tokens(frame)
        if tokens:
            self._tokens.extend(tokens)
        return " ".join(self._tokens)

    # ------------------------------------------------------------------
    def _frame_to_tokens(self, frame: bytes | np.ndarray | str | None) -> list[str]:
        if frame is None:
            return []
        if isinstance(frame, bytes):
            text = frame.decode("utf-8", errors="ignore").strip()
            if not text:
                return []
            raw_tokens = text.split()
            return [f"{self.token_prefix}:{tok}" for tok in raw_tokens]
        if isinstance(frame, np.ndarray):
            flattened = frame.flatten().tolist()
            if not flattened:
                return []
            return [f"{self.token_prefix}:{int(value)}" for value in flattened]
        if isinstance(frame, str):
            text = frame.strip()
            if not text:
                return []
            raw_tokens = text.split()
            return [f"{self.token_prefix}:{tok}" for tok in raw_tokens]
        text = str(frame).strip()
        if not text:
            return []
        return [f"{self.token_prefix}:{tok}" for tok in text.split()]


class ASRStream:
    """Utility that exposes a streaming transcription interface.

    Parameters
    ----------
    asr_backend:
        Optional backend responsible for turning audio frames into partial
        transcripts. When omitted a :class:`MockASR` instance is used unless the
        ``USE_WHISPER_STREAMING`` environment flag is set, in which case the
        (not yet implemented) Whisper streaming backend is selected.
    stability_delta:
        Threshold :math:`\\delta` used by the stability gate.
    stability_consecutive:
        Number of consecutive stable partials (``K``) required to mark the
        transcript as final.
    frame_duration_ms:
        Synthetic timing information used for ``t_ms`` metadata. Because the
        mock backend does not operate on real audio timestamps, each processed
        frame advances the virtual clock by this amount.
    """

    def __init__(
        self,
        *,
        asr_backend: MockASR | None = None,
        stability_delta: float = 0.1,
        stability_consecutive: int = 2,
        frame_duration_ms: float = 20.0,
    ) -> None:
        self.stability_delta = float(stability_delta)
        self.stability_consecutive = max(1, int(stability_consecutive))
        self.frame_duration_ms = float(frame_duration_ms)
        self._backend = asr_backend or self._select_backend()

    # ------------------------------------------------------------------
    def _select_backend(self) -> MockASR:
        if os.getenv("USE_WHISPER_STREAMING") == "1":
            return self._build_whisper_backend()
        return MockASR()

    def _build_whisper_backend(self) -> MockASR:
        """Placeholder for the Whisper streaming implementation."""

        raise NotImplementedError("TODO: integrate Whisper streaming backend")

    # ------------------------------------------------------------------
    def run(self, audio_frames: Iterator[bytes | np.ndarray]) -> Iterator[dict]:
        """Yield streaming ASR hypotheses for ``audio_frames``."""

        backend = self._backend
        if hasattr(backend, "reset"):
            backend.reset()  # type: ignore[call-arg]

        prev_tokens: list[str] | None = None
        stability_counter = 0
        first_frame_index: int | None = None

        frame_index = -1
        for frame in audio_frames:
            frame_index += 1
            partial = backend.process(frame)
            if partial is None:
                continue
            partial = partial.strip()
            if not partial:
                continue
            curr_tokens = partial.split()
            if not curr_tokens:
                continue

            if first_frame_index is None:
                first_frame_index = frame_index

            if prev_tokens is not None:
                similarity = self._similarity(prev_tokens, curr_tokens)
                if 1.0 - similarity <= self.stability_delta:
                    stability_counter += 1
                else:
                    stability_counter = 0
            else:
                stability_counter = 0

            is_final = stability_counter >= self.stability_consecutive
            result = {
                "text": partial,
                "is_final": bool(is_final),
                "t_first_ms": (first_frame_index or 0) * self.frame_duration_ms,
                "t_ms": (frame_index + 1) * self.frame_duration_ms,
            }
            yield result

            if is_final:
                break

            prev_tokens = curr_tokens

    # ------------------------------------------------------------------
    def run_with_provider(self, provider: Any, *, seconds: float = 1.0) -> Iterator[dict]:
        """Stream microphone audio from ``provider`` through the stability gate."""

        mic = getattr(provider, "mic", None) or getattr(provider, "microphone", None)
        if mic is None:
            raise AttributeError("provider does not expose a 'mic' or 'microphone' attribute")

        provider_name = type(provider).__name__ if provider is not None else "unknown"
        log_metric("asr.provider", 1.0, tags={"provider": provider_name})

        frame_count = 0

        def counted_frames() -> Iterator[Sequence[float] | np.ndarray]:
            nonlocal frame_count
            for frame in frames_from_mic(mic, seconds=seconds):
                frame_count += 1
                yield frame

        try:
            for result in self.run(counted_frames()):
                yield result
        finally:
            log_metric("asr.frames_from_mic", frame_count, unit="count")

    # ------------------------------------------------------------------
    def _similarity(self, prev_tokens: Sequence[str], curr_tokens: Sequence[str]) -> float:
        if not prev_tokens or not curr_tokens:
            return 0.0
        lcs = self._lcs_length(prev_tokens, curr_tokens)
        return lcs / max(1, len(curr_tokens))

    @staticmethod
    def _lcs_length(a: Sequence[str], b: Sequence[str]) -> int:
        if not a or not b:
            return 0
        dp = [0] * (len(b) + 1)
        for token_a in a:
            prev_diag = 0
            for j, token_b in enumerate(b, start=1):
                temp = dp[j]
                if token_a == token_b:
                    dp[j] = prev_diag + 1
                else:
                    dp[j] = max(dp[j], dp[j - 1])
                prev_diag = temp
        return dp[-1]


class WhisperASRStream(ASRStream):
    """Placeholder Whisper streaming adapter.

    This stub intentionally raises to remind integrators that the real Whisper
    client needs to be wired in outside of the CI environment. Keeping the
    interface available allows downstream modules to import the factory without
    pulling in optional dependencies during tests.
    """

    def __init__(self, *args, **kwargs) -> None:  # noqa: D401 - intentionally simple
        raise NotImplementedError(
            "Wire your Whisper client here; disabled in CI"
        )

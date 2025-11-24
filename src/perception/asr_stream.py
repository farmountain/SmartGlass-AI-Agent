"""Streaming automatic-speech-recognition utilities."""
from __future__ import annotations

import logging
import os
from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Sequence

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

        mic = None
        if hasattr(provider, "open_audio_stream"):
            mic = provider.open_audio_stream()
        if mic is None:
            mic = getattr(provider, "mic", None) or getattr(provider, "microphone", None)
        if mic is None:
            raise AttributeError("provider does not expose a microphone-compatible interface")

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
    """Streaming Whisper adapter that tracks token stability over time."""

    sample_rate = 16_000

    @dataclass
    class _TrackedToken:
        word: str
        first_seen: float
        last_seen: float
        confirmed: bool = False

    def __init__(
        self,
        *,
        model_name: str = "base",
        language: str | None = None,
        device: str | None = None,
        stability_window: float = 1.5,
        window_duration: float = 5.0,
    ) -> None:
        try:
            import whisper  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - defensive import
            raise RuntimeError("WhisperASRStream requires the 'whisper' package") from exc

        self.logger = logging.getLogger(__name__)
        self.model = whisper.load_model(model_name, device=device)
        self.language = language
        self.stability_window = float(stability_window)
        self.window_duration = float(window_duration)
        self.device = device

        if self.stability_window <= 0:
            raise ValueError("stability_window must be positive")
        if self.window_duration <= 0:
            raise ValueError("window_duration must be positive")

        self._buffer: deque[float] = deque()
        self._tokens: list[WhisperASRStream._TrackedToken] = []
        self._current_time = 0.0
        self._last_final_len = 0

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._buffer.clear()
        self._tokens.clear()
        self._current_time = 0.0
        self._last_final_len = 0
        self.logger.debug("WhisperASRStream state reset")

    # ------------------------------------------------------------------
    def _to_mono(self, chunk: object) -> list[float]:
        if chunk is None:
            return []
        if isinstance(chunk, np.ndarray):
            return chunk.astype(np.float32).flatten().tolist()
        if isinstance(chunk, (bytes, bytearray)):
            return []
        if isinstance(chunk, str):
            return []
        try:
            return [float(sample) for sample in chunk]  # type: ignore[arg-type]
        except TypeError:
            return []

    def _append_buffer(self, samples: Iterable[float]) -> None:
        for sample in samples:
            self._buffer.append(float(sample))
            if len(self._buffer) > int(self.sample_rate * self.window_duration):
                self._buffer.popleft()

    def _transcribe_window(self) -> tuple[list[str], float]:
        if not self._buffer:
            return [], self._current_time
        window = np.array(list(self._buffer), dtype=np.float32)
        result = self.model.transcribe(
            window,
            word_timestamps=True,
            beam_size=5,
            language=self.language,
        )
        words: list[dict[str, object]] = []
        for segment in result.get("segments", []):
            words.extend(segment.get("words", []))
        tokens: list[str] = []
        end_ts = self._current_time
        for word_info in words:
            word = str(word_info.get("word", "")).strip()
            if not word:
                continue
            tokens.append(word)
            end_ts = float(word_info.get("end", end_ts))
        return tokens, end_ts

    def _update_stability(self, tokens: list[str], timestamp: float) -> tuple[list[str], bool]:
        for idx, word in enumerate(tokens):
            if idx < len(self._tokens) and self._tokens[idx].word == word:
                self._tokens[idx].last_seen = timestamp
            else:
                self._tokens = self._tokens[:idx]
                self._tokens.append(
                    WhisperASRStream._TrackedToken(
                        word=word, first_seen=timestamp, last_seen=timestamp
                    )
                )
        if len(tokens) < len(self._tokens):
            self._tokens = self._tokens[: len(tokens)]

        for token in self._tokens:
            if not token.confirmed and (timestamp - token.first_seen) >= self.stability_window:
                token.confirmed = True
        confirmed_text = [token.word for token in self._tokens if token.confirmed]
        is_new_final = len(confirmed_text) > self._last_final_len
        if is_new_final:
            self._last_final_len = len(confirmed_text)
        return confirmed_text, is_new_final

    # ------------------------------------------------------------------
    def run(self, audio_frames: Iterator[bytes | np.ndarray | Sequence[float]]) -> Iterator[dict]:
        self.reset()
        for frame in audio_frames:
            samples = self._to_mono(frame)
            if not samples:
                continue
            self._append_buffer(samples)
            self._current_time += len(samples) / self.sample_rate
            tokens, ts = self._transcribe_window()
            if not tokens:
                continue
            confirmed, has_new_final = self._update_stability(tokens, ts)
            partial_text = " ".join(tokens)
            event = {"text": partial_text, "timestamp": ts, "is_final": False}
            self.logger.debug("Partial transcript: %s", partial_text)
            yield event

            if confirmed and has_new_final:
                final_text = " ".join(confirmed)
                final_event = {"text": final_text, "timestamp": ts, "is_final": True}
                self.logger.debug("Finalised transcript: %s", final_text)
                yield final_event

        if self._tokens:
            final_text = " ".join(token.word for token in self._tokens)
            final_event = {
                "text": final_text,
                "timestamp": self._current_time,
                "is_final": True,
            }
            self.logger.debug("Flushing final transcript: %s", final_text)
            yield final_event

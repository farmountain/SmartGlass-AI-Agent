"""Streaming ASR utilities with stability-aware gating."""

from __future__ import annotations

import os
from collections import Counter, deque
from typing import Deque, Dict, Iterable, Iterator, List, MutableMapping, Optional, Sequence, Tuple

from src.io.telemetry import log_metric

TokenSequence = List[str]
Timestamp = Tuple[float, float]
ASRPartial = MutableMapping[str, object]


class ASRStream:
    """Post-process streaming ASR partials into stable transcripts.

    Parameters
    ----------
    asr:
        Object that exposes a ``stream`` method yielding partial hypotheses.
    stability_window:
        Number of partials (``K``) considered when determining stability.
    stability_delta:
        Maximum instability (``δ``) tolerated when finalising tokens. Values
        should lie in ``[0, 1]`` and represent the share of disagreeing
        partials that is tolerated.
    """

    ENV_TOGGLE = "SMARTGLASS_USE_WHISPER"

    def __init__(
        self,
        *,
        asr: Optional["StreamingASR"] = None,
        stability_window: int = 4,
        stability_delta: float = 0.25,
    ) -> None:
        if stability_window < 1:
            raise ValueError("stability_window must be >= 1")
        if not 0.0 <= stability_delta <= 1.0:
            raise ValueError("stability_delta must be within [0, 1]")

        self.stability_window = stability_window
        self.stability_delta = stability_delta
        self.asr = asr or self._default_asr()

    def _default_asr(self) -> "StreamingASR":
        use_whisper = os.getenv(self.ENV_TOGGLE, "").lower() in {"1", "true", "yes"}
        if use_whisper:
            raise RuntimeError(
                "Real Whisper integration is guarded by SMARTGLASS_USE_WHISPER. "
                "Set the variable to 0 (default) to use the deterministic mock."
            )
        return MockASR([])

    def run(self, audio_source: Optional[Iterable[bytes]] = None) -> Iterator[Dict[str, object]]:
        """Yield partial and final transcripts in sequence.

        Parameters
        ----------
        audio_source:
            Iterable audio source passed through to the underlying ASR engine.

        Yields
        ------
        dict
            Structured dictionaries describing partial and final transcripts.
        """

        history: Deque[TokenSequence] = deque(maxlen=self.stability_window)
        final_tokens: TokenSequence = []
        latest_timestamp: Timestamp = (0.0, 0.0)

        first_partial_ms: Optional[float] = None
        total_partials = 0
        rollback_chars = 0
        previous_partial_text = ""

        def _emit_event(
            *,
            text: str,
            timestamp: Timestamp,
            stability: float,
            is_final: bool,
        ) -> Dict[str, object]:
            nonlocal first_partial_ms
            event_time_ms = self._timestamp_to_ms(timestamp)
            if first_partial_ms is None:
                first_partial_ms = event_time_ms
            event = {
                "type": "final" if is_final else "partial",
                "text": text,
                "timestamp": timestamp,
                "stability": stability,
                "is_final": is_final,
                "t_ms": event_time_ms,
                "t_first_ms": first_partial_ms,
            }
            return event

        for partial in self.asr.stream(audio_source):
            text = str(partial.get("text", "")).strip()
            timestamp = self._coerce_timestamp(partial.get("timestamp"))
            tokens = self._tokenize(text)
            history.append(tokens)
            latest_timestamp = timestamp

            stable_len, stable_tokens = self._stable_prefix(history, final_tokens)
            stability = stable_len / max(1, len(tokens)) if tokens else 1.0

            total_partials += 1
            if len(text) < len(previous_partial_text):
                rollback_chars += len(previous_partial_text) - len(text)
            previous_partial_text = text

            yield _emit_event(
                text=text,
                timestamp=timestamp,
                stability=stability,
                is_final=False,
            )

            if stable_len > len(final_tokens):
                new_tokens = stable_tokens[len(final_tokens) : stable_len]
                if new_tokens:
                    final_tokens.extend(new_tokens)
                    yield _emit_event(
                        text=self._join_tokens(final_tokens),
                        timestamp=timestamp,
                        stability=stability,
                        is_final=True,
                    )

        if history:
            residual = history[-1]
            if len(residual) > len(final_tokens):
                final_tokens.extend(residual[len(final_tokens) :])
                yield _emit_event(
                    text=self._join_tokens(final_tokens),
                    timestamp=latest_timestamp,
                    stability=1.0,
                    is_final=True,
                )

        first_ms = first_partial_ms if first_partial_ms is not None else 0.0
        reversal_rate = rollback_chars / max(1, total_partials)
        log_metric("asr.first_partial_ms", first_ms, unit="ms")
        log_metric("asr.total_partials", total_partials, unit="count")
        log_metric("asr.reversal_rate", reversal_rate, unit="ratio")

    def _stable_prefix(
        self, history: Deque[TokenSequence], finalized: TokenSequence
    ) -> Tuple[int, TokenSequence]:
        stable_tokens = list(finalized)
        if len(history) < self.stability_window:
            return len(stable_tokens), stable_tokens

        prefix_len = min(len(seq) for seq in history)
        for idx in range(len(stable_tokens), prefix_len):
            column = [seq[idx] for seq in history]
            token, count = Counter(column).most_common(1)[0]
            agreement = count / len(history)
            if 1.0 - agreement <= self.stability_delta:
                stable_tokens.append(token)
            else:
                break
        return len(stable_tokens), stable_tokens

    @staticmethod
    def _tokenize(text: str) -> TokenSequence:
        return text.split()

    @staticmethod
    def _join_tokens(tokens: TokenSequence) -> str:
        return " ".join(tokens)

    @staticmethod
    def _coerce_timestamp(value: Optional[object]) -> Timestamp:
        if isinstance(value, (tuple, list)) and len(value) == 2:
            start, end = value
            return float(start), float(end)
        return (0.0, 0.0)

    @staticmethod
    def _timestamp_to_ms(timestamp: Timestamp) -> float:
        start, end = timestamp
        base = end if end > 0.0 else start
        return float(base) * 1000.0


class StreamingASR:
    """Protocol-like base class for streaming ASR engines."""

    def stream(self, audio_source: Optional[Iterable[bytes]]) -> Iterator[ASRPartial]:
        raise NotImplementedError


class MockASR(StreamingASR):
    """Deterministic ASR mock that replays scripted partials."""

    def __init__(self, partials: Sequence[Dict[str, object]]) -> None:
        self._partials = [
            {
                "text": str(item.get("text", "")),
                "timestamp": ASRStream._coerce_timestamp(item.get("timestamp")),
            }
            for item in partials
        ]

    def stream(self, audio_source: Optional[Iterable[bytes]] = None) -> Iterator[ASRPartial]:
        for partial in self._partials:
            yield dict(partial)

    @classmethod
    def from_transcript(
        cls, transcript: str, *, splits: Sequence[int], base_timestamp: Tuple[float, float] = (0.0, 0.0)
    ) -> "MockASR":
        tokens = transcript.split()
        partials: List[Dict[str, object]] = []
        for length in splits:
            length = max(0, min(len(tokens), length))
            text = " ".join(tokens[:length])
            partials.append({"text": text, "timestamp": base_timestamp})
        return cls(partials)


__all__ = ["ASRStream", "MockASR", "StreamingASR"]

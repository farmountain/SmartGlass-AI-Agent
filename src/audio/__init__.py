"""Audio utilities for SmartGlass."""

from __future__ import annotations

import os
from typing import Any

from .asr_stream import ASRStream, MockASR, StreamingASR
from .vad import AudioFrame, EnergyVAD


def _is_env_enabled(name: str) -> bool:
    """Return ``True`` when the named environment variable is truthy."""

    value = os.getenv(name, "")
    return value.lower() in {"1", "true", "yes", "on"}


class WhisperASRStream:
    """Placeholder for the Whisper streaming ASR integration."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - stub
        self.args = args
        self.kwargs = kwargs

    def run(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - stub
        raise NotImplementedError(
            "Whisper streaming support is not yet integrated. "
            "Unset USE_WHISPER_STREAMING to fall back to the mock ASR."
        )


def get_default_vad(**kwargs: Any) -> EnergyVAD:
    """Return the default voice activity detector implementation."""

    return EnergyVAD(**kwargs)


def get_default_asr(
    *, stability_window: int = 4, stability_delta: float = 0.25
) -> ASRStream | WhisperASRStream:
    """Return the default streaming ASR implementation for the agent."""

    if _is_env_enabled("USE_WHISPER_STREAMING"):
        return WhisperASRStream(
            stability_window=stability_window, stability_delta=stability_delta
        )

    mock_asr = MockASR([])
    return ASRStream(
        asr=mock_asr,
        stability_window=stability_window,
        stability_delta=stability_delta,
    )


__all__ = [
    "ASRStream",
    "MockASR",
    "StreamingASR",
    "AudioFrame",
    "EnergyVAD",
    "WhisperASRStream",
    "get_default_asr",
    "get_default_vad",
]

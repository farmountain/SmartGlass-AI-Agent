"""Session management for the edge runtime server."""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np
from PIL import Image

from src.smartglass_agent import SmartGlassAgent
from src.utils.metrics import metrics, record_latency

from .config import EdgeRuntimeConfig


class BufferLimitExceeded(Exception):
    """Raised when an ingest payload exceeds configured buffer limits."""


@dataclass
class SessionState:
    """Container for per-session runtime state."""

    agent: SmartGlassAgent
    transcripts: List[str] = field(default_factory=list)
    audio_buffers: List[np.ndarray] = field(default_factory=list)
    audio_durations: List[Optional[float]] = field(default_factory=list)
    last_frame: Optional[Image.Image] = None
    frame_history: List[Image.Image] = field(default_factory=list)
    query_history: List[Dict[str, Any]] = field(default_factory=list)


class SessionManager:
    """Creates and tracks stateful :class:`SmartGlassAgent` sessions."""

    def __init__(self, config: EdgeRuntimeConfig):
        self.config = config
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.Lock()

    def create_session(self) -> str:
        """Create a new SmartGlassAgent-backed session."""

        with self._lock:
            session_id = str(uuid4())
            agent = SmartGlassAgent(
                whisper_model=self.config.whisper_model,
                clip_model=self.config.vision_model,
            )
            self._sessions[session_id] = SessionState(agent=agent)
            metrics.increment_sessions()
            return session_id

    def _get_state(self, session_id: str) -> SessionState:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown session id: {session_id}") from exc

    def display_available(self) -> bool:
        """Infer whether the underlying provider exposes a display."""

        with self._lock:
            agents = [state.agent for state in self._sessions.values()]

        for agent in agents:
            if self._agent_has_display(agent):
                return True

        provider_hint = (self.config.provider or "").lower()
        return any(hint in provider_hint for hint in ("display", "glass", "hud"))

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Unknown session id: {session_id}")
            del self._sessions[session_id]
            metrics.decrement_sessions()

    def ingest_audio(
        self,
        session_id: str,
        audio_array: np.ndarray,
        language: Optional[str] = None,
        sample_rate: Optional[int] = None,
    ) -> str:
        """Transcribe and retain audio input for a session."""

        duration_seconds = self._calculate_audio_duration(audio_array, sample_rate)
        with record_latency("VAD"):
            self._validate_audio_limits(audio_array, duration_seconds)

        state = self._get_state(session_id)
        self._ensure_audio_capacity(state, audio_array, duration_seconds)

        transcript = state.agent.process_audio_command(audio_array, language=language)
        state.transcripts.append(transcript)
        state.audio_buffers.append(audio_array)
        state.audio_durations.append(duration_seconds)
        self._finalize_audio_buffers(state)
        return transcript

    def ingest_frame(self, session_id: str, frame: Image.Image) -> None:
        """Store the latest video frame for the session."""

        state = self._get_state(session_id)
        self._validate_frame_limits(frame)
        self._ensure_frame_capacity(state, frame)
        state.frame_history.append(frame)
        state.last_frame = frame
        self._trim_frame_history(state)

    def run_query(
        self,
        session_id: str,
        *,
        text_query: Optional[str] = None,
        audio_input: Optional[np.ndarray] = None,
        audio_sample_rate: Optional[int] = None,
        image_input: Optional[Image.Image] = None,
        language: Optional[str] = None,
        cloud_offload: bool = False,
    ) -> Dict[str, Any]:
        """Execute a multimodal query through the session's agent."""
        metrics.increment_queries()
        state = self._get_state(session_id)

        with record_latency("Skill"):
            if isinstance(audio_input, np.ndarray):
                duration_seconds = self._calculate_audio_duration(audio_input, audio_sample_rate)
                self._validate_audio_limits(audio_input, duration_seconds)

            image = image_input if image_input is not None else state.last_frame
            if image is not None:
                self._validate_frame_limits(image)

            result = state.agent.process_multimodal_query(
                audio_input=audio_input,
                image_input=image,
                text_query=text_query,
                language=language,
                cloud_offload=cloud_offload,
            )
        state.query_history.append(result)
        if "query" in result:
            state.transcripts.append(result["query"])
        return result

    def get_summary(self, session_id: str) -> Dict[str, Any]:
        """Return lightweight session diagnostics."""

        state = self._get_state(session_id)
        return {
            "transcript_count": len(state.transcripts),
            "has_frame": state.last_frame is not None,
            "query_count": len(state.query_history),
        }

    @staticmethod
    def _calculate_audio_duration(
        audio_array: np.ndarray, sample_rate: Optional[int]
    ) -> Optional[float]:
        if sample_rate is None:
            return None
        return float(len(audio_array) / sample_rate)

    @staticmethod
    def _agent_has_display(agent: Any) -> bool:
        has_display = getattr(agent, "has_display", None)
        try:
            if isinstance(has_display, bool):
                return has_display
            if callable(has_display) and has_display():
                return True
        except Exception:  # pylint: disable=broad-except
            return False

        for attr in ("display", "overlay"):
            if getattr(agent, attr, None) is not None:
                return True
        return False

    def _validate_audio_limits(
        self, audio_array: np.ndarray, duration_seconds: Optional[float]
    ) -> None:
        if (
            self.config.audio_buffer_max_bytes is not None
            and audio_array.nbytes > self.config.audio_buffer_max_bytes
        ):
            raise BufferLimitExceeded(
                "Audio payload exceeds configured maximum buffer size"
            )

        if (
            self.config.audio_buffer_max_seconds is not None
            and duration_seconds is None
        ):
            raise BufferLimitExceeded(
                "Audio payload duration unknown; cannot enforce maximum buffer duration"
            )

        if (
            self.config.audio_buffer_max_seconds is not None
            and duration_seconds is not None
            and duration_seconds > self.config.audio_buffer_max_seconds
        ):
            raise BufferLimitExceeded(
                "Audio payload exceeds configured maximum buffer duration"
            )

    def _trim_audio_buffers(self, state: SessionState) -> None:
        max_bytes = self.config.audio_buffer_max_bytes
        max_seconds = self.config.audio_buffer_max_seconds

        if max_bytes is None and max_seconds is None:
            return

        def total_bytes() -> int:
            return sum(buffer.nbytes for buffer in state.audio_buffers)

        def total_duration() -> float:
            return sum(duration or 0.0 for duration in state.audio_durations)

        while state.audio_buffers:
            over_bytes = max_bytes is not None and total_bytes() > max_bytes
            over_time = max_seconds is not None and total_duration() > max_seconds
            if not over_bytes and not over_time:
                break
            state.audio_buffers.pop(0)
            state.audio_durations.pop(0)

    def _finalize_audio_buffers(self, state: SessionState) -> None:
        if self.config.audio_buffer_policy == "trim":
            self._trim_audio_buffers(state)

    def _ensure_audio_capacity(
        self,
        state: SessionState,
        pending_buffer: np.ndarray,
        pending_duration: Optional[float],
    ) -> None:
        max_bytes = self.config.audio_buffer_max_bytes
        max_seconds = self.config.audio_buffer_max_seconds

        if max_bytes is None and max_seconds is None:
            return

        policy = self.config.audio_buffer_policy

        def total_bytes() -> int:
            return sum(buffer.nbytes for buffer in state.audio_buffers) + pending_buffer.nbytes

        def total_duration() -> float:
            return sum(duration or 0.0 for duration in state.audio_durations) + (
                pending_duration or 0.0
            )

        if policy == "trim":
            while state.audio_buffers:
                over_bytes = max_bytes is not None and total_bytes() > max_bytes
                over_time = max_seconds is not None and total_duration() > max_seconds
                if not over_bytes and not over_time:
                    break
                state.audio_buffers.pop(0)
                state.audio_durations.pop(0)
        elif policy == "reject":
            over_bytes = max_bytes is not None and total_bytes() > max_bytes
            over_time = max_seconds is not None and total_duration() > max_seconds
            if over_bytes or over_time:
                raise BufferLimitExceeded(
                    "Audio buffer would exceed configured limits; adjust AUDIO_BUFFER_* settings or set AUDIO_BUFFER_POLICY=trim"
                )
        else:
            raise ValueError(f"Unsupported audio buffer policy: {policy}")

    def _validate_frame_limits(self, frame: Image.Image) -> None:
        if self.config.frame_buffer_max_bytes is None:
            return

        if self._estimate_frame_bytes(frame) > self.config.frame_buffer_max_bytes:
            raise BufferLimitExceeded(
                "Frame payload exceeds configured maximum buffer size"
            )

    def _trim_frame_history(self, state: SessionState) -> None:
        max_frames = max(1, self.config.frame_history_size)
        max_bytes = self.config.frame_buffer_max_bytes

        def total_frame_bytes() -> int:
            return sum(self._estimate_frame_bytes(frame) for frame in state.frame_history)

        while state.frame_history:
            over_count = len(state.frame_history) > max_frames
            over_bytes = max_bytes is not None and total_frame_bytes() > max_bytes
            if not over_count and not over_bytes:
                break
            state.frame_history.pop(0)
            state.last_frame = state.frame_history[-1] if state.frame_history else None

    def _ensure_frame_capacity(self, state: SessionState, frame: Image.Image) -> None:
        max_bytes = self.config.frame_buffer_max_bytes
        max_frames = max(1, self.config.frame_history_size)
        policy = self.config.frame_buffer_policy

        if policy == "trim":
            return

        frame_bytes = self._estimate_frame_bytes(frame)
        total_bytes = sum(self._estimate_frame_bytes(existing) for existing in state.frame_history)
        over_count = len(state.frame_history) + 1 > max_frames
        over_bytes = max_bytes is not None and (total_bytes + frame_bytes) > max_bytes

        if policy == "reject":
            if over_count or over_bytes:
                raise BufferLimitExceeded(
                    "Frame buffer would exceed configured limits; reduce frame frequency or set FRAME_BUFFER_POLICY=trim"
                )
            return

        raise ValueError(f"Unsupported frame buffer policy: {policy}")

    @staticmethod
    def _estimate_frame_bytes(frame: Image.Image) -> int:
        width, height = frame.size
        channels = len(frame.getbands())
        return width * height * channels

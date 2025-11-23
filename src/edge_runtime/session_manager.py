"""Session management for the edge runtime server."""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np
from PIL import Image

from src.smartglass_agent import SmartGlassAgent

from .config import EdgeRuntimeConfig


@dataclass
class SessionState:
    """Container for per-session runtime state."""

    agent: SmartGlassAgent
    transcripts: List[str] = field(default_factory=list)
    audio_buffers: List[np.ndarray] = field(default_factory=list)
    last_frame: Optional[Image.Image] = None
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
            return session_id

    def _get_state(self, session_id: str) -> SessionState:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown session id: {session_id}") from exc

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Unknown session id: {session_id}")
            del self._sessions[session_id]

    def ingest_audio(
        self, session_id: str, audio_array: np.ndarray, language: Optional[str] = None
    ) -> str:
        """Transcribe and retain audio input for a session."""

        state = self._get_state(session_id)
        transcript = state.agent.process_audio_command(audio_array, language=language)
        state.transcripts.append(transcript)
        state.audio_buffers.append(audio_array)
        return transcript

    def ingest_frame(self, session_id: str, frame: Image.Image) -> None:
        """Store the latest video frame for the session."""

        state = self._get_state(session_id)
        state.last_frame = frame

    def run_query(
        self,
        session_id: str,
        *,
        text_query: Optional[str] = None,
        audio_input: Optional[np.ndarray] = None,
        image_input: Optional[Image.Image] = None,
        language: Optional[str] = None,
        cloud_offload: bool = False,
    ) -> Dict[str, Any]:
        """Execute a multimodal query through the session's agent."""

        state = self._get_state(session_id)
        image = image_input if image_input is not None else state.last_frame
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

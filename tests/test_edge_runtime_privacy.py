"""Privacy controls for the edge runtime buffers."""

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image

np = pytest.importorskip("numpy")

from src.edge_runtime.config import EdgeRuntimeConfig
from src.edge_runtime.session_manager import SessionManager


class _StubSmartGlassAgent:
    def __init__(self, whisper_model: str, clip_model: str):
        self.whisper_model = whisper_model
        self.clip_model = clip_model

    def process_audio_command(self, audio_array: np.ndarray, language: str | None = None) -> str:
        return "stub-transcript"

    def process_multimodal_query(
        self,
        *,
        audio_input: np.ndarray | None = None,
        image_input: Image.Image | None = None,
        text_query: str | None = None,
        language: str | None = None,
        cloud_offload: bool = False,
    ) -> dict:
        return {"query": text_query or "stub-query", "response": "ok"}


def _make_config(**overrides) -> EdgeRuntimeConfig:
    defaults = dict(
        provider="local",
        whisper_model="base",
        vision_model="clip",
        llm_backend_type="ann",
        ports={"http": 8000},
    )
    defaults.update(overrides)
    return EdgeRuntimeConfig(**defaults)


def test_privacy_flags_disable_storage(monkeypatch):
    monkeypatch.setattr("src.edge_runtime.session_manager.SmartGlassAgent", _StubSmartGlassAgent)
    config = _make_config(
        store_raw_audio=False, store_raw_frames=False, store_transcripts=False
    )
    manager = SessionManager(config)
    session_id = manager.create_session()

    audio_array = np.zeros(160, dtype=np.float32)
    transcript = manager.ingest_audio(session_id, audio_array, sample_rate=16000)
    state = manager._get_state(session_id)

    assert transcript == "stub-transcript"
    assert state.transcripts == []
    assert state.audio_buffers == []
    assert state.audio_durations == []

    frame = Image.new("RGB", (2, 2))
    manager.ingest_frame(session_id, frame)
    assert state.frame_history == []
    assert state.last_frame is None

    manager.run_query(session_id, text_query="hello")
    assert state.transcripts == []


def test_privacy_flags_allow_storage(monkeypatch):
    monkeypatch.setattr("src.edge_runtime.session_manager.SmartGlassAgent", _StubSmartGlassAgent)
    config = _make_config(
        store_raw_audio=True, store_raw_frames=True, store_transcripts=True
    )
    manager = SessionManager(config)
    session_id = manager.create_session()

    audio_array = np.zeros(160, dtype=np.float32)
    transcript = manager.ingest_audio(session_id, audio_array, sample_rate=16000)
    state = manager._get_state(session_id)

    assert transcript == "stub-transcript"
    assert state.transcripts == ["stub-transcript"]
    assert state.audio_buffers and state.audio_buffers[0] is audio_array
    assert state.audio_durations == [len(audio_array) / 16000]

    frame = Image.new("RGB", (2, 2))
    manager.ingest_frame(session_id, frame)
    assert state.frame_history == [frame]
    assert state.last_frame is frame

    manager.run_query(session_id, text_query="hello")
    assert state.transcripts[-1] == "hello"

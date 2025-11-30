"""Privacy flag helpers and storage behavior tests."""

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image

np = pytest.importorskip("numpy")

from src.edge_runtime.config import load_config_from_env
from src.edge_runtime.session_manager import SessionManager
from src.privacy_flags import should_store_audio, should_store_frames, should_store_transcripts


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


def _clear_privacy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("STORE_RAW_AUDIO", "STORE_RAW_FRAMES", "STORE_TRANSCRIPTS"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _stub_agent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.edge_runtime.session_manager.SmartGlassAgent", _StubSmartGlassAgent)


@pytest.mark.parametrize(
    "env_values, expected",
    [
        ({}, (False, False, False)),
        (
            {"STORE_RAW_AUDIO": "1", "STORE_RAW_FRAMES": "true", "STORE_TRANSCRIPTS": "yes"},
            (True, True, True),
        ),
    ],
)
def test_privacy_flags_opt_in_default(monkeypatch: pytest.MonkeyPatch, env_values, expected):
    _clear_privacy_env(monkeypatch)
    for key, value in env_values.items():
        monkeypatch.setenv(key, value)

    assert should_store_audio() is expected[0]
    assert should_store_frames() is expected[1]
    assert should_store_transcripts() is expected[2]


def test_privacy_flags_control_runtime_storage(monkeypatch: pytest.MonkeyPatch):
    _clear_privacy_env(monkeypatch)
    config = load_config_from_env()
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
    assert state.query_history == []


def test_privacy_flags_enable_storage(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STORE_RAW_AUDIO", "1")
    monkeypatch.setenv("STORE_RAW_FRAMES", "1")
    monkeypatch.setenv("STORE_TRANSCRIPTS", "1")

    config = load_config_from_env()
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

    query_result = manager.run_query(session_id, text_query="hello")
    assert query_result["query"] == "hello"
    assert state.transcripts[-1] == "hello"
    assert state.query_history and state.query_history[-1] == query_result

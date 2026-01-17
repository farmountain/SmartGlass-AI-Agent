"""Integration-style tests for the edge runtime FastAPI server."""

import base64
import io
import sys
import types
from importlib import import_module, reload
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from PIL import Image


class FakeSmartGlassAgent:
    """Lightweight stand-in that avoids loading heavy models."""

    def __init__(self, whisper_model: str, clip_model: str):
        self.whisper_model = whisper_model
        self.clip_model = clip_model
        self.audio_commands = []
        self.multimodal_queries = []

    def process_audio_command(self, audio_array: np.ndarray, language: str | None = None) -> str:
        from src.utils.metrics import record_latency

        with record_latency("ASR"):
            self.audio_commands.append((audio_array, language))
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
        from src.utils.metrics import record_latency

        self.multimodal_queries.append(
            {
                "audio_input": audio_input,
                "image_input": image_input,
                "text_query": text_query,
                "language": language,
                "cloud_offload": cloud_offload,
            }
        )
        with record_latency("LLM"):
            return {
                "transcript": text_query or "stub-query",
                "response": "stub-response",
                "overlays": [{"type": "text", "content": "overlay"}],
            }

    def has_display(self) -> bool:
        return True


def _encode_silent_wav(duration_seconds: float = 0.1, sample_rate: int = 16000) -> str:
    samples = int(duration_seconds * sample_rate)
    audio_array = np.zeros(samples, dtype=np.float32)
    buffer = io.BytesIO()
    sf.write(buffer, audio_array, sample_rate, format="WAV")
    return base64.b64encode(buffer.getvalue()).decode()


def _make_silent_wav_bytes(duration_seconds: float = 0.1, sample_rate: int = 16000) -> bytes:
    """Convenience helper for creating raw WAV payloads for WebSocket tests."""

    return base64.b64decode(_encode_silent_wav(duration_seconds, sample_rate))


def _encode_test_image(size: int = 8, color: tuple[int, int, int] = (255, 0, 0)) -> str:
    image = Image.new("RGB", (size, size), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def _make_test_image_bytes(size: int = 8, color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    return base64.b64decode(_encode_test_image(size, color=color))


@pytest.fixture(name="edge_app")
def fixture_edge_app(monkeypatch, request):
    # Patch the SmartGlassAgent used by the session manager before importing the server.
    src_root = Path(__file__).resolve().parent.parent / "src"
    src_package = types.ModuleType("src")
    src_package.__path__ = [str(src_root)]
    monkeypatch.setitem(sys.modules, "src", src_package)

    stubs: dict[str, types.ModuleType] = {}
    for module_name, attributes in {
        "src.smartglass_agent": {"SmartGlassAgent": FakeSmartGlassAgent},
        "src.whisper_processor": {"WhisperAudioProcessor": object},
        "src.clip_vision": {"CLIPVisionProcessor": object},
        "src.gpt2_generator": {"GPT2TextGenerator": object},
        "src.llm_backend": {"AnnLLMBackend": object, "LLMBackend": object},
        "src.llm_snn_backend": {"SNNLLMBackend": object},
        "src.audio": {"get_default_asr": lambda: None, "get_default_vad": lambda: None},
        "src.fusion": {"ConfidenceFusion": object},
        "src.perception": {
            "get_default_keyframer": lambda: None,
            "get_default_ocr": lambda: None,
            "get_default_vq": lambda: None,
        },
        "src.policy": {"get_default_policy": lambda: None},
    }.items():
        stub = types.ModuleType(module_name)
        for attr, value in attributes.items():
            setattr(stub, attr, value)
        stubs[module_name] = stub
        monkeypatch.setitem(sys.modules, module_name, stub)

    auth_config = getattr(request, "param", None)
    token: str | None
    header_name: str | None
    extra_env: dict[str, str]
    override_dependency = False

    if isinstance(auth_config, dict):
        token = auth_config.get("token")
        header_name = auth_config.get("header")
        extra_env = auth_config.get("env", {})
        override_dependency = auth_config.get("override_dependency", False)
    else:
        token = auth_config
        header_name = None
        extra_env = {}

    if token is None:
        for env_var in ["EDGE_RUNTIME_API_KEY", "EDGE_RUNTIME_AUTH_TOKEN", "EDGE_RUNTIME_AUTH_HEADER"]:
            monkeypatch.delenv(env_var, raising=False)
    else:
        monkeypatch.setenv("EDGE_RUNTIME_API_KEY", token)
        monkeypatch.setenv("EDGE_RUNTIME_AUTH_TOKEN", token)
        if header_name:
            monkeypatch.setenv("EDGE_RUNTIME_AUTH_HEADER", header_name)

    for key, value in extra_env.items():
        monkeypatch.setenv(key, value)

    session_manager_module = import_module("src.edge_runtime.session_manager")
    monkeypatch.setattr(session_manager_module, "SmartGlassAgent", FakeSmartGlassAgent)

    server_module = import_module("src.edge_runtime.server")
    reload(server_module)
    metrics_module = import_module("src.utils.metrics")
    metrics_module.metrics.reset()
    app = server_module.app

    if override_dependency:
        def _override_verify(request=None) -> None:  # type: ignore[annotation-unchecked]
            return server_module._verify_auth_token(request) if request is not None else None

        app.dependency_overrides[server_module._verify_api_key_header] = _override_verify
    return app


def test_edge_runtime_server_lifecycle(edge_app):
    client = TestClient(edge_app)

    create_response = client.post("/sessions")
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    audio_payload = {"audio_base64": _encode_silent_wav(), "language": "en"}
    audio_response = client.post(f"/sessions/{session_id}/audio", json=audio_payload)
    assert audio_response.status_code == 200
    assert audio_response.json()["transcript"] == "stub-transcript"

    frame_payload = {"image_base64": _encode_test_image()}
    frame_response = client.post(f"/sessions/{session_id}/frame", json=frame_payload)
    assert frame_response.status_code == 200
    assert frame_response.json()["status"] == "frame stored"

    query_payload = {"text_query": "What do you see?"}
    query_response = client.post(f"/sessions/{session_id}/query", json=query_payload)
    assert query_response.status_code == 200
    result = query_response.json()
    assert result["transcript"] == "What do you see?"
    assert result["response"] == "stub-response"
    assert isinstance(result["overlays"], list)

    delete_response = client.delete(f"/sessions/{session_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"


def test_list_sessions_endpoint(edge_app):
    client = TestClient(edge_app)
    
    # Initially, no sessions should exist
    list_response = client.get("/sessions")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0
    assert list_response.json()["sessions"] == []
    
    # Create first session
    session1_id = client.post("/sessions").json()["session_id"]
    
    # List should show one session
    list_response = client.get("/sessions")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    sessions = list_response.json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == session1_id
    assert sessions[0]["transcript_count"] == 0
    assert sessions[0]["has_frame"] is False
    assert sessions[0]["query_count"] == 0
    
    # Create second session with some activity
    session2_id = client.post("/sessions").json()["session_id"]
    audio_payload = {"audio_base64": _encode_silent_wav(), "language": "en"}
    client.post(f"/sessions/{session2_id}/audio", json=audio_payload)
    frame_payload = {"image_base64": _encode_test_image()}
    client.post(f"/sessions/{session2_id}/frame", json=frame_payload)
    client.post(f"/sessions/{session2_id}/query", json={"text_query": "test"})
    
    # List should show two sessions with different states
    list_response = client.get("/sessions")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 2
    sessions = list_response.json()["sessions"]
    assert len(sessions) == 2
    
    # Find session2 in the list and verify its state
    session2_data = next(s for s in sessions if s["session_id"] == session2_id)
    assert session2_data["transcript_count"] > 0
    assert session2_data["has_frame"] is True
    assert session2_data["query_count"] > 0
    
    # Delete first session
    client.delete(f"/sessions/{session1_id}")
    
    # List should show only one session now
    list_response = client.get("/sessions")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["sessions"][0]["session_id"] == session2_id
    
    # Delete second session
    client.delete(f"/sessions/{session2_id}")
    
    # List should be empty again
    list_response = client.get("/sessions")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0


def test_metrics_endpoint_reports_activity(edge_app):
    client = TestClient(edge_app)

    session_id = client.post("/sessions").json()["session_id"]
    audio_payload = {"audio_base64": _encode_silent_wav(), "language": "en"}
    client.post(f"/sessions/{session_id}/audio", json=audio_payload)
    client.post(f"/sessions/{session_id}/query", json={"text_query": "ping"})

    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["sessions"]["created"] >= 1
    assert payload["queries"]["total"] >= 1
    assert payload["latencies"]["ASR"]["count"] >= 1
    assert payload["latencies"]["LLM"]["count"] >= 1
    assert payload["display_available"] is True


@pytest.mark.parametrize("edge_app", ["secret-key"], indirect=True)
def test_edge_runtime_server_requires_api_key(edge_app):
    client = TestClient(edge_app)

    missing_header_response = client.post("/sessions")
    assert missing_header_response.status_code == 401

    wrong_header_response = client.post("/sessions", headers={"X-API-Key": "wrong"})
    assert wrong_header_response.status_code == 401

    headers = {"X-API-Key": "secret-key"}
    create_response = client.post("/sessions", headers=headers)
    assert create_response.status_code == 200

    session_id = create_response.json()["session_id"]
    delete_response = client.delete(f"/sessions/{session_id}", headers=headers)
    assert delete_response.status_code == 200


@pytest.mark.parametrize(
    "edge_app",
    [
        {
            "token": "bearer-token",
            "header": "Authorization",
        }
    ],
    indirect=True,
)
def test_edge_runtime_server_supports_custom_auth_header(edge_app):
    client = TestClient(edge_app)

    missing_header_response = client.post("/sessions")
    assert missing_header_response.status_code == 401

    wrong_header_response = client.post(
        "/sessions", headers={"Authorization": "Bearer wrong-token"}
    )
    assert wrong_header_response.status_code == 401

    headers = {"Authorization": "Bearer bearer-token"}
    create_response = client.post("/sessions", headers=headers)
    assert create_response.status_code == 200

    session_id = create_response.json()["session_id"]
    delete_response = client.delete(f"/sessions/{session_id}", headers=headers)
    assert delete_response.status_code == 200


@pytest.mark.parametrize(
    "edge_app",
    [
        {
            "env": {
                "AUDIO_BUFFER_MAX_SECONDS": "0.05",
                "AUDIO_BUFFER_POLICY": "reject",
            }
        }
    ],
    indirect=True,
)
def test_audio_ingest_rejects_when_limits_exceeded(edge_app):
    client = TestClient(edge_app)

    session_id = client.post("/sessions").json()["session_id"]
    audio_payload = {"audio_base64": _encode_silent_wav(duration_seconds=0.1)}
    response = client.post(f"/sessions/{session_id}/audio", json=audio_payload)

    assert response.status_code == 413
    assert "Audio payload exceeds configured maximum buffer duration" in response.json()["detail"]


@pytest.mark.parametrize(
    "edge_app",
    [
        {
            "env": {
                "AUDIO_BUFFER_MAX_SECONDS": "0.15",
                "AUDIO_BUFFER_POLICY": "trim",
            }
        }
    ],
    indirect=True,
)
def test_audio_ingest_trims_when_limits_exceeded(edge_app):
    client = TestClient(edge_app)

    session_id = client.post("/sessions").json()["session_id"]
    audio_payload = {"audio_base64": _encode_silent_wav(duration_seconds=0.1)}

    first = client.post(f"/sessions/{session_id}/audio", json=audio_payload)
    second = client.post(f"/sessions/{session_id}/audio", json=audio_payload)

    assert first.status_code == 200
    assert second.status_code == 200


@pytest.mark.parametrize(
    "edge_app",
    [
        {
            "env": {
                "FRAME_BUFFER_POLICY": "reject",
                "FRAME_BUFFER_MAX_BYTES": "300",
                "FRAME_HISTORY_SIZE": "2",
            }
        }
    ],
    indirect=True,
)
def test_frame_ingest_rejects_when_limits_exceeded(edge_app):
    client = TestClient(edge_app)

    session_id = client.post("/sessions").json()["session_id"]
    frame_payload = {"image_base64": _encode_test_image(size=8)}

    first = client.post(f"/sessions/{session_id}/frame", json=frame_payload)
    second = client.post(f"/sessions/{session_id}/frame", json=frame_payload)

    assert first.status_code == 200
    assert second.status_code == 413
    assert "Frame buffer would exceed configured limits" in second.json()["detail"]


def test_http_routes_reject_unknown_session_ids(edge_app):
    client = TestClient(edge_app)

    invalid_session = "does-not-exist"
    audio_payload = {"audio_base64": _encode_silent_wav()}
    frame_payload = {"image_base64": _encode_test_image()}
    query_payload = {"text_query": "hello"}

    audio_response = client.post(f"/sessions/{invalid_session}/audio", json=audio_payload)
    frame_response = client.post(f"/sessions/{invalid_session}/frame", json=frame_payload)
    query_response = client.post(f"/sessions/{invalid_session}/query", json=query_payload)
    delete_response = client.delete(f"/sessions/{invalid_session}")

    for response in (audio_response, frame_response, query_response, delete_response):
        assert response.status_code == 404
        assert "Unknown session id" in response.json()["detail"]


@pytest.mark.parametrize(
    "edge_app",
    [
        {
            "override_dependency": True,
        }
    ],
    indirect=True,
)
def test_websocket_routes_reject_unknown_session_ids(edge_app):
    client = TestClient(edge_app)
    missing_session = "missing"

    with pytest.raises(WebSocketDisconnect) as audio_exc:
        with client.websocket_connect(f"/ws/audio/{missing_session}") as websocket:
            websocket.receive_json()

    assert audio_exc.value.code == 4404

    with pytest.raises(WebSocketDisconnect) as frame_exc:
        with client.websocket_connect(f"/ws/frame/{missing_session}") as websocket:
            websocket.receive_json()

    assert frame_exc.value.code == 4404


@pytest.mark.parametrize(
    "edge_app",
    [
        {"token": "secret-key", "override_dependency": True},
    ],
    indirect=True,
)
def test_websocket_authentication_required(edge_app):
    client = TestClient(edge_app)
    session_id = client.post("/sessions", headers={"X-API-Key": "secret-key"}).json()["session_id"]

    with pytest.raises(WebSocketDisconnect) as audio_exc:
        with client.websocket_connect(f"/ws/audio/{session_id}") as websocket:
            websocket.receive_json()

    assert audio_exc.value.code == 4401

    with pytest.raises(WebSocketDisconnect) as frame_exc:
        with client.websocket_connect(f"/ws/frame/{session_id}") as websocket:
            websocket.receive_json()

    assert frame_exc.value.code == 4401


@pytest.mark.parametrize(
    "edge_app",
    [
        {
            "token": "secret-token",
            "env": {"AUDIO_BUFFER_MAX_SECONDS": "0.01", "AUDIO_BUFFER_POLICY": "reject"},
            "override_dependency": True,
        }
    ],
    indirect=True,
)
def test_websocket_audio_streaming_and_limits(edge_app):
    client = TestClient(edge_app)
    headers = {"X-API-Key": "secret-token"}
    session_id = client.post("/sessions", headers=headers).json()["session_id"]

    with client.websocket_connect(f"/ws/audio/{session_id}", headers=headers) as websocket:
        websocket: WebSocketTestSession

        websocket.send_bytes(_make_silent_wav_bytes(duration_seconds=0.005))
        first = websocket.receive_json()
        assert first["session_id"] == session_id
        assert first["transcript"] == "stub-transcript"

        websocket.send_bytes(_make_silent_wav_bytes(duration_seconds=0.05))
        second = websocket.receive_json()
        assert second["session_id"] == session_id
        assert "Audio payload exceeds configured maximum buffer duration" in second["error"]

        with pytest.raises(WebSocketDisconnect) as excinfo:
            websocket.receive_json()

        assert excinfo.value.code == 1009


@pytest.mark.parametrize(
    "edge_app",
    [
        {"token": "secret-token", "override_dependency": True},
    ],
    indirect=True,
)
def test_websocket_frame_streaming(edge_app):
    client = TestClient(edge_app)
    headers = {"X-API-Key": "secret-token"}
    session_id = client.post("/sessions", headers=headers).json()["session_id"]

    with client.websocket_connect(f"/ws/frame/{session_id}", headers=headers) as websocket:
        websocket: WebSocketTestSession

        websocket.send_bytes(_make_test_image_bytes(size=4))
        first = websocket.receive_json()
        assert first == {"session_id": session_id, "status": "frame stored"}

        websocket.send_bytes(_make_test_image_bytes(size=4))
        second = websocket.receive_json()
        assert second == {"session_id": session_id, "status": "frame stored"}

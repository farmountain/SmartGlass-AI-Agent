pytest_plugins = ["tests.test_edge_runtime_server"]

import pytest
from fastapi.testclient import TestClient

from tests.test_edge_runtime_server import _encode_silent_wav, _encode_test_image


@pytest.mark.parametrize(
    "edge_app", [{"env": {"PROVIDER": "mock"}}], indirect=True
)
def test_mobile_end_to_end_flow(edge_app):
    client = TestClient(edge_app)

    create_response = client.post("/sessions")
    assert 200 <= create_response.status_code < 300
    session_id = create_response.json()["session_id"]

    audio_payload = {"audio_base64": _encode_silent_wav(), "language": "en"}
    for _ in range(2):
        audio_response = client.post(
            f"/sessions/{session_id}/audio", json=audio_payload
        )
        assert 200 <= audio_response.status_code < 300

    frame_payload = {"image_base64": _encode_test_image(color=(0, 0, 0))}
    frame_response = client.post(f"/sessions/{session_id}/frame", json=frame_payload)
    assert 200 <= frame_response.status_code < 300

    query_payload = {"text_query": "Hello"}
    query_response = client.post(f"/sessions/{session_id}/query", json=query_payload)
    assert 200 <= query_response.status_code < 300

    result = query_response.json()
    assert "transcript" in result
    assert "response" in result


@pytest.mark.parametrize(
    "edge_app", [{"env": {"PROVIDER": "mock"}}], indirect=True
)
def test_mobile_handles_disconnect_and_bad_payloads(edge_app):
    client = TestClient(edge_app)

    # Simulate a mobile disconnect by deleting the session before sending audio
    session_id = client.post("/sessions").json()["session_id"]
    delete_response = client.delete(f"/sessions/{session_id}")
    assert 200 <= delete_response.status_code < 300

    missing_session_audio = client.post(
        f"/sessions/{session_id}/audio",
        json={"audio_base64": _encode_silent_wav(), "language": "en"},
    )
    assert missing_session_audio.status_code == 404
    assert "Unknown session id" in missing_session_audio.json()["detail"]

    # Verify malformed payloads are rejected with client errors
    active_session = client.post("/sessions").json()["session_id"]

    bad_audio_response = client.post(
        f"/sessions/{active_session}/audio",
        json={"audio_base64": "not-base64", "language": "en"},
    )
    assert bad_audio_response.status_code == 400
    assert "Invalid audio payload" in bad_audio_response.json()["detail"]

    bad_frame_response = client.post(
        f"/sessions/{active_session}/frame",
        json={"image_base64": "%%%not-base64%%%"},
    )
    assert bad_frame_response.status_code == 400
    assert "Invalid image payload" in bad_frame_response.json()["detail"]

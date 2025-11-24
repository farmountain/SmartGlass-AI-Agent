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

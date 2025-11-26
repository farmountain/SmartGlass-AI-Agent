"""Tests for the FastAPI server that wraps SmartGlassAgent."""

from __future__ import annotations

import importlib
import os
import sys
from types import SimpleNamespace
from unittest import mock

from fastapi.testclient import TestClient


def _load_server_module():
    os.environ["SDK_PYTHON_DUMMY_AGENT"] = "1"
    sys.modules.pop("sdk_python.server", None)
    with mock.patch.dict(
        sys.modules, {"src.smartglass_agent": SimpleNamespace(SmartGlassAgent=object)}
    ):
        return importlib.import_module("sdk_python.server")


def test_ingest_creates_session_id():
    server = _load_server_module()
    client = TestClient(server.app)

    response = client.post("/ingest", json={"text": "hello"})

    assert response.status_code == 200
    payload = response.json()
    assert "session_id" in payload


def test_answer_returns_response():
    server = _load_server_module()
    client = TestClient(server.app)

    ingest_response = client.post("/ingest", json={"text": "start"})
    session_id = ingest_response.json()["session_id"]

    answer_response = client.post(
        "/answer", json={"session_id": session_id, "text": "question"}
    )

    assert answer_response.status_code == 200
    payload = answer_response.json()
    assert "response" in payload


def test_answer_missing_session_returns_404():
    server = _load_server_module()
    client = TestClient(server.app)

    response = client.post(
        "/answer", json={"session_id": "missing-session", "text": "question"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_image_path_preserved_in_sessions():
    server = _load_server_module()
    client = TestClient(server.app)

    ingest_payload = {"text": "hello", "image_path": "/tmp/ingest.png"}
    ingest_response = client.post("/ingest", json=ingest_payload)
    session_id = ingest_response.json()["session_id"]

    assert server.SESSIONS[session_id] == ingest_payload

    answer_payload = {
        "session_id": session_id,
        "text": "question",
        "image_path": "/tmp/answer.png",
    }

    answer_response = client.post("/answer", json=answer_payload)
    assert answer_response.status_code == 200
    assert server.SESSIONS[session_id]["image_path"] == "/tmp/answer.png"
    assert server.SESSIONS[session_id]["text"] == "question"

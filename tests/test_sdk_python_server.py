"""Tests for the FastAPI server that wraps SmartGlassAgent."""

from __future__ import annotations

import importlib
import os

from fastapi.testclient import TestClient


def _load_server_module():
    os.environ["SDK_PYTHON_DUMMY_AGENT"] = "1"
    return importlib.reload(importlib.import_module("sdk_python.server"))


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

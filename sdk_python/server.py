"""Lightweight HTTP server exposing :class:`SmartGlassAgent` for mobile clients.

The FastAPI app defined here keeps an in-memory mapping of ``session_id`` values
to the latest context provided by the Android application. The server is kept
intentionally minimal to unblock early integrations; future iterations can
extend session handling, authentication, and streaming.
"""

from __future__ import annotations

import argparse
import logging
import os
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.smartglass_agent import SmartGlassAgent

logger = logging.getLogger(__name__)


class IngestRequest(BaseModel):
    """Payload for creating or updating a session."""

    text: str
    image_path: Optional[str] = None


class IngestResponse(BaseModel):
    """Response containing the generated session identifier."""

    session_id: str


class AnswerRequest(BaseModel):
    """Payload for generating an agent response within a session."""

    session_id: str
    text: str
    image_path: Optional[str] = None


class AnswerResponse(BaseModel):
    """Response from the agent including actions and raw payload."""

    response: str
    actions: list
    raw: dict


def _create_agent() -> SmartGlassAgent:
    """Instantiate the global SmartGlassAgent.

    The default behavior enforces ``PROVIDER=mock`` to avoid hardware
    dependencies. For lightweight testing, set ``SDK_PYTHON_DUMMY_AGENT=1`` to
    bypass heavy model initialization in favor of a simple stub.
    """

    os.environ.setdefault("PROVIDER", "mock")

    if os.getenv("SDK_PYTHON_DUMMY_AGENT") == "1":

        class _DummyAgent:
            def process_multimodal_query(
                self,
                audio_input: Optional[Any] = None,
                image_input: Optional[Any] = None,
                text_query: Optional[str] = None,
                language: Optional[str] = None,
                cloud_offload: bool = False,
            ) -> Dict[str, Any]:
                query_text = text_query or ""
                return {
                    "query": query_text,
                    "visual_context": "",
                    "response": f"Echo: {query_text}",
                    "metadata": {"cloud_offload": cloud_offload},
                    "actions": [],
                    "raw": {
                        "query": query_text,
                        "visual_context": "",
                        "metadata": {"cloud_offload": cloud_offload},
                    },
                }

        logger.info("Using dummy SmartGlassAgent for testing.")
        return _DummyAgent()  # type: ignore[return-value]

    return SmartGlassAgent()


AGENT = _create_agent()
SESSIONS: Dict[str, Dict[str, Optional[str]]] = {}

app = FastAPI(title="SmartGlass Agent Server", version="0.1.0")


@app.post("/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest) -> IngestResponse:
    """Create a new session or refresh context for an existing one."""

    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {"text": payload.text, "image_path": payload.image_path}
    logger.info("Ingested session %s", session_id)
    return IngestResponse(session_id=session_id)


@app.post("/answer", response_model=AnswerResponse)
def answer(payload: AnswerRequest) -> AnswerResponse:
    """Generate an agent response for the provided session."""

    if payload.session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    SESSIONS[payload.session_id] = {
        "text": payload.text,
        "image_path": payload.image_path,
    }

    result = AGENT.process_multimodal_query(
        text_query=payload.text,
        image_input=payload.image_path,
    )

    return AnswerResponse(
        response=result.get("response", ""),
        actions=result.get("actions", []),
        raw=result.get("raw", {}),
    )


def main(argv: Optional[list[str]] = None) -> None:
    """CLI entrypoint allowing ``python -m sdk_python.server``."""

    parser = argparse.ArgumentParser(description="Run SmartGlassAgent HTTP server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args(argv)

    import uvicorn

    uvicorn.run("sdk_python.server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":  # pragma: no cover - CLI bootstrap
    main()

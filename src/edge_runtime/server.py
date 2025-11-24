"""FastAPI server exposing SmartGlassAgent sessions for edge runtimes."""

import base64
import io
import logging
from typing import Any, Dict, Optional

import numpy as np
import soundfile as sf
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from PIL import Image
import uvicorn

from .config import EdgeRuntimeConfig, load_config_from_env
from .session_manager import BufferLimitExceeded, SessionManager

logger = logging.getLogger(__name__)


class CreateSessionResponse(BaseModel):
    session_id: str


class AudioPayload(BaseModel):
    audio_base64: str = Field(..., description="Base64-encoded audio data")
    language: Optional[str] = Field(None, description="Optional language code")


class FramePayload(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image data")


class QueryPayload(BaseModel):
    text_query: Optional[str] = Field(None, description="Text query to send to the agent")
    audio_base64: Optional[str] = Field(None, description="Optional base64-encoded audio")
    image_base64: Optional[str] = Field(None, description="Optional base64-encoded image")
    language: Optional[str] = Field(None, description="Optional language code")
    cloud_offload: bool = Field(False, description="Flag to redact and offload vision to cloud")


runtime_config: EdgeRuntimeConfig = load_config_from_env()
session_manager = SessionManager(runtime_config)


def _verify_api_key_header(x_api_key: str | None = Header(default=None)) -> None:
    """Guard HTTP endpoints with the configured API key if present."""

    if runtime_config.api_key is None:
        return

    if x_api_key != runtime_config.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


app = FastAPI(
    title="SmartGlass Edge Runtime",
    version="0.1.0",
    dependencies=[Depends(_verify_api_key_header)],
)


def _decode_audio_payload(audio_base64: str) -> tuple[np.ndarray, int]:
    try:
        audio_bytes = base64.b64decode(audio_base64)
        return _decode_audio_bytes(audio_bytes)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail=f"Invalid audio payload: {exc}") from exc


def _decode_audio_bytes(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    data, sample_rate = sf.read(io.BytesIO(audio_bytes))
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    return data.astype(np.float32), int(sample_rate)


def _decode_image_payload(image_base64: str) -> Image.Image:
    try:
        image_bytes = base64.b64decode(image_base64)
        return _decode_image_bytes(image_bytes)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail=f"Invalid image payload: {exc}") from exc


def _decode_image_bytes(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


@app.post("/sessions", response_model=CreateSessionResponse)
def create_session() -> Dict[str, str]:
    """Instantiate a new :class:`SmartGlassAgent` session."""

    logger.info("Creating new SmartGlassAgent session")
    session_id = session_manager.create_session()
    return {"session_id": session_id}


@app.post("/sessions/{session_id}/audio")
def post_audio(session_id: str, payload: AudioPayload) -> Dict[str, Any]:
    """Submit audio for transcription within the session."""

    try:
        audio_array, sample_rate = _decode_audio_payload(payload.audio_base64)
        transcript = session_manager.ingest_audio(
            session_id, audio_array, payload.language, sample_rate
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BufferLimitExceeded as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    return {"session_id": session_id, "transcript": transcript}


@app.post("/sessions/{session_id}/frame")
def post_frame(session_id: str, payload: FramePayload) -> Dict[str, Any]:
    """Submit a video frame for later multimodal queries."""

    try:
        frame = _decode_image_payload(payload.image_base64)
        session_manager.ingest_frame(session_id, frame)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BufferLimitExceeded as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    return {"session_id": session_id, "status": "frame stored"}


@app.post("/sessions/{session_id}/query")
def post_query(session_id: str, payload: QueryPayload) -> Dict[str, Any]:
    """Run a multimodal query using the stored session context."""

    if payload.text_query is None and payload.audio_base64 is None:
        raise HTTPException(status_code=400, detail="Provide either text_query or audio_base64")

    audio_input, audio_sample_rate = (
        _decode_audio_payload(payload.audio_base64) if payload.audio_base64 else (None, None)
    )
    image_input = _decode_image_payload(payload.image_base64) if payload.image_base64 else None

    try:
        result = session_manager.run_query(
            session_id,
            text_query=payload.text_query,
            audio_input=audio_input,
            audio_sample_rate=audio_sample_rate,
            image_input=image_input,
            language=payload.language,
            cloud_offload=payload.cloud_offload,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BufferLimitExceeded as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    return result


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> Dict[str, str]:
    """Tear down a session and free its resources."""

    try:
        session_manager.delete_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "deleted", "session_id": session_id}


@app.websocket("/ws/audio/{session_id}")
async def websocket_audio(session_id: str, websocket: WebSocket) -> None:
    """Ingest audio over WebSocket and stream transcripts back."""

    language = websocket.query_params.get("language")

    if runtime_config.api_key and websocket.headers.get("x-api-key") != runtime_config.api_key:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    try:
        session_manager.get_summary(session_id)
    except KeyError:
        await websocket.close(code=4404, reason="Unknown session id")
        return

    await websocket.accept()
    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            audio_array, sample_rate = _decode_audio_bytes(audio_bytes)
            transcript = session_manager.ingest_audio(
                session_id, audio_array, language, sample_rate
            )
            await websocket.send_json({"session_id": session_id, "transcript": transcript})
    except BufferLimitExceeded as exc:
        await websocket.send_json({"session_id": session_id, "error": str(exc)})
        await websocket.close(code=1009, reason="Buffer limit exceeded")
    except WebSocketDisconnect:
        logger.info("Audio WebSocket disconnected for session %s", session_id)
    finally:
        try:
            session_manager.delete_session(session_id)
        except KeyError:
            logger.debug("Session %s already cleaned up", session_id)


@app.websocket("/ws/frame/{session_id}")
async def websocket_frame(session_id: str, websocket: WebSocket) -> None:
    """Ingest frames over WebSocket for multimodal context."""

    if runtime_config.api_key and websocket.headers.get("x-api-key") != runtime_config.api_key:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    try:
        session_manager.get_summary(session_id)
    except KeyError:
        await websocket.close(code=4404, reason="Unknown session id")
        return

    await websocket.accept()
    try:
        while True:
            frame_bytes = await websocket.receive_bytes()
            frame = _decode_image_bytes(frame_bytes)
            session_manager.ingest_frame(session_id, frame)
            await websocket.send_json({"session_id": session_id, "status": "frame stored"})
    except BufferLimitExceeded as exc:
        await websocket.send_json({"session_id": session_id, "error": str(exc)})
        await websocket.close(code=1009, reason="Buffer limit exceeded")
    except WebSocketDisconnect:
        logger.info("Frame WebSocket disconnected for session %s", session_id)
    finally:
        try:
            session_manager.delete_session(session_id)
        except KeyError:
            logger.debug("Session %s already cleaned up", session_id)


def main() -> None:
    """Entrypoint for ``python -m src.edge_runtime.server``."""

    logging.basicConfig(level=logging.INFO)
    logger.info(
        "Starting SmartGlass Edge Runtime with provider=%s, whisper_model=%s, vision_model=%s",
        runtime_config.provider,
        runtime_config.whisper_model,
        runtime_config.vision_model,
    )
    uvicorn.run(
        "src.edge_runtime.server:app",
        host="0.0.0.0",
        port=runtime_config.ports.get("http", 8000),
        log_level="info",
    )


if __name__ == "__main__":
    main()

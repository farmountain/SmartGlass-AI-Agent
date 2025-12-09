"""FastAPI server exposing SmartGlassAgent sessions for edge runtimes."""

import base64
import copy
import io
import logging
import logging.config
from contextvars import ContextVar
from typing import Any, Dict, Optional
from uuid import uuid4

import numpy as np
import soundfile as sf
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from PIL import Image
import uvicorn
from uvicorn.config import LOGGING_CONFIG

from .config import EdgeRuntimeConfig, load_config_from_env
from .session_manager import BufferLimitExceeded, SessionManager
from src.utils.metrics import get_metrics_snapshot, get_metrics_summary, record_latency
from src.wire.dat_protocol import (
    SessionInitRequest,
    SessionInitResponse,
    StreamChunk,
    StreamChunkResponse,
    TurnCompleteRequest,
    TurnCompleteResponse,
    ChunkStatus,
    ChunkType,
    ErrorCode,
    ErrorResponse,
)
from drivers.providers.meta import _DAT_REGISTRY

logger = logging.getLogger(__name__)

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
session_id_ctx: ContextVar[str] = ContextVar("session_id", default="-")


class ContextFilter(logging.Filter):
    """Attach request/session context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        record.request_id = request_id_ctx.get("-")
        record.session_id = session_id_ctx.get("-")
        return True


def _build_log_config() -> Dict[str, Any]:
    """Generate a uvicorn log config that includes request and session IDs."""

    log_config = copy.deepcopy(LOGGING_CONFIG)
    log_config.setdefault("formatters", {})
    log_config.setdefault("handlers", {})
    log_config.setdefault("filters", {})

    log_config["formatters"].setdefault("default", {})
    log_config["formatters"]["default"].update(
        {
            "fmt": "%(levelprefix)s %(asctime)s | %(name)s | request_id=%(request_id)s | session_id=%(session_id)s | %(message)s",
            "use_colors": False,
        }
    )

    log_config["formatters"].setdefault("access", {})
    log_config["formatters"]["access"].update(
        {
            "fmt": "%(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s request_id=%(request_id)s session_id=%(session_id)s",
            "use_colors": False,
        }
    )

    log_config["filters"]["context"] = {"()": ContextFilter}

    for handler_name in ("default", "access"):
        log_config["handlers"].setdefault(handler_name, {})
        log_config["handlers"][handler_name].setdefault("filters", [])
        if "context" not in log_config["handlers"][handler_name]["filters"]:
            log_config["handlers"][handler_name]["filters"].append("context")

    return log_config


log_config: Dict[str, Any] = _build_log_config()


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


def _verify_api_key_header(request: Request) -> None:
    """Guard HTTP endpoints with the configured API key if present."""

    _verify_auth_token(request)


def _verify_auth_token(headers: Dict[str, Optional[str]] | Request | WebSocket) -> None:
    """Validate the request headers against the configured auth token."""

    expected_token = runtime_config.auth_token or runtime_config.api_key
    if expected_token is None:
        return

    header_name = runtime_config.auth_header_name.lower()
    provided_value = None
    if isinstance(headers, (Request, WebSocket)):
        provided_value = headers.headers.get(header_name)
    else:
        for key, value in headers.items():
            if key.lower() == header_name:
                provided_value = value
                break

    if provided_value is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if provided_value.lower().startswith("bearer "):
        provided_value = provided_value[7:].strip()

    if provided_value != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


app = FastAPI(
    title="SmartGlass Edge Runtime",
    version="0.1.0",
    dependencies=[Depends(_verify_api_key_header)],
)


@app.middleware("http")
async def add_trace_context(request: Request, call_next):
    """Attach request and session IDs to request context and responses."""

    request_id = request.headers.get("x-request-id") or str(uuid4())
    session_id = request.path_params.get("session_id", "-")

    request_id_token = request_id_ctx.set(request_id)
    session_id_token = session_id_ctx.set(session_id)

    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(request_id_token)
        session_id_ctx.reset(session_id_token)

    response.headers["X-Request-ID"] = request_id
    if session_id != "-":
        response.headers["X-Session-ID"] = session_id

    return response


@app.get("/health")
def healthcheck() -> Dict[str, str]:
    """Lightweight liveness endpoint."""

    return {"status": "ok"}


@app.get("/ready")
def readiness() -> Dict[str, str]:
    """Readiness probe for deployment environments."""

    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Dict[str, object]:
    """Expose aggregate latency and lifecycle metrics."""

    display_available = session_manager.display_available()
    return get_metrics_snapshot(display_available=display_available)


@app.get("/metrics/summary")
def metrics_summary() -> Dict[str, object]:
    """Expose a compact metrics summary for mobile clients.
    
    Returns a lightweight JSON response optimized for Android/iOS apps,
    including DAT-specific latencies and overall health state.
    
    Example response:
        {
            "health": "ok",
            "dat_metrics": {
                "ingest_audio": {"count": 42, "avg_ms": 15.3, "max_ms": 32.1},
                "ingest_frame": {"count": 38, "avg_ms": 22.7, "max_ms": 45.2},
                "end_to_end_turn": {"count": 12, "avg_ms": 850.4, "max_ms": 1203.5}
            },
            "summary": {
                "total_sessions": 12,
                "active_sessions": 3,
                "total_queries": 45
            }
        }
    """
    return get_metrics_summary()


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
def create_session(request: Request) -> Dict[str, str]:
    """Instantiate a new :class:`SmartGlassAgent` session.
    
    Privacy preferences can be included as headers:
    - X-Privacy-Store-Raw-Audio: true/false
    - X-Privacy-Store-Raw-Frames: true/false
    - X-Privacy-Store-Transcripts: true/false
    """

    logger.info("Creating new SmartGlassAgent session")
    
    # Extract privacy preferences from headers
    privacy_flags = {}
    if "X-Privacy-Store-Raw-Audio" in request.headers:
        privacy_flags["store_raw_audio"] = request.headers["X-Privacy-Store-Raw-Audio"].lower() == "true"
    if "X-Privacy-Store-Raw-Frames" in request.headers:
        privacy_flags["store_raw_frames"] = request.headers["X-Privacy-Store-Raw-Frames"].lower() == "true"
    if "X-Privacy-Store-Transcripts" in request.headers:
        privacy_flags["store_transcripts"] = request.headers["X-Privacy-Store-Transcripts"].lower() == "true"
    
    if privacy_flags:
        logger.info(
            "Privacy preferences for session: %s",
            privacy_flags,
        )
    
    # TODO: Pass privacy_flags to session creation once session manager supports per-session privacy settings
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
    request_id = websocket.headers.get("x-request-id") or str(uuid4())

    request_id_token = request_id_ctx.set(request_id)
    session_id_token = session_id_ctx.set(session_id)

    try:
        _verify_auth_token(websocket)
    except HTTPException:
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
        request_id_ctx.reset(request_id_token)
        session_id_ctx.reset(session_id_token)


@app.websocket("/ws/frame/{session_id}")
async def websocket_frame(session_id: str, websocket: WebSocket) -> None:
    """Ingest frames over WebSocket for multimodal context."""

    request_id = websocket.headers.get("x-request-id") or str(uuid4())

    request_id_token = request_id_ctx.set(request_id)
    session_id_token = session_id_ctx.set(session_id)

    try:
        _verify_auth_token(websocket)
    except HTTPException:
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
        request_id_ctx.reset(request_id_token)
        session_id_ctx.reset(session_id_token)


# DAT Wire Protocol Endpoints


@app.post("/dat/session", response_model=SessionInitResponse)
def dat_session_init(payload: SessionInitRequest) -> SessionInitResponse:
    """Initialize a new DAT streaming session.
    
    This endpoint creates a new session for streaming audio/video/sensor data
    from the Android DAT client. The session_id returned should be used in
    all subsequent stream and turn completion requests.
    
    Privacy flags can be included in the metadata field to control what data
    is retained during the session:
    - privacy_store_raw_audio: Allow temporary storage of raw audio buffers
    - privacy_store_raw_frames: Allow temporary storage of video frames
    - privacy_store_transcripts: Allow storing transcripts for session history
    
    Args:
        payload: SessionInitRequest with device_id, client_version, and capabilities
        
    Returns:
        SessionInitResponse with session_id and server capabilities
        
    Example:
        >>> # Request
        >>> {
        >>>   "device_id": "rayban-meta-12345",
        >>>   "client_version": "1.0.0",
        >>>   "capabilities": {
        >>>     "audio_streaming": true,
        >>>     "video_streaming": true
        >>>   },
        >>>   "metadata": {
        >>>     "privacy_store_raw_audio": true,
        >>>     "privacy_store_raw_frames": false,
        >>>     "privacy_store_transcripts": true
        >>>   }
        >>> }
        >>> # Response
        >>> {
        >>>   "session_id": "550e8400-e29b-41d4-a716-446655440000",
        >>>   "server_version": "0.1.0",
        >>>   "max_chunk_size_bytes": 1048576
        >>> }
    """
    logger.info(
        "Initializing DAT session for device_id=%s, client_version=%s",
        payload.device_id,
        payload.client_version,
    )
    
    # Extract privacy preferences from metadata
    privacy_flags = {}
    if payload.metadata:
        privacy_flags = {
            "store_raw_audio": payload.metadata.get("privacy_store_raw_audio", runtime_config.store_raw_audio),
            "store_raw_frames": payload.metadata.get("privacy_store_raw_frames", runtime_config.store_raw_frames),
            "store_transcripts": payload.metadata.get("privacy_store_transcripts", runtime_config.store_transcripts),
        }
        logger.info(
            "Privacy preferences for session: audio=%s, frames=%s, transcripts=%s",
            privacy_flags.get("store_raw_audio"),
            privacy_flags.get("store_raw_frames"),
            privacy_flags.get("store_transcripts"),
        )
    
    # TODO: Pass privacy_flags to session creation once session manager supports per-session privacy settings
    session_id = session_manager.create_session()
    
    return SessionInitResponse(
        session_id=session_id,
        server_version="0.1.0",  # TODO: Get from config or package metadata
        max_chunk_size_bytes=1048576,  # 1MB default
    )


@app.post("/dat/stream", response_model=StreamChunkResponse)
def dat_stream_chunk(payload: StreamChunk) -> StreamChunkResponse:
    """Receive and buffer a stream chunk (audio/frame/IMU).
    
    This endpoint receives data chunks from the mobile app and stores them
    in the session-specific DAT registry. The chunks are later processed
    when the client calls the turn completion endpoint.
    
    Args:
        payload: StreamChunk with session_id, chunk_type, payload, and metadata
        
    Returns:
        StreamChunkResponse acknowledging receipt and processing status
        
    Raises:
        HTTPException: 404 if session not found, 413 if buffer limit exceeded
        
    Example:
        >>> # Audio chunk request
        >>> {
        >>>   "session_id": "550e8400-e29b-41d4-a716-446655440000",
        >>>   "chunk_type": "audio",
        >>>   "sequence_number": 0,
        >>>   "timestamp_ms": 1702080000000,
        >>>   "payload": "base64_encoded_audio_data...",
        >>>   "meta": {
        >>>     "sample_rate": 16000,
        >>>     "channels": 1,
        >>>     "format": "pcm_s16le"
        >>>   }
        >>> }
    """
    logger.debug(
        "Received stream chunk: session_id=%s, chunk_type=%s, sequence_number=%d",
        payload.session_id,
        payload.chunk_type,
        payload.sequence_number,
    )
    
    # Verify session exists
    try:
        session_manager.get_summary(payload.session_id)
    except KeyError as exc:
        logger.warning("Unknown session_id=%s for stream chunk", payload.session_id)
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {payload.session_id}",
        ) from exc
    
    try:
        # Decode base64 payload
        data_bytes = base64.b64decode(payload.payload)
        
        # Validate payload size to prevent memory exhaustion
        max_size = 10 * 1024 * 1024  # 10MB hard limit
        if len(data_bytes) > max_size:
            raise ValueError(f"Payload size {len(data_bytes)} exceeds maximum {max_size} bytes")
        
        if payload.chunk_type == ChunkType.AUDIO:
            # TODO: Validate audio metadata and convert if needed
            # For now, store raw audio bytes with metadata
            # In production, decode based on format (pcm_s16le, opus, etc.)
            with record_latency("dat_ingest_audio_latency_ms"):
                audio_meta = {
                    "sequence_number": payload.sequence_number,
                    "timestamp_ms": payload.timestamp_ms,
                    "format": payload.meta.format if payload.meta else "unknown",
                    "sample_rate": payload.meta.sample_rate if payload.meta else 16000,
                }
                
                # Convert bytes to audio array for compatibility with existing system
                # Assume pcm_s16le for now
                if payload.meta and payload.meta.format == "pcm_s16le":
                    audio_array = np.frombuffer(data_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                else:
                    # For other formats, decode using soundfile
                    audio_array, sample_rate = _decode_audio_bytes(data_bytes)
                    audio_meta["sample_rate"] = sample_rate
                
                _DAT_REGISTRY.set_audio(payload.session_id, audio_array, audio_meta)
            
        elif payload.chunk_type == ChunkType.FRAME:
            # Decode image from JPEG/PNG bytes
            with record_latency("dat_ingest_frame_latency_ms"):
                frame = _decode_image_bytes(data_bytes)
                frame_array = np.array(frame)
                
                frame_meta = {
                    "sequence_number": payload.sequence_number,
                    "timestamp_ms": payload.timestamp_ms,
                    "width": payload.meta.width if payload.meta else frame_array.shape[1],
                    "height": payload.meta.height if payload.meta else frame_array.shape[0],
                    "format": payload.meta.format if payload.meta else "jpeg",
                }
                
                _DAT_REGISTRY.set_frame(payload.session_id, frame_array, frame_meta)
            
        elif payload.chunk_type == ChunkType.IMU:
            # TODO: Implement IMU data handling
            # For now, just acknowledge receipt
            logger.info(
                "IMU chunk received but not yet implemented: session_id=%s",
                payload.session_id,
            )
            
        return StreamChunkResponse(
            session_id=payload.session_id,
            sequence_number=payload.sequence_number,
            status=ChunkStatus.BUFFERED,
            message="Chunk buffered successfully",
        )
        
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "Error processing stream chunk: session_id=%s, error=%s",
            payload.session_id,
            str(exc),
        )
        return StreamChunkResponse(
            session_id=payload.session_id,
            sequence_number=payload.sequence_number,
            status=ChunkStatus.ERROR,
            message=f"Error processing chunk: {str(exc)}",
        )


@app.post("/dat/turn/complete", response_model=TurnCompleteResponse)
def dat_turn_complete(payload: TurnCompleteRequest) -> TurnCompleteResponse:
    """Finalize a turn and receive agent response with actions.
    
    This endpoint processes all buffered stream chunks for the session,
    runs the SmartGlass agent to generate a response, and returns
    the natural language response along with any actions to execute.
    
    Args:
        payload: TurnCompleteRequest with session_id, turn_id, and optional query
        
    Returns:
        TurnCompleteResponse with agent response, transcript, and actions
        
    Raises:
        HTTPException: 404 if session not found
        
    Example:
        >>> # Request
        >>> {
        >>>   "session_id": "550e8400-e29b-41d4-a716-446655440000",
        >>>   "turn_id": "660e8400-e29b-41d4-a716-446655440001",
        >>>   "language": "en",
        >>>   "cloud_offload": false
        >>> }
        >>> # Response
        >>> {
        >>>   "session_id": "550e8400-e29b-41d4-a716-446655440000",
        >>>   "turn_id": "660e8400-e29b-41d4-a716-446655440001",
        >>>   "response": "I can see you're looking at a coffee shop. Would you like directions?",
        >>>   "transcript": "What am I looking at?",
        >>>   "actions": [
        >>>     {
        >>>       "action_type": "NAVIGATE",
        >>>       "parameters": {"destination": "Nearest Coffee Shop"},
        >>>       "priority": "normal"
        >>>     }
        >>>   ]
        >>> }
    """
    with record_latency("end_to_end_turn_latency_ms"):
        logger.info(
            "Turn completion requested: session_id=%s, turn_id=%s",
            payload.session_id,
            payload.turn_id,
        )
        
        # Verify session exists
        try:
            session_manager.get_summary(payload.session_id)
        except KeyError as exc:
            logger.warning("Unknown session_id=%s for turn completion", payload.session_id)
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {payload.session_id}",
            ) from exc
        
        # TODO: Implement full turn completion logic
        # 1. Retrieve buffered audio/frames from _DAT_REGISTRY
        # 2. Run agent query with multimodal inputs
        # 3. Parse agent response and extract actions
        # 4. Clear buffers after processing
        
        # For now, return a placeholder response
        logger.warning(
            "Turn completion not fully implemented yet. Returning placeholder response."
        )
        
        # Get transcript from audio if available (simplified)
        transcript = None
        if payload.query_text:
            transcript = payload.query_text
        else:
            # TODO: Process buffered audio to get transcript
            # audio, meta = _DAT_REGISTRY.get_latest_audio_buffer(payload.session_id)
            # if audio is not None:
            #     transcript = session_manager.ingest_audio(...)
            pass
        
        # TODO: Process buffered frames and run multimodal query
        # frame, meta = _DAT_REGISTRY.get_latest_frame(payload.session_id)
        # if frame is not None:
        #     result = session_manager.run_query(
        #         payload.session_id,
        #         text_query=transcript,
        #         image_input=frame,
        #         ...
        #     )
        
        return TurnCompleteResponse(
            session_id=payload.session_id,
            turn_id=payload.turn_id,
        response="Turn completion endpoint is under development. Full implementation coming soon.",
        transcript=transcript,
        actions=[],
        metadata=None,
    )


def main() -> None:
    """Entrypoint for ``python -m src.edge_runtime.server``."""

    logging.config.dictConfig(log_config)
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
        log_config=log_config,
    )


if __name__ == "__main__":
    main()

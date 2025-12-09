"""DAT Wire Protocol - Pydantic models for Android ↔ Python communication.

This module defines strongly-typed Pydantic models for the wire protocol between
the Android DAT client and the SmartGlass-AI-Agent Python backend. The protocol
supports session management, streaming data chunks (audio/video/IMU), and turn
completion with agent responses.

The schema is designed to be:
- Easy to consume from Android (maps cleanly to Kotlin data classes)
- Extensible for future sensor types
- Type-safe with validation
- Compatible with FastAPI automatic serialization/deserialization

See Also:
    - schemas/dat_wire_protocol.json: JSON Schema definition
    - src/edge_runtime/server.py: FastAPI endpoints using these models
    - sdk-android/: Android client implementation
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# Enums for type safety


class ChunkType(str, Enum):
    """Type of data in a StreamChunk."""

    AUDIO = "audio"
    FRAME = "frame"
    IMU = "imu"


class ChunkStatus(str, Enum):
    """Processing status for StreamChunkResponse."""

    ACCEPTED = "accepted"
    BUFFERED = "buffered"
    ERROR = "error"


class ActionType(str, Enum):
    """Types of actions the agent can request the client to perform."""

    NAVIGATE = "NAVIGATE"
    SHOW_TEXT = "SHOW_TEXT"
    PLAY_AUDIO = "PLAY_AUDIO"
    SHOW_IMAGE = "SHOW_IMAGE"
    VIBRATE = "VIBRATE"
    NOTIFICATION = "NOTIFICATION"
    OPEN_APP = "OPEN_APP"
    SEARCH = "SEARCH"
    CUSTOM = "CUSTOM"


class Priority(str, Enum):
    """Action priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ErrorCode(str, Enum):
    """Standard error codes for ErrorResponse."""

    INVALID_SESSION = "INVALID_SESSION"
    INVALID_CHUNK = "INVALID_CHUNK"
    BUFFER_OVERFLOW = "BUFFER_OVERFLOW"
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"


# Session initialization models


class ClientCapabilities(BaseModel):
    """Client capabilities and supported features."""

    audio_streaming: bool = True
    video_streaming: bool = True
    imu_streaming: bool = False


class SessionInitRequest(BaseModel):
    """Request to initialize a new DAT streaming session."""

    device_id: str = Field(..., description="Unique identifier for the Ray-Ban glasses device")
    client_version: str = Field(
        ..., description="Version of the Android client application", pattern=r"^\d+\.\d+\.\d+$"
    )
    capabilities: ClientCapabilities = Field(
        default_factory=ClientCapabilities,
        description="Client capabilities and supported features",
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional client metadata")


class ServerCapabilities(BaseModel):
    """Server capabilities."""

    multimodal_queries: bool = True
    streaming_transcription: bool = False


class SessionInitResponse(BaseModel):
    """Response containing the new session identifier."""

    session_id: str = Field(
        ...,
        description="Unique session identifier (UUID format)",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    server_version: str = Field(
        ..., description="Version of the SmartGlass backend", pattern=r"^\d+\.\d+\.\d+$"
    )
    max_chunk_size_bytes: int = Field(
        default=1048576,
        description="Maximum size for stream chunk payloads in bytes",
        ge=1024,
    )
    capabilities: ServerCapabilities = Field(
        default_factory=ServerCapabilities, description="Server capabilities"
    )


# Streaming chunk models


class AudioMeta(BaseModel):
    """Metadata for audio chunks."""

    sample_rate: int = Field(..., description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels (1 or 2)")
    format: str = Field(
        default="pcm_s16le", description="Audio encoding format (pcm_s16le, pcm_f32le, opus)"
    )
    duration_ms: Optional[int] = Field(
        None, description="Duration of audio chunk in milliseconds", ge=0
    )

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: int) -> int:
        """Validate sample rate is a common value."""
        allowed = {8000, 16000, 22050, 44100, 48000}
        if v not in allowed:
            raise ValueError(f"sample_rate must be one of {allowed}")
        return v

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: int) -> int:
        """Validate channel count."""
        if v not in {1, 2}:
            raise ValueError("channels must be 1 or 2")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate audio format."""
        allowed = {"pcm_s16le", "pcm_f32le", "opus"}
        if v not in allowed:
            raise ValueError(f"format must be one of {allowed}")
        return v


class FrameMeta(BaseModel):
    """Metadata for video frame chunks."""

    width: int = Field(..., description="Frame width in pixels", gt=0)
    height: int = Field(..., description="Frame height in pixels", gt=0)
    format: str = Field(default="jpeg", description="Image encoding format")
    quality: Optional[int] = Field(
        None, description="JPEG quality (0-100) if applicable", ge=0, le=100
    )
    is_keyframe: bool = Field(
        default=True, description="Whether this is a keyframe in the stream"
    )

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate image format."""
        allowed = {"jpeg", "png", "yuv420", "i420"}
        if v not in allowed:
            raise ValueError(f"format must be one of {allowed}")
        return v


class ImuMeta(BaseModel):
    """Metadata for IMU sensor data chunks."""

    sensor_type: str = Field(..., description="Type of IMU sensor data")
    sample_count: int = Field(
        ..., description="Number of samples in this chunk", gt=0
    )

    @field_validator("sensor_type")
    @classmethod
    def validate_sensor_type(cls, v: str) -> str:
        """Validate sensor type."""
        allowed = {"accelerometer", "gyroscope", "magnetometer"}
        if v not in allowed:
            raise ValueError(f"sensor_type must be one of {allowed}")
        return v


class StreamChunk(BaseModel):
    """Envelope for streaming audio/video/sensor data chunks."""

    session_id: str = Field(
        ...,
        description="Session identifier from SessionInitResponse",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    chunk_type: ChunkType = Field(..., description="Type of data in this chunk")
    sequence_number: int = Field(
        ...,
        description="Monotonically increasing sequence number for ordering",
        ge=0,
    )
    timestamp_ms: int = Field(
        ..., description="Client-side timestamp in milliseconds since epoch", ge=0
    )
    payload: str = Field(
        ...,
        description="Base64-encoded binary data (audio samples, JPEG frame, or IMU data)",
    )
    meta: Optional[Union[AudioMeta, FrameMeta, ImuMeta]] = Field(
        None, description="Type-specific metadata"
    )

    @field_validator("meta", mode="before")
    @classmethod
    def validate_meta_type(cls, v: Any, info: Any) -> Any:
        """Ensure meta matches chunk_type if provided."""
        if v is None:
            return v

        # Access values dict to get chunk_type
        values = info.data if hasattr(info, "data") else {}
        chunk_type = values.get("chunk_type")

        if chunk_type == ChunkType.AUDIO:
            return AudioMeta(**v) if isinstance(v, dict) else v
        elif chunk_type == ChunkType.FRAME:
            return FrameMeta(**v) if isinstance(v, dict) else v
        elif chunk_type == ChunkType.IMU:
            return ImuMeta(**v) if isinstance(v, dict) else v

        return v


class StreamChunkResponse(BaseModel):
    """Acknowledgment response for stream chunks."""

    session_id: str = Field(..., description="Session identifier")
    sequence_number: int = Field(..., description="Acknowledged sequence number", ge=0)
    status: ChunkStatus = Field(..., description="Processing status")
    message: Optional[str] = Field(None, description="Optional status message")


# Turn completion models


class TurnCompleteRequest(BaseModel):
    """Request to finalize a turn and receive agent response."""

    session_id: str = Field(
        ...,
        description="Session identifier",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    turn_id: str = Field(
        ...,
        description="Unique identifier for this turn (client-generated)",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    query_text: Optional[str] = Field(
        None, description="Optional explicit text query (if not using audio transcription)"
    )
    language: Optional[str] = Field(
        None, description="Optional language code for query (ISO 639-1)", pattern=r"^[a-z]{2}(-[A-Z]{2})?$"
    )
    cloud_offload: bool = Field(
        default=False, description="Whether to offload processing to cloud (may redact PII)"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional turn metadata")


class Action(BaseModel):
    """Agent-generated action to execute on client."""

    action_type: ActionType = Field(..., description="Type of action to perform")
    parameters: Dict[str, Any] = Field(..., description="Action-specific parameters")
    priority: Priority = Field(default=Priority.NORMAL, description="Action priority level")


class ResponseMetadata(BaseModel):
    """Response metadata (timing, model info, etc.)."""

    processing_time_ms: Optional[int] = Field(
        None, description="Total processing time in milliseconds", ge=0
    )
    model_version: Optional[str] = Field(None, description="Version of the AI model used")
    # Allow additional fields for extensibility
    extra: Optional[Dict[str, Any]] = None


class TurnCompleteResponse(BaseModel):
    """Agent response with NLG result and actions."""

    session_id: str = Field(..., description="Session identifier")
    turn_id: str = Field(..., description="Turn identifier from request")
    response: str = Field(..., description="Natural language response from agent")
    transcript: Optional[str] = Field(
        None, description="Transcribed audio query (if audio was provided)"
    )
    actions: list[Action] = Field(
        default_factory=list, description="List of actions for client to execute"
    )
    metadata: Optional[ResponseMetadata] = Field(
        None, description="Response metadata (timing, model info, etc.)"
    )


# Error handling


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorCode = Field(..., description="Error code or type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

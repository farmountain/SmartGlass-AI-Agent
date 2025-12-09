"""Tests for DAT wire protocol Pydantic models and validation.

Note on import pattern:
This test uses importlib to load the wire protocol module directly, bypassing
src/__init__.py which imports heavy dependencies (whisper, torch, etc.).
This allows these lightweight tests to run without those dependencies installed,
which is important for CI/CD environments and fast test execution.

Alternative approaches considered:
- Lazy imports in src/__init__.py (rejected: too invasive)
- Separate package for wire protocol (rejected: over-engineering)
- Mock heavy imports (rejected: fragile and complex)

This pattern is specific to testing modules that don't actually need the heavy
dependencies but are located in the src/ package.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Import the wire protocol module directly without triggering src/__init__.py
wire_protocol_path = Path(__file__).parent.parent / "src" / "wire" / "dat_protocol.py"
spec = importlib.util.spec_from_file_location("dat_protocol", wire_protocol_path)
dat_protocol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dat_protocol)

# Import all needed classes from the module
Action = dat_protocol.Action
ActionType = dat_protocol.ActionType
AudioMeta = dat_protocol.AudioMeta
ChunkStatus = dat_protocol.ChunkStatus
ChunkType = dat_protocol.ChunkType
ClientCapabilities = dat_protocol.ClientCapabilities
ErrorCode = dat_protocol.ErrorCode
ErrorResponse = dat_protocol.ErrorResponse
FrameMeta = dat_protocol.FrameMeta
ImuMeta = dat_protocol.ImuMeta
Priority = dat_protocol.Priority
ResponseMetadata = dat_protocol.ResponseMetadata
ServerCapabilities = dat_protocol.ServerCapabilities
SessionInitRequest = dat_protocol.SessionInitRequest
SessionInitResponse = dat_protocol.SessionInitResponse
StreamChunk = dat_protocol.StreamChunk
StreamChunkResponse = dat_protocol.StreamChunkResponse
TurnCompleteRequest = dat_protocol.TurnCompleteRequest
TurnCompleteResponse = dat_protocol.TurnCompleteResponse

# Rebuild Pydantic models to resolve forward references with proper namespace
# Include the module's namespace so typing annotations can be resolved
import typing
from typing import Optional, Union, Any, Dict, List
namespace = {
    'ClientCapabilities': ClientCapabilities,
    'ServerCapabilities': ServerCapabilities,
    'AudioMeta': AudioMeta,
    'FrameMeta': FrameMeta,
    'ImuMeta': ImuMeta,
    'ChunkType': ChunkType,
    'ChunkStatus': ChunkStatus,
    'ActionType': ActionType,
    'Priority': Priority,
    'ErrorCode': ErrorCode,
    'ResponseMetadata': ResponseMetadata,
    'Action': Action,
    'Optional': Optional,
    'Union': Union,
    'Any': Any,
    'Dict': Dict,
    'List': List,
    'list': list,
}

for model in [ClientCapabilities, ServerCapabilities, AudioMeta, FrameMeta, ImuMeta,
              SessionInitRequest, SessionInitResponse, StreamChunk, StreamChunkResponse,
              TurnCompleteRequest, TurnCompleteResponse, Action, ErrorResponse,
              ResponseMetadata]:
    if hasattr(model, 'model_rebuild'):
        try:
            model.model_rebuild(_types_namespace=namespace)
        except Exception:
            # If rebuild fails, continue - tests may still work
            pass


class TestSessionInitModels:
    """Test session initialization request and response models."""

    def test_session_init_request_valid(self):
        """Test valid SessionInitRequest creation."""
        request = SessionInitRequest(
            device_id="rayban-meta-12345",
            client_version="1.0.0",
        )
        assert request.device_id == "rayban-meta-12345"
        assert request.client_version == "1.0.0"
        assert request.capabilities.audio_streaming is True
        assert request.capabilities.video_streaming is True

    def test_session_init_request_with_capabilities(self):
        """Test SessionInitRequest with custom capabilities."""
        request = SessionInitRequest(
            device_id="rayban-meta-12345",
            client_version="2.1.0",
            capabilities={
                "audio_streaming": True,
                "video_streaming": False,
                "imu_streaming": True,
            },
        )
        assert request.capabilities.audio_streaming is True
        assert request.capabilities.video_streaming is False
        assert request.capabilities.imu_streaming is True

    def test_session_init_request_invalid_version(self):
        """Test SessionInitRequest rejects invalid version format."""
        with pytest.raises(ValidationError) as exc_info:
            SessionInitRequest(
                device_id="rayban-meta-12345",
                client_version="1.0",  # Invalid: must be X.Y.Z
            )
        assert "client_version" in str(exc_info.value)

    def test_session_init_response_valid(self):
        """Test valid SessionInitResponse creation."""
        response = SessionInitResponse(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            server_version="0.1.0",
        )
        assert response.session_id == "550e8400-e29b-41d4-a716-446655440000"
        assert response.server_version == "0.1.0"
        assert response.max_chunk_size_bytes == 1048576  # Default 1MB

    def test_session_init_response_invalid_session_id(self):
        """Test SessionInitResponse rejects invalid UUID format."""
        with pytest.raises(ValidationError) as exc_info:
            SessionInitResponse(
                session_id="not-a-valid-uuid",
                server_version="0.1.0",
            )
        assert "session_id" in str(exc_info.value)


class TestStreamChunkModels:
    """Test stream chunk models and metadata validation."""

    def test_audio_meta_valid(self):
        """Test valid AudioMeta creation."""
        meta = AudioMeta(
            sample_rate=16000,
            channels=1,
            format="pcm_s16le",
            duration_ms=1000,
        )
        assert meta.sample_rate == 16000
        assert meta.channels == 1
        assert meta.format == "pcm_s16le"

    def test_audio_meta_invalid_sample_rate(self):
        """Test AudioMeta rejects invalid sample rate."""
        with pytest.raises(ValidationError) as exc_info:
            AudioMeta(
                sample_rate=12345,  # Not in allowed list
                channels=1,
            )
        assert "sample_rate" in str(exc_info.value)

    def test_audio_meta_invalid_channels(self):
        """Test AudioMeta rejects invalid channel count."""
        with pytest.raises(ValidationError) as exc_info:
            AudioMeta(
                sample_rate=16000,
                channels=5,  # Must be 1 or 2
            )
        assert "channels" in str(exc_info.value)

    def test_frame_meta_valid(self):
        """Test valid FrameMeta creation."""
        meta = FrameMeta(
            width=1920,
            height=1080,
            format="jpeg",
            quality=85,
            is_keyframe=True,
        )
        assert meta.width == 1920
        assert meta.height == 1080
        assert meta.format == "jpeg"
        assert meta.quality == 85

    def test_frame_meta_invalid_dimensions(self):
        """Test FrameMeta rejects invalid dimensions."""
        with pytest.raises(ValidationError):
            FrameMeta(
                width=0,  # Must be > 0
                height=1080,
                format="jpeg",
            )

    def test_imu_meta_valid(self):
        """Test valid ImuMeta creation."""
        meta = ImuMeta(
            sensor_type="accelerometer",
            sample_count=10,
        )
        assert meta.sensor_type == "accelerometer"
        assert meta.sample_count == 10

    def test_imu_meta_invalid_sensor_type(self):
        """Test ImuMeta rejects invalid sensor type."""
        with pytest.raises(ValidationError) as exc_info:
            ImuMeta(
                sensor_type="invalid_sensor",
                sample_count=10,
            )
        assert "sensor_type" in str(exc_info.value)

    def test_stream_chunk_audio(self):
        """Test StreamChunk with audio data."""
        chunk = StreamChunk(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            chunk_type=ChunkType.AUDIO,
            sequence_number=0,
            timestamp_ms=1702080000000,
            payload="YmFzZTY0X2VuY29kZWRfYXVkaW8=",
            meta=AudioMeta(sample_rate=16000, channels=1),
        )
        assert chunk.chunk_type == ChunkType.AUDIO
        assert chunk.sequence_number == 0
        assert isinstance(chunk.meta, AudioMeta)
        assert chunk.meta.sample_rate == 16000

    def test_stream_chunk_frame(self):
        """Test StreamChunk with frame data."""
        chunk = StreamChunk(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            chunk_type=ChunkType.FRAME,
            sequence_number=1,
            timestamp_ms=1702080001000,
            payload="YmFzZTY0X2VuY29kZWRfaW1hZ2U=",
            meta=FrameMeta(width=1920, height=1080, format="jpeg"),
        )
        assert chunk.chunk_type == ChunkType.FRAME
        assert isinstance(chunk.meta, FrameMeta)
        assert chunk.meta.width == 1920

    def test_stream_chunk_response(self):
        """Test StreamChunkResponse creation."""
        response = StreamChunkResponse(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            sequence_number=5,
            status=ChunkStatus.BUFFERED,
            message="Chunk received successfully",
        )
        assert response.status == ChunkStatus.BUFFERED
        assert response.sequence_number == 5


class TestTurnCompleteModels:
    """Test turn completion request and response models."""

    def test_turn_complete_request_minimal(self):
        """Test TurnCompleteRequest with minimal fields."""
        request = TurnCompleteRequest(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            turn_id="660e8400-e29b-41d4-a716-446655440001",
        )
        assert request.session_id == "550e8400-e29b-41d4-a716-446655440000"
        assert request.turn_id == "660e8400-e29b-41d4-a716-446655440001"
        assert request.cloud_offload is False

    def test_turn_complete_request_with_query(self):
        """Test TurnCompleteRequest with explicit query text."""
        request = TurnCompleteRequest(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            turn_id="660e8400-e29b-41d4-a716-446655440001",
            query_text="What am I looking at?",
            language="en",
            cloud_offload=True,
        )
        assert request.query_text == "What am I looking at?"
        assert request.language == "en"
        assert request.cloud_offload is True

    def test_turn_complete_request_invalid_language(self):
        """Test TurnCompleteRequest rejects invalid language code."""
        with pytest.raises(ValidationError) as exc_info:
            TurnCompleteRequest(
                session_id="550e8400-e29b-41d4-a716-446655440000",
                turn_id="660e8400-e29b-41d4-a716-446655440001",
                language="english",  # Must be ISO 639-1
            )
        assert "language" in str(exc_info.value)

    def test_action_valid(self):
        """Test Action model creation."""
        action = Action(
            action_type=ActionType.NAVIGATE,
            parameters={"destination": "Nearest Coffee Shop"},
            priority=Priority.HIGH,
        )
        assert action.action_type == ActionType.NAVIGATE
        assert action.parameters["destination"] == "Nearest Coffee Shop"
        assert action.priority == Priority.HIGH

    def test_turn_complete_response_with_actions(self):
        """Test TurnCompleteResponse with multiple actions."""
        response = TurnCompleteResponse(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            turn_id="660e8400-e29b-41d4-a716-446655440001",
            response="I can see a coffee shop. Would you like directions?",
            transcript="What am I looking at?",
            actions=[
                Action(
                    action_type=ActionType.NAVIGATE,
                    parameters={"destination": "Starbucks"},
                    priority=Priority.NORMAL,
                ),
                Action(
                    action_type=ActionType.SHOW_TEXT,
                    parameters={"text": "Coffee shop ahead"},
                    priority=Priority.LOW,
                ),
            ],
        )
        assert len(response.actions) == 2
        assert response.actions[0].action_type == ActionType.NAVIGATE
        assert response.transcript == "What am I looking at?"


class TestErrorResponse:
    """Test error response model."""

    def test_error_response_valid(self):
        """Test ErrorResponse creation."""
        error = ErrorResponse(
            error=ErrorCode.INVALID_SESSION,
            message="Session not found",
            details={"session_id": "550e8400-e29b-41d4-a716-446655440000"},
        )
        assert error.error == ErrorCode.INVALID_SESSION
        assert error.message == "Session not found"
        assert error.details["session_id"] == "550e8400-e29b-41d4-a716-446655440000"


class TestEnums:
    """Test enum definitions."""

    def test_chunk_type_enum(self):
        """Test ChunkType enum values."""
        assert ChunkType.AUDIO.value == "audio"
        assert ChunkType.FRAME.value == "frame"
        assert ChunkType.IMU.value == "imu"

    def test_action_type_enum(self):
        """Test ActionType enum has expected values."""
        assert ActionType.NAVIGATE in ActionType
        assert ActionType.SHOW_TEXT in ActionType
        assert ActionType.PLAY_AUDIO in ActionType

    def test_priority_enum(self):
        """Test Priority enum values."""
        assert Priority.LOW.value == "low"
        assert Priority.NORMAL.value == "normal"
        assert Priority.HIGH.value == "high"
        assert Priority.URGENT.value == "urgent"


class TestModelSerialization:
    """Test JSON serialization/deserialization."""

    def test_session_init_request_serialization(self):
        """Test SessionInitRequest can be serialized to JSON."""
        request = SessionInitRequest(
            device_id="rayban-meta-12345",
            client_version="1.0.0",
        )
        json_data = request.model_dump()
        assert json_data["device_id"] == "rayban-meta-12345"
        assert json_data["client_version"] == "1.0.0"

    def test_stream_chunk_deserialization(self):
        """Test StreamChunk can be deserialized from JSON."""
        json_data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "chunk_type": "audio",
            "sequence_number": 0,
            "timestamp_ms": 1702080000000,
            "payload": "YmFzZTY0X2VuY29kZWRfYXVkaW8=",
            "meta": {
                "sample_rate": 16000,
                "channels": 1,
                "format": "pcm_s16le",
            },
        }
        chunk = StreamChunk(**json_data)
        assert chunk.chunk_type == ChunkType.AUDIO
        assert chunk.meta.sample_rate == 16000

    def test_turn_complete_response_full_cycle(self):
        """Test TurnCompleteResponse serialization and deserialization."""
        response = TurnCompleteResponse(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            turn_id="660e8400-e29b-41d4-a716-446655440001",
            response="Test response",
            transcript="Test query",
            actions=[
                Action(
                    action_type=ActionType.NAVIGATE,
                    parameters={"destination": "Test"},
                )
            ],
        )
        
        # Serialize
        json_data = response.model_dump()
        
        # Deserialize
        restored = TurnCompleteResponse(**json_data)
        assert restored.session_id == response.session_id
        assert restored.turn_id == response.turn_id
        assert restored.response == response.response
        assert len(restored.actions) == 1
        assert restored.actions[0].action_type == ActionType.NAVIGATE

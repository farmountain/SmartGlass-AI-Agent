"""End-to-end tests for DAT-based SmartGlass interaction flow.

This test module validates the complete DAT (Device Access Toolkit) workflow
using the mock provider to simulate a Ray-Ban Meta glasses session without
requiring real hardware.

The tests cover:
- Session initialization with DAT protocol
- Streaming audio and frame chunks
- Turn completion and agent response generation
- Actions list structure and content validation

These tests run entirely offline and are suitable for CI/CD pipelines.

For manual smoke tests with real Ray-Ban Meta glasses, see:
    docs/meta_dat_implementation_plan.md - Section on "Testing with Real Hardware"
    
To run smoke tests with actual hardware:
    1. Connect your Ray-Ban Meta glasses via the Meta View app
    2. Ensure the Android app is paired with your backend server
    3. Set PROVIDER=meta in your environment
    4. Run the integration test suite with hardware flag:
       pytest tests/test_dat_end_to_end.py --hardware
    
Note: Hardware tests are not run in CI and require physical devices.
"""

# Ensure pytest plugins are loaded before other imports
pytest_plugins = ["tests.test_edge_runtime_server"]

import base64
import io
import sys
import types
from pathlib import Path
from typing import Optional
from uuid import uuid4, UUID

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from PIL import Image

from tests.test_edge_runtime_server import (
    FakeSmartGlassAgent,
    _encode_silent_wav,
    _encode_test_image,
)


def _encode_pcm_s16le(duration_seconds: float = 0.1, sample_rate: int = 16000) -> str:
    """Generate base64-encoded PCM s16le audio for DAT streaming."""
    samples = int(duration_seconds * sample_rate)
    # Create simple sine wave for more realistic audio
    t = np.linspace(0, duration_seconds, samples)
    audio_float = 0.1 * np.sin(2 * np.pi * 440 * t)  # 440 Hz tone at low volume
    # Convert to int16
    audio_int16 = (audio_float * 32767).astype(np.int16)
    return base64.b64encode(audio_int16.tobytes()).decode()


@pytest.fixture(name="dat_app")
def fixture_dat_app(monkeypatch):
    """Create FastAPI app configured for DAT testing with mock provider."""
    # Use the same pattern as test_edge_runtime_server.py
    src_root = Path(__file__).resolve().parent.parent / "src"
    src_package = types.ModuleType("src")
    src_package.__path__ = [str(src_root)]
    monkeypatch.setitem(sys.modules, "src", src_package)

    # Stub out heavy dependencies
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
        "privacy_flags": {
            "should_store_audio": lambda: False,
            "should_store_frames": lambda: False,
            "should_store_transcripts": lambda: False,
        },
    }.items():
        stub = types.ModuleType(module_name)
        for attr, value in attributes.items():
            setattr(stub, attr, value)
        stubs[module_name] = stub
        monkeypatch.setitem(sys.modules, module_name, stub)

    # Set environment for mock provider
    monkeypatch.setenv("PROVIDER", "mock")

    # Import and configure server
    from importlib import import_module, reload

    # The session_manager imports SmartGlassAgent locally in create_session()
    # so we don't need to patch the module itself - the stub in sys.modules will be used
    session_manager_module = import_module("src.edge_runtime.session_manager")

    server_module = import_module("src.edge_runtime.server")
    reload(server_module)

    metrics_module = import_module("src.utils.metrics")
    metrics_module.metrics.reset()

    return server_module.app


class TestDatSessionLifecycle:
    """Test complete DAT session workflow from init to completion."""

    def test_dat_session_init_returns_session_id(self, dat_app):
        """Test DAT session initialization returns valid session ID and capabilities."""
        client = TestClient(dat_app)

        # Initialize session with DAT protocol
        init_payload = {
            "device_id": "rayban-meta-test-12345",
            "client_version": "1.0.0",
            "capabilities": {
                "audio_streaming": True,
                "video_streaming": True,
                "imu_streaming": False,
            },
        }

        response = client.post("/dat/session", json=init_payload)
        assert response.status_code == 200

        result = response.json()
        assert "session_id" in result
        assert "server_version" in result
        assert "max_chunk_size_bytes" in result
        assert result["max_chunk_size_bytes"] > 0

        # Session ID should be a valid UUID format
        session_id = result["session_id"]
        try:
            UUID(session_id)  # Will raise ValueError if invalid
        except ValueError:
            pytest.fail(f"Session ID is not a valid UUID: {session_id}")

    def test_dat_session_init_with_privacy_metadata(self, dat_app):
        """Test DAT session initialization with privacy preferences in metadata."""
        client = TestClient(dat_app)

        init_payload = {
            "device_id": "rayban-meta-test-12345",
            "client_version": "1.0.0",
            "metadata": {
                "privacy_store_raw_audio": True,
                "privacy_store_raw_frames": False,
                "privacy_store_transcripts": True,
            },
        }

        response = client.post("/dat/session", json=init_payload)
        assert response.status_code == 200
        assert "session_id" in response.json()


class TestDatStreamingFlow:
    """Test DAT streaming endpoints with audio and frame chunks."""

    def test_stream_audio_chunks_are_buffered(self, dat_app):
        """Test audio chunks are accepted and buffered for later processing."""
        client = TestClient(dat_app)

        # Create session
        session_id = client.post(
            "/dat/session",
            json={"device_id": "test-device", "client_version": "1.0.0"},
        ).json()["session_id"]

        # Send audio chunk
        audio_chunk = {
            "session_id": session_id,
            "chunk_type": "audio",
            "sequence_number": 0,
            "timestamp_ms": 1702080000000,
            "payload": _encode_pcm_s16le(duration_seconds=0.2),
            "meta": {"sample_rate": 16000, "channels": 1, "format": "pcm_s16le"},
        }

        response = client.post("/dat/stream", json=audio_chunk)
        assert response.status_code == 200

        result = response.json()
        assert result["session_id"] == session_id
        assert result["sequence_number"] == 0
        assert result["status"] == "buffered"

    def test_stream_frame_chunks_are_buffered(self, dat_app):
        """Test video frame chunks are accepted and buffered for later processing."""
        client = TestClient(dat_app)

        # Create session
        session_id = client.post(
            "/dat/session",
            json={"device_id": "test-device", "client_version": "1.0.0"},
        ).json()["session_id"]

        # Send frame chunk
        frame_chunk = {
            "session_id": session_id,
            "chunk_type": "frame",
            "sequence_number": 0,
            "timestamp_ms": 1702080001000,
            "payload": _encode_test_image(size=64, color=(128, 128, 255)),
            "meta": {
                "width": 64,
                "height": 64,
                "format": "jpeg",
                "is_keyframe": True,
            },
        }

        response = client.post("/dat/stream", json=frame_chunk)
        assert response.status_code == 200

        result = response.json()
        assert result["session_id"] == session_id
        assert result["sequence_number"] == 0
        assert result["status"] == "buffered"

    def test_stream_multiple_chunks_in_sequence(self, dat_app):
        """Test streaming multiple audio and frame chunks with sequence numbers."""
        client = TestClient(dat_app)

        # Create session
        session_id = client.post(
            "/dat/session",
            json={"device_id": "test-device", "client_version": "1.0.0"},
        ).json()["session_id"]

        # Stream multiple audio chunks
        for i in range(3):
            audio_chunk = {
                "session_id": session_id,
                "chunk_type": "audio",
                "sequence_number": i,
                "timestamp_ms": 1702080000000 + (i * 100),
                "payload": _encode_pcm_s16le(duration_seconds=0.1),
                "meta": {"sample_rate": 16000, "channels": 1, "format": "pcm_s16le"},
            }
            response = client.post("/dat/stream", json=audio_chunk)
            assert response.status_code == 200
            assert response.json()["sequence_number"] == i

        # Stream a couple of frames
        for i in range(2):
            frame_chunk = {
                "session_id": session_id,
                "chunk_type": "frame",
                "sequence_number": 100 + i,  # Different sequence space
                "timestamp_ms": 1702080000000 + (i * 500),
                "payload": _encode_test_image(size=32),
                "meta": {"width": 32, "height": 32, "format": "jpeg"},
            }
            response = client.post("/dat/stream", json=frame_chunk)
            assert response.status_code == 200
            assert response.json()["sequence_number"] == 100 + i

    def test_stream_chunk_rejects_unknown_session(self, dat_app):
        """Test streaming to non-existent session returns 404."""
        client = TestClient(dat_app)

        audio_chunk = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",  # Doesn't exist
            "chunk_type": "audio",
            "sequence_number": 0,
            "timestamp_ms": 1702080000000,
            "payload": _encode_pcm_s16le(),
            "meta": {"sample_rate": 16000, "channels": 1, "format": "pcm_s16le"},
        }

        response = client.post("/dat/stream", json=audio_chunk)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDatTurnCompletion:
    """Test turn completion and agent response generation."""

    def test_turn_complete_returns_response_structure(self, dat_app):
        """Test turn completion returns expected response structure with transcript and actions."""
        client = TestClient(dat_app)

        # Create session
        session_id = client.post(
            "/dat/session",
            json={"device_id": "test-device", "client_version": "1.0.0"},
        ).json()["session_id"]

        # Stream some data first
        audio_chunk = {
            "session_id": session_id,
            "chunk_type": "audio",
            "sequence_number": 0,
            "timestamp_ms": 1702080000000,
            "payload": _encode_pcm_s16le(duration_seconds=0.2),
            "meta": {"sample_rate": 16000, "channels": 1, "format": "pcm_s16le"},
        }
        client.post("/dat/stream", json=audio_chunk)

        frame_chunk = {
            "session_id": session_id,
            "chunk_type": "frame",
            "sequence_number": 0,
            "timestamp_ms": 1702080000500,
            "payload": _encode_test_image(size=64),
            "meta": {"width": 64, "height": 64, "format": "jpeg"},
        }
        client.post("/dat/stream", json=frame_chunk)

        # Complete turn
        turn_request = {
            "session_id": session_id,
            "turn_id": str(uuid4()),
            "query_text": "What do I see?",
            "language": "en",
            "cloud_offload": False,
        }

        response = client.post("/dat/turn/complete", json=turn_request)
        assert response.status_code == 200

        result = response.json()
        
        # Assert response structure matches TurnCompleteResponse
        assert "session_id" in result
        assert result["session_id"] == session_id
        assert "turn_id" in result
        assert result["turn_id"] == turn_request["turn_id"]
        
        # Assert SmartGlassAgent returns a plausible response string
        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0
        
        # Assert transcript is present (either from query_text or ASR)
        assert "transcript" in result
        assert result["transcript"] is not None
        
        # Assert actions list has expected shape (list of dicts with action_type)
        assert "actions" in result
        assert isinstance(result["actions"], list)
        # Note: Current implementation returns empty actions list (TODO in server.py)
        # Once implemented, this should validate action structure:
        # for action in result["actions"]:
        #     assert "action_type" in action
        #     assert "parameters" in action
        #     assert "priority" in action
        #     assert "parameters" in action

    def test_turn_complete_without_streaming_data(self, dat_app):
        """Test turn completion works even without prior stream chunks (text-only query)."""
        client = TestClient(dat_app)

        # Create session
        session_id = client.post(
            "/dat/session",
            json={"device_id": "test-device", "client_version": "1.0.0"},
        ).json()["session_id"]

        # Complete turn without streaming any audio/frames
        turn_request = {
            "session_id": session_id,
            "turn_id": str(uuid4()),
            "query_text": "Hello, what's the weather?",
            "language": "en",
        }

        response = client.post("/dat/turn/complete", json=turn_request)
        assert response.status_code == 200

        result = response.json()
        assert result["session_id"] == session_id
        assert result["transcript"] == "Hello, what's the weather?"
        assert isinstance(result["actions"], list)

    def test_turn_complete_rejects_unknown_session(self, dat_app):
        """Test turn completion for non-existent session returns 404."""
        client = TestClient(dat_app)

        turn_request = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",  # Doesn't exist
            "turn_id": str(uuid4()),
        }

        response = client.post("/dat/turn/complete", json=turn_request)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDatEndToEndFlow:
    """Test complete end-to-end DAT workflow simulating real app usage."""

    def test_complete_multimodal_turn_flow(self, dat_app):
        """
        Test complete workflow: init -> stream audio -> stream frames -> complete turn.
        
        This simulates the typical usage pattern from the Android DatSmartGlassController:
        1. Initialize session with device capabilities
        2. Stream continuous audio chunks (simulating microphone)
        3. Stream keyframes at intervals (simulating camera)
        4. Finalize turn to get agent response with actions
        """
        client = TestClient(dat_app)

        # Step 1: Initialize DAT session
        init_response = client.post(
            "/dat/session",
            json={
                "device_id": "rayban-meta-e2e-test",
                "client_version": "1.0.0",
                "capabilities": {
                    "audio_streaming": True,
                    "video_streaming": True,
                    "imu_streaming": False,
                },
                "metadata": {
                    "privacy_store_raw_audio": True,
                    "privacy_store_raw_frames": True,
                    "privacy_store_transcripts": True,
                },
            },
        )
        assert init_response.status_code == 200
        session_id = init_response.json()["session_id"]

        # Step 2: Stream audio chunks (simulate ~400ms of audio)
        base_timestamp = 1702080000000
        audio_sequence = 0
        for i in range(4):  # 4 chunks of 100ms each
            audio_chunk = {
                "session_id": session_id,
                "chunk_type": "audio",
                "sequence_number": audio_sequence,
                "timestamp_ms": base_timestamp + (i * 100),
                "payload": _encode_pcm_s16le(duration_seconds=0.1),
                "meta": {
                    "sample_rate": 16000,
                    "channels": 1,
                    "format": "pcm_s16le",
                    "duration_ms": 100,
                },
            }
            response = client.post("/dat/stream", json=audio_chunk)
            assert response.status_code == 200
            assert response.json()["status"] == "buffered"
            audio_sequence += 1

        # Step 3: Stream frame chunks (simulate keyframes at 500ms intervals)
        frame_sequence = 0
        for i in range(2):  # 2 keyframes
            frame_chunk = {
                "session_id": session_id,
                "chunk_type": "frame",
                "sequence_number": frame_sequence,
                "timestamp_ms": base_timestamp + (i * 500),
                "payload": _encode_test_image(size=128, color=(100, 150, 200)),
                "meta": {
                    "width": 128,
                    "height": 128,
                    "format": "jpeg",
                    "quality": 85,
                    "is_keyframe": True,
                },
            }
            response = client.post("/dat/stream", json=frame_chunk)
            assert response.status_code == 200
            assert response.json()["status"] == "buffered"
            frame_sequence += 1

        # Step 4: Complete turn and get agent response
        turn_id = str(uuid4())
        turn_response = client.post(
            "/dat/turn/complete",
            json={
                "session_id": session_id,
                "turn_id": turn_id,
                "query_text": "What's in front of me?",
                "language": "en",
                "cloud_offload": False,
            },
        )
        assert turn_response.status_code == 200

        result = turn_response.json()
        
        # Validate complete response structure
        assert result["session_id"] == session_id
        assert result["turn_id"] == turn_id
        
        # SmartGlassAgent should return a plausible response
        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0
        
        # Transcript should be present
        assert result["transcript"] == "What's in front of me?"
        
        # Actions list should have expected shape
        assert isinstance(result["actions"], list)
        # Once fully implemented, validate action structure:
        # if len(result["actions"]) > 0:
        #     action = result["actions"][0]
        #     assert "action_type" in action
        #     assert action["action_type"] in ["NAVIGATE", "SHOW_TEXT", "PLAY_AUDIO", "TAKE_PHOTO"]
        #     assert "parameters" in action
        #     assert isinstance(action["parameters"], dict)

    def test_metrics_track_dat_operations(self, dat_app):
        """Test that DAT operations are tracked in metrics for monitoring."""
        client = TestClient(dat_app)

        # Create session and stream data
        session_id = client.post(
            "/dat/session",
            json={"device_id": "test-device", "client_version": "1.0.0"},
        ).json()["session_id"]

        # Stream audio chunk (should record dat_ingest_audio_latency_ms)
        audio_chunk = {
            "session_id": session_id,
            "chunk_type": "audio",
            "sequence_number": 0,
            "timestamp_ms": 1702080000000,
            "payload": _encode_pcm_s16le(),
            "meta": {"sample_rate": 16000, "channels": 1, "format": "pcm_s16le"},
        }
        client.post("/dat/stream", json=audio_chunk)

        # Stream frame chunk (should record dat_ingest_frame_latency_ms)
        frame_chunk = {
            "session_id": session_id,
            "chunk_type": "frame",
            "sequence_number": 0,
            "timestamp_ms": 1702080000000,
            "payload": _encode_test_image(),
            "meta": {"width": 64, "height": 64, "format": "jpeg"},
        }
        client.post("/dat/stream", json=frame_chunk)

        # Complete turn (should record end_to_end_turn_latency_ms)
        turn_request = {
            "session_id": session_id,
            "turn_id": str(uuid4()),
            "query_text": "Test query",
        }
        client.post("/dat/turn/complete", json=turn_request)

        # Check metrics summary includes DAT metrics
        metrics_response = client.get("/metrics/summary")
        assert metrics_response.status_code == 200

        metrics = metrics_response.json()
        assert "dat_metrics" in metrics

        dat_metrics = metrics["dat_metrics"]
        assert "ingest_audio" in dat_metrics
        assert "ingest_frame" in dat_metrics
        assert "end_to_end_turn" in dat_metrics

        # Verify we recorded at least one of each operation
        assert dat_metrics["ingest_audio"]["count"] >= 1
        assert dat_metrics["ingest_frame"]["count"] >= 1
        assert dat_metrics["end_to_end_turn"]["count"] >= 1


if __name__ == "__main__":
    # Allow running tests directly for quick validation
    pytest.main([__file__, "-v"])

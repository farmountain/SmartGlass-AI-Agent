"""Tests for MetaDatRegistry thread-safe buffer management."""

from __future__ import annotations

import threading
import time

import pytest

np = pytest.importorskip("numpy")

try:
    from drivers.providers.meta import MetaDatRegistry
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    pytest.skip("drivers.providers.meta not available", allow_module_level=True)


def test_registry_set_and_get_frame():
    """Registry stores and retrieves camera frames per session."""
    registry = MetaDatRegistry()
    
    session_id = "test-session-1"
    frame = np.random.randint(0, 255, (720, 960, 3), dtype=np.uint8)
    metadata = {"timestamp_ms": 1234567890, "device_id": "META-001"}
    
    registry.set_frame(session_id, frame, metadata)
    
    retrieved_frame, retrieved_meta = registry.get_latest_frame(session_id)
    
    assert retrieved_frame is not None
    assert np.array_equal(retrieved_frame, frame)
    assert retrieved_meta["timestamp_ms"] == 1234567890
    assert retrieved_meta["device_id"] == "META-001"


def test_registry_set_and_get_audio():
    """Registry stores and retrieves audio buffers per session."""
    registry = MetaDatRegistry()
    
    session_id = "test-session-2"
    audio = np.random.randn(400, 1).astype(np.float32)
    metadata = {"sample_rate_hz": 16000, "timestamp_ms": 9876543210}
    
    registry.set_audio(session_id, audio, metadata)
    
    retrieved_audio, retrieved_meta = registry.get_latest_audio_buffer(session_id)
    
    assert retrieved_audio is not None
    assert np.array_equal(retrieved_audio, audio)
    assert retrieved_meta["sample_rate_hz"] == 16000
    assert retrieved_meta["timestamp_ms"] == 9876543210


def test_registry_returns_none_for_missing_session():
    """Registry returns None for sessions with no data."""
    registry = MetaDatRegistry()
    
    frame, frame_meta = registry.get_latest_frame("nonexistent-session")
    audio, audio_meta = registry.get_latest_audio_buffer("nonexistent-session")
    
    assert frame is None
    assert frame_meta == {}
    assert audio is None
    assert audio_meta == {}


def test_registry_overwrites_previous_frame():
    """Registry keeps only the latest frame per session."""
    registry = MetaDatRegistry()
    
    session_id = "test-session-3"
    frame1 = np.zeros((720, 960, 3), dtype=np.uint8)
    frame2 = np.ones((720, 960, 3), dtype=np.uint8)
    
    registry.set_frame(session_id, frame1, {"timestamp_ms": 1000})
    registry.set_frame(session_id, frame2, {"timestamp_ms": 2000})
    
    retrieved_frame, retrieved_meta = registry.get_latest_frame(session_id)
    
    assert np.array_equal(retrieved_frame, frame2)
    assert retrieved_meta["timestamp_ms"] == 2000


def test_registry_overwrites_previous_audio():
    """Registry keeps only the latest audio buffer per session."""
    registry = MetaDatRegistry()
    
    session_id = "test-session-4"
    audio1 = np.zeros(400, dtype=np.float32)
    audio2 = np.ones(400, dtype=np.float32)
    
    registry.set_audio(session_id, audio1, {"timestamp_ms": 1000})
    registry.set_audio(session_id, audio2, {"timestamp_ms": 2000})
    
    retrieved_audio, retrieved_meta = registry.get_latest_audio_buffer(session_id)
    
    assert np.array_equal(retrieved_audio, audio2)
    assert retrieved_meta["timestamp_ms"] == 2000


def test_registry_clear_session():
    """Registry removes all data when clearing a session."""
    registry = MetaDatRegistry()
    
    session_id = "test-session-5"
    frame = np.random.randint(0, 255, (720, 960, 3), dtype=np.uint8)
    audio = np.random.randn(400).astype(np.float32)
    
    registry.set_frame(session_id, frame, {})
    registry.set_audio(session_id, audio, {})
    
    # Verify data exists
    assert registry.get_latest_frame(session_id)[0] is not None
    assert registry.get_latest_audio_buffer(session_id)[0] is not None
    
    # Clear session
    registry.clear_session(session_id)
    
    # Verify data removed
    assert registry.get_latest_frame(session_id)[0] is None
    assert registry.get_latest_audio_buffer(session_id)[0] is None


def test_registry_list_sessions():
    """Registry lists all sessions with buffered data."""
    registry = MetaDatRegistry()
    
    session1 = "session-1"
    session2 = "session-2"
    session3 = "session-3"
    
    frame = np.zeros((720, 960, 3), dtype=np.uint8)
    audio = np.zeros(400, dtype=np.float32)
    
    registry.set_frame(session1, frame, {})
    registry.set_audio(session2, audio, {})
    registry.set_frame(session3, frame, {})
    registry.set_audio(session3, audio, {})
    
    sessions = registry.list_sessions()
    
    assert len(sessions) == 3
    assert session1 in sessions
    assert session2 in sessions
    assert session3 in sessions


def test_registry_metadata_optional():
    """Registry works with None metadata."""
    registry = MetaDatRegistry()
    
    session_id = "test-session-6"
    frame = np.zeros((720, 960, 3), dtype=np.uint8)
    audio = np.zeros(400, dtype=np.float32)
    
    registry.set_frame(session_id, frame, None)
    registry.set_audio(session_id, audio, None)
    
    retrieved_frame, frame_meta = registry.get_latest_frame(session_id)
    retrieved_audio, audio_meta = registry.get_latest_audio_buffer(session_id)
    
    assert retrieved_frame is not None
    assert frame_meta == {}
    assert retrieved_audio is not None
    assert audio_meta == {}


def test_registry_thread_safety():
    """Registry is thread-safe for concurrent access."""
    registry = MetaDatRegistry()
    session_id = "test-session-7"
    
    # Number of threads and operations
    num_threads = 10
    ops_per_thread = 50
    
    errors = []
    
    def writer_thread(thread_id: int):
        try:
            for i in range(ops_per_thread):
                frame = np.full((720, 960, 3), thread_id, dtype=np.uint8)
                metadata = {"thread_id": thread_id, "op": i}
                registry.set_frame(session_id, frame, metadata)
                time.sleep(0.001)  # Small delay to encourage interleaving
        except Exception as e:
            errors.append(e)
    
    def reader_thread():
        try:
            for _ in range(ops_per_thread):
                frame, metadata = registry.get_latest_frame(session_id)
                if frame is not None:
                    # Verify frame consistency - all values should be same
                    assert np.all(frame == frame[0, 0, 0])
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)
    
    # Start writer threads
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=writer_thread, args=(i,))
        threads.append(t)
        t.start()
    
    # Start reader threads
    for _ in range(num_threads):
        t = threading.Thread(target=reader_thread)
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Check no errors occurred
    assert len(errors) == 0, f"Errors during concurrent access: {errors}"
    
    # Verify final state is valid
    final_frame, final_meta = registry.get_latest_frame(session_id)
    assert final_frame is not None
    assert final_frame.shape == (720, 960, 3)


def test_registry_multiple_sessions_isolated():
    """Registry keeps data isolated between different sessions."""
    registry = MetaDatRegistry()
    
    session1 = "session-a"
    session2 = "session-b"
    
    frame1 = np.zeros((720, 960, 3), dtype=np.uint8)
    frame2 = np.ones((720, 960, 3), dtype=np.uint8)
    
    audio1 = np.zeros(400, dtype=np.float32)
    audio2 = np.ones(400, dtype=np.float32)
    
    registry.set_frame(session1, frame1, {"session": "a"})
    registry.set_audio(session1, audio1, {"session": "a"})
    
    registry.set_frame(session2, frame2, {"session": "b"})
    registry.set_audio(session2, audio2, {"session": "b"})
    
    # Verify session1 data
    retrieved_frame1, meta1 = registry.get_latest_frame(session1)
    retrieved_audio1, _ = registry.get_latest_audio_buffer(session1)
    assert np.array_equal(retrieved_frame1, frame1)
    assert np.array_equal(retrieved_audio1, audio1)
    assert meta1["session"] == "a"
    
    # Verify session2 data
    retrieved_frame2, meta2 = registry.get_latest_frame(session2)
    retrieved_audio2, _ = registry.get_latest_audio_buffer(session2)
    assert np.array_equal(retrieved_frame2, frame2)
    assert np.array_equal(retrieved_audio2, audio2)
    assert meta2["session"] == "b"

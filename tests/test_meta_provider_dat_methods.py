"""Tests for MetaRayBanProvider DAT integration methods."""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

try:
    from drivers.providers.meta import MetaRayBanProvider, _DAT_REGISTRY
    import drivers.providers.meta as meta_module
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    pytest.skip("drivers.providers.meta not available", allow_module_level=True)


@pytest.fixture(autouse=True)
def _force_mock_meta_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the Meta provider operates in mock mode for hermetic tests."""
    monkeypatch.setattr(meta_module, "_META_SDK_AVAILABLE", False)
    monkeypatch.setattr(meta_module, "_META_SDK", None)


@pytest.fixture
def clean_registry():
    """Clear the global DAT registry before and after each test."""
    # Clear before test
    for session_id in _DAT_REGISTRY.list_sessions():
        _DAT_REGISTRY.clear_session(session_id)
    
    yield
    
    # Clear after test
    for session_id in _DAT_REGISTRY.list_sessions():
        _DAT_REGISTRY.clear_session(session_id)


def test_provider_has_display_returns_false():
    """Meta Ray-Ban glasses do not have a display."""
    provider = MetaRayBanProvider()
    assert provider.has_display() is False


def test_provider_get_latest_frame_with_no_session():
    """get_latest_frame returns None when no session_id is set."""
    provider = MetaRayBanProvider()
    frame = provider.get_latest_frame()
    assert frame is None


def test_provider_get_latest_audio_buffer_with_no_session():
    """get_latest_audio_buffer returns None when no session_id is set."""
    provider = MetaRayBanProvider()
    audio = provider.get_latest_audio_buffer()
    assert audio is None


def test_provider_get_latest_frame_with_session(clean_registry):
    """get_latest_frame retrieves frame from registry when session_id is set."""
    session_id = "test-session-frame"
    provider = MetaRayBanProvider(session_id=session_id)
    
    # No frame yet
    frame = provider.get_latest_frame()
    assert frame is None
    
    # Add frame to registry
    test_frame = np.random.randint(0, 255, (720, 960, 3), dtype=np.uint8)
    _DAT_REGISTRY.set_frame(session_id, test_frame, {"timestamp_ms": 12345})
    
    # Retrieve frame
    frame = provider.get_latest_frame()
    assert frame is not None
    assert np.array_equal(frame, test_frame)


def test_provider_get_latest_audio_buffer_with_session(clean_registry):
    """get_latest_audio_buffer retrieves audio from registry when session_id is set."""
    session_id = "test-session-audio"
    provider = MetaRayBanProvider(session_id=session_id)
    
    # No audio yet
    audio = provider.get_latest_audio_buffer()
    assert audio is None
    
    # Add audio to registry
    test_audio = np.random.randn(400, 1).astype(np.float32)
    _DAT_REGISTRY.set_audio(session_id, test_audio, {"sample_rate_hz": 16000})
    
    # Retrieve audio
    audio = provider.get_latest_audio_buffer()
    assert audio is not None
    assert np.array_equal(audio, test_audio)


def test_provider_multiple_sessions_isolated(clean_registry):
    """Different provider instances with different sessions access independent data."""
    session_a = "session-a"
    session_b = "session-b"
    
    provider_a = MetaRayBanProvider(session_id=session_a)
    provider_b = MetaRayBanProvider(session_id=session_b)
    
    # Add different frames to each session
    frame_a = np.zeros((720, 960, 3), dtype=np.uint8)
    frame_b = np.ones((720, 960, 3), dtype=np.uint8)
    
    _DAT_REGISTRY.set_frame(session_a, frame_a, {})
    _DAT_REGISTRY.set_frame(session_b, frame_b, {})
    
    # Each provider gets its own session's frame
    retrieved_a = provider_a.get_latest_frame()
    retrieved_b = provider_b.get_latest_frame()
    
    assert np.array_equal(retrieved_a, frame_a)
    assert np.array_equal(retrieved_b, frame_b)
    assert not np.array_equal(retrieved_a, retrieved_b)


def test_provider_backward_compatibility():
    """Provider still works in legacy mode without session_id."""
    provider = MetaRayBanProvider(
        device_id="TEST-DEVICE",
        transport="mock",
        camera_resolution=(720, 960),
        microphone_sample_rate_hz=16000,
    )
    
    # These should work with mock data
    camera = provider.open_video_stream()
    microphone = provider.open_audio_stream()
    
    assert camera is not None
    assert microphone is not None
    
    # Should be able to get frames from mock
    frame_iter = provider.iter_frames()
    first_frame_dict = next(frame_iter)
    
    # Extract frame from dict
    if isinstance(first_frame_dict, dict):
        first_frame = first_frame_dict.get("frame")
    else:
        first_frame = first_frame_dict
    
    assert first_frame is not None
    first_frame_array = np.asarray(first_frame)
    assert first_frame_array.ndim >= 2


def test_provider_session_id_parameter_stored():
    """Provider stores session_id parameter."""
    session_id = "test-session-storage"
    provider = MetaRayBanProvider(session_id=session_id)
    
    assert provider._session_id == session_id


def test_provider_get_latest_frame_updates_with_registry(clean_registry):
    """Provider reflects updates to the registry."""
    session_id = "test-session-updates"
    provider = MetaRayBanProvider(session_id=session_id)
    
    # Set initial frame
    frame1 = np.zeros((720, 960, 3), dtype=np.uint8)
    _DAT_REGISTRY.set_frame(session_id, frame1, {"timestamp_ms": 1000})
    
    retrieved1 = provider.get_latest_frame()
    assert np.array_equal(retrieved1, frame1)
    
    # Update with new frame
    frame2 = np.ones((720, 960, 3), dtype=np.uint8)
    _DAT_REGISTRY.set_frame(session_id, frame2, {"timestamp_ms": 2000})
    
    retrieved2 = provider.get_latest_frame()
    assert np.array_equal(retrieved2, frame2)
    assert not np.array_equal(retrieved2, frame1)


def test_provider_integration_with_existing_methods(clean_registry):
    """New DAT methods work alongside existing provider methods."""
    session_id = "test-session-integration"
    provider = MetaRayBanProvider(
        session_id=session_id,
        device_id="TEST-001",
        transport="mock",
    )
    
    # Test new methods
    assert provider.has_display() is False
    assert provider.get_latest_frame() is None
    assert provider.get_latest_audio_buffer() is None
    
    # Test existing methods still work
    assert provider.open_video_stream() is not None
    assert provider.open_audio_stream() is not None
    assert provider.get_audio_out() is not None
    assert provider.get_overlay() is not None
    assert provider.get_haptics() is not None
    assert provider.get_permissions() is not None

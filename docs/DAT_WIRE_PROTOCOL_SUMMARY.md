# DAT Wire Protocol Implementation Summary

## Overview

This implementation provides a complete, strongly-typed wire protocol for communication between the Android DAT client and the SmartGlass-AI-Agent Python backend. The protocol enables robust streaming of multimodal data (audio, video, IMU sensors) from Ray-Ban Meta glasses to the AI backend.

## What Was Implemented

### 1. JSON Schema Definition (`schemas/dat_wire_protocol.json`)

A comprehensive JSON Schema document defining 8 message types:

- **SessionInitRequest/Response**: Session initialization with device info and capabilities
- **StreamChunk**: Unified envelope for audio/frame/IMU data chunks
- **StreamChunkResponse**: Acknowledgment for received chunks
- **TurnCompleteRequest/Response**: Turn finalization with agent response and actions
- **Action**: Agent-generated actions for client execution
- **ErrorResponse**: Standardized error handling

Key features:
- Strict validation rules (UUID patterns, semantic versioning, ISO 639-1 language codes)
- Extensible metadata fields
- Support for multiple audio formats (PCM, Opus) and video formats (JPEG, PNG, YUV)
- IMU sensor support (accelerometer, gyroscope, magnetometer)

### 2. Python Pydantic Models (`src/wire/dat_protocol.py`)

Type-safe Pydantic v2 models with validation:

- **Enums**: `ChunkType`, `ActionType`, `Priority`, `ChunkStatus`, `ErrorCode`
- **Request/Response Models**: All JSON Schema types as Pydantic BaseModel classes
- **Metadata Models**: `AudioMeta`, `FrameMeta`, `ImuMeta`, `ResponseMetadata`
- **Field Validators**: Custom validators for sample rates, formats, sensor types

Features:
- Automatic JSON serialization/deserialization via Pydantic
- Field-level validation with descriptive error messages
- Support for Union types (meta field can be AudioMeta, FrameMeta, or ImuMeta)
- FastAPI-ready (automatic OpenAPI/Swagger documentation)

### 3. FastAPI Endpoints (`src/edge_runtime/server.py`)

Three new HTTP endpoints integrated into the existing FastAPI server:

#### POST /dat/session
- **Purpose**: Initialize a new DAT streaming session
- **Input**: `SessionInitRequest` (device_id, client_version, capabilities)
- **Output**: `SessionInitResponse` (session_id, server_version)
- **Implementation**: Creates session via `SessionManager`, returns UUID
- **Status Codes**: 200 (success), 401 (unauthorized)

#### POST /dat/stream
- **Purpose**: Receive and buffer stream chunks (audio/frame/IMU)
- **Input**: `StreamChunk` (session_id, chunk_type, payload, meta)
- **Output**: `StreamChunkResponse` (status, sequence_number)
- **Implementation**:
  - Validates session exists
  - Decodes base64 payload
  - Converts audio (PCM → float32 numpy array)
  - Decodes images (JPEG/PNG → PIL Image → numpy array)
  - Stores in `_DAT_REGISTRY` with metadata
- **Status Codes**: 200 (success), 404 (session not found), 413 (buffer overflow)

#### POST /dat/turn/complete
- **Purpose**: Finalize turn and receive agent response
- **Input**: `TurnCompleteRequest` (session_id, turn_id, query_text, language)
- **Output**: `TurnCompleteResponse` (response, transcript, actions)
- **Implementation**: Currently returns placeholder response with TODO markers for:
  - Processing buffered audio/frames from `_DAT_REGISTRY`
  - Running multimodal agent query
  - Extracting actions from agent response
  - Clearing buffers after processing
- **Status Codes**: 200 (success), 404 (session not found)

### 4. Comprehensive Test Suite (`tests/test_dat_wire_protocol.py`)

27 tests covering:
- **Session Initialization**: Valid/invalid requests, version validation, UUID format
- **Stream Chunks**: Audio/Frame/IMU metadata validation, invalid formats
- **Turn Completion**: Request validation, language codes, action creation
- **Error Handling**: Error response creation with error codes
- **Serialization**: JSON round-trip testing for all models
- **Enums**: Enum value validation

All tests pass with proper importlib-based loading to avoid heavy dependencies.

### 5. Documentation

#### `docs/dat_wire_protocol.md`
- Protocol flow diagram
- Message type specifications with JSON examples
- Field descriptions and validation rules
- API endpoint documentation
- Kotlin integration mapping
- Best practices guide

#### `docs/dat_wire_protocol_android_examples.md`
- Complete Kotlin data class definitions
- Full `DatWireProtocolClient` implementation with OkHttp + Moshi
- Usage examples and integration patterns
- Integration with `DatSmartGlassController`
- Testing examples with coroutines

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Android Client (Kotlin)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ DatSmartGlassController                                 │   │
│  │  • Manages Meta Ray-Ban glasses connection              │   │
│  │  • Streams audio/video from DAT SDK                     │   │
│  └────────────────┬────────────────────────────────────────┘   │
│                   │                                             │
│  ┌────────────────▼────────────────────────────────────────┐   │
│  │ DatWireProtocolClient                                   │   │
│  │  • SessionInit, StreamChunk, TurnComplete requests      │   │
│  │  • OkHttp + Moshi for HTTP/JSON                         │   │
│  │  • Base64 encoding for binary payloads                  │   │
│  └────────────────┬────────────────────────────────────────┘   │
└───────────────────┼─────────────────────────────────────────────┘
                    │
                    │ HTTP (JSON over POST)
                    │
┌───────────────────▼─────────────────────────────────────────────┐
│  Python Backend (FastAPI)                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ FastAPI Endpoints (src/edge_runtime/server.py)          │   │
│  │  • POST /dat/session → SessionInitResponse              │   │
│  │  • POST /dat/stream → StreamChunkResponse               │   │
│  │  • POST /dat/turn/complete → TurnCompleteResponse       │   │
│  └────────────────┬────────────────────────────────────────┘   │
│                   │                                             │
│  ┌────────────────▼────────────────────────────────────────┐   │
│  │ Pydantic Models (src/wire/dat_protocol.py)             │   │
│  │  • Request/Response validation                          │   │
│  │  • JSON serialization/deserialization                   │   │
│  │  • Field-level validation                               │   │
│  └────────────────┬────────────────────────────────────────┘   │
│                   │                                             │
│  ┌────────────────▼────────────────────────────────────────┐   │
│  │ _DAT_REGISTRY (drivers/providers/meta.py)               │   │
│  │  • Per-session frame/audio buffer storage               │   │
│  │  • Thread-safe with Lock                                │   │
│  └────────────────┬────────────────────────────────────────┘   │
│                   │                                             │
│  ┌────────────────▼────────────────────────────────────────┐   │
│  │ SessionManager + SmartGlassAgent                        │   │
│  │  • Process multimodal queries                           │   │
│  │  • Generate agent responses + actions                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Design Decisions

### 1. Base64 Encoding for Binary Data
- **Rationale**: JSON-compatible, widely supported, no escaping issues
- **Trade-off**: 33% size increase, but acceptable for 1MB chunks
- **Alternative Considered**: Multipart form data (rejected for complexity)

### 2. Separate Chunk Type Metadata Models
- **Rationale**: Type-safe metadata validation per chunk type
- **Benefit**: Prevents mixing incompatible metadata (e.g., sample_rate on frame)
- **Implementation**: Union type with validators

### 3. Sequence Numbers + Timestamps
- **Rationale**: Enables debugging, out-of-order detection, replay protection
- **Usage**: Client maintains counter, server validates monotonic increase
- **Benefit**: Easy troubleshooting of streaming issues

### 4. Turn-Based Processing
- **Rationale**: Aligns with conversational AI pattern (user turn → agent response)
- **Benefit**: Clear boundaries for buffering, processing, and response
- **Alternative Considered**: Streaming responses (planned for future)

### 5. TODO Markers for Business Logic
- **Rationale**: Protocol infrastructure complete, agent integration needs domain expertise
- **Benefit**: Clear separation of concerns, enables parallel development
- **Next Steps**: Implement full turn completion logic with multimodal query

## Extensibility

The protocol is designed to be extended without breaking changes:

### Adding New Sensor Types
1. Add new `chunk_type` enum value (e.g., "gps", "compass")
2. Define new metadata model (e.g., `GpsMeta`)
3. Update `StreamChunk.meta` Union type
4. Implement handler in `/dat/stream` endpoint
5. Update JSON schema and documentation

### Adding New Action Types
1. Add to `ActionType` enum
2. Define parameters schema in documentation
3. Implement handler in Android client
4. Update JSON schema

### Adding New Capabilities
1. Add to `ClientCapabilities` or `ServerCapabilities`
2. Negotiate during session init
3. Update both client and server to respect new capability

## Integration Points

### With Existing Systems

1. **MetaDatRegistry** (`drivers/providers/meta.py`)
   - Wire protocol stores chunks in registry
   - Provider reads from registry for agent processing

2. **SessionManager** (`src/edge_runtime/session_manager.py`)
   - Wire protocol creates sessions via manager
   - Manager tracks session lifecycle and buffers

3. **SmartGlassAgent** (`src/smartglass_agent.py`)
   - Turn completion calls agent's multimodal query method
   - Agent processes audio + vision + context

### With Android SDK

1. **DatSmartGlassController** (`sdk-android/`)
   - Bridges Meta DAT SDK and wire protocol client
   - Manages streaming lifecycle (start → stream → finalize → stop)

2. **ActionExecutor** (`sdk-android/`)
   - Executes actions from `TurnCompleteResponse`
   - Action types compatible between wire protocol and executor

## Future Work

### Immediate (TODO in code)
- [ ] Implement full turn completion logic in `/dat/turn/complete`
- [ ] Integrate buffered chunks with `SessionManager.run_query()`
- [ ] Extract actions from agent response
- [ ] Clear buffers after processing
- [ ] Add IMU data handling

### Short-term
- [ ] Add streaming transcription capability
- [ ] Implement WebSocket endpoint for real-time responses
- [ ] Add session expiration and cleanup
- [ ] Add rate limiting per session
- [ ] Add metrics (chunk counts, latency tracking)

### Long-term
- [ ] End-to-end encryption for payloads
- [ ] Compression for large chunks (gzip, brotli)
- [ ] Video codec negotiation (H.264, VP9)
- [ ] P2P mode for local processing
- [ ] Multi-device session support

## Testing

### Running Tests

```bash
# Run wire protocol tests
cd /home/runner/work/SmartGlass-AI-Agent/SmartGlass-AI-Agent
python -m pytest tests/test_dat_wire_protocol.py -v

# Expected: 27 tests passed
```

### Test Coverage
- ✅ Request validation (required fields, formats, patterns)
- ✅ Response serialization (JSON round-trip)
- ✅ Metadata validation (sample rates, formats, sensor types)
- ✅ Enum values and types
- ✅ Error handling and error codes
- ⏸️ Endpoint integration tests (requires full stack)
- ⏸️ End-to-end tests with Android client (requires mobile setup)

## Files Modified/Created

### Created
- `schemas/dat_wire_protocol.json` - JSON Schema definition (12KB, 8 message types)
- `src/wire/__init__.py` - Module exports
- `src/wire/dat_protocol.py` - Pydantic models (11KB, 400+ lines)
- `tests/test_dat_wire_protocol.py` - Test suite (13KB, 27 tests)
- `docs/dat_wire_protocol.md` - Protocol documentation (11KB)
- `docs/dat_wire_protocol_android_examples.md` - Android examples (16KB)
- `docs/DAT_WIRE_PROTOCOL_SUMMARY.md` - This summary

### Modified
- `src/edge_runtime/server.py` - Added 3 DAT endpoints (+250 lines)
- `requirements.txt` - Added `pydantic>=2.0.0`

## Dependencies

### Python
- `pydantic>=2.0.0` - Type-safe models with validation
- `fastapi` (existing) - HTTP endpoints
- `numpy` (existing) - Audio/image data processing
- `soundfile` (existing) - Audio decoding
- `Pillow` (existing) - Image decoding

### Android (for client)
- `okhttp3:okhttp:4.12.0` - HTTP client
- `moshi:moshi:1.15.0` - JSON serialization
- `moshi:moshi-kotlin:1.15.0` - Kotlin support

## Success Criteria

✅ **Complete**: Wire protocol schema defined with 8 message types  
✅ **Complete**: Python Pydantic models with validation  
✅ **Complete**: FastAPI endpoints integrated into server  
✅ **Complete**: Comprehensive test suite (27 tests passing)  
✅ **Complete**: Documentation with examples  
✅ **Complete**: Android-friendly design (Kotlin data classes map cleanly)  
✅ **Complete**: Extensible for future sensor types  
⏸️ **Partial**: Turn completion business logic (TODO markers in place)  

## References

- JSON Schema Spec: https://json-schema.org/draft-07/schema
- Pydantic v2 Docs: https://docs.pydantic.dev/2.0/
- FastAPI Docs: https://fastapi.tiangolo.com/
- Meta DAT SDK: (see `docs/meta_dat_integration.md`)
- Moshi JSON Library: https://github.com/square/moshi
- OkHttp: https://square.github.io/okhttp/

---

**Implementation Date**: December 9, 2024  
**Status**: ✅ Complete (except turn completion business logic)  
**Tests**: ✅ 27/27 passing  
**Documentation**: ✅ Complete

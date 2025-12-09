# DAT Wire Protocol Documentation

## Overview

This document describes the wire protocol for communication between the Android DAT client and the SmartGlass-AI-Agent Python backend. The protocol is designed for streaming multimodal data (audio, video, IMU sensors) from Ray-Ban Meta glasses to the backend for processing by the AI agent.

## Design Principles

1. **Strongly Typed**: All messages use Pydantic models with validation
2. **Extensible**: Easy to add new sensor types or metadata fields
3. **Android-Friendly**: Schema maps cleanly to Kotlin data classes
4. **Debuggable**: Sequence numbers and timestamps for troubleshooting
5. **Efficient**: Base64 encoding for binary payloads with chunking support

## Protocol Flow

```
┌─────────────────┐                              ┌──────────────────────┐
│  Android Client │                              │  Python Backend      │
│  (DAT SDK)      │                              │  (FastAPI Server)    │
└────────┬────────┘                              └──────────┬───────────┘
         │                                                   │
         │  1. POST /dat/session                            │
         │     SessionInitRequest                           │
         ├──────────────────────────────────────────────────>│
         │                                                   │
         │                    SessionInitResponse            │
         │                    (session_id)                   │
         │<──────────────────────────────────────────────────┤
         │                                                   │
         │  2. POST /dat/stream (multiple times)            │
         │     StreamChunk (audio/frame/imu)                │
         ├──────────────────────────────────────────────────>│
         │                    StreamChunkResponse            │
         │<──────────────────────────────────────────────────┤
         │                                                   │
         │  3. POST /dat/turn/complete                      │
         │     TurnCompleteRequest                          │
         ├──────────────────────────────────────────────────>│
         │                                                   │
         │                    TurnCompleteResponse           │
         │                    (response + actions)           │
         │<──────────────────────────────────────────────────┤
         │                                                   │
```

## Message Types

### 1. Session Initialization

#### SessionInitRequest

Initializes a new streaming session.

```json
{
  "device_id": "rayban-meta-12345",
  "client_version": "1.0.0",
  "capabilities": {
    "audio_streaming": true,
    "video_streaming": true,
    "imu_streaming": false
  },
  "metadata": {
    "device_model": "Ray-Ban Meta Wayfarer",
    "os_version": "Android 14"
  }
}
```

**Fields:**
- `device_id` (required): Unique identifier for the glasses device
- `client_version` (required): Semantic version of Android client (e.g., "1.0.0")
- `capabilities` (optional): Client capabilities (defaults shown above)
- `metadata` (optional): Additional device/client metadata

#### SessionInitResponse

Returns the session identifier and server capabilities.

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "server_version": "0.1.0",
  "max_chunk_size_bytes": 1048576,
  "capabilities": {
    "multimodal_queries": true,
    "streaming_transcription": false
  }
}
```

**Fields:**
- `session_id` (required): UUID to use in subsequent requests
- `server_version` (required): Backend version
- `max_chunk_size_bytes` (optional): Maximum payload size (default 1MB)
- `capabilities` (optional): Server capabilities

### 2. Stream Chunks

#### StreamChunk

Envelope for streaming data chunks.

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_type": "audio",
  "sequence_number": 0,
  "timestamp_ms": 1702080000000,
  "payload": "YmFzZTY0X2VuY29kZWRfYXVkaW8=",
  "meta": {
    "sample_rate": 16000,
    "channels": 1,
    "format": "pcm_s16le",
    "duration_ms": 100
  }
}
```

**Fields:**
- `session_id` (required): Session UUID from SessionInitResponse
- `chunk_type` (required): One of "audio", "frame", "imu"
- `sequence_number` (required): Monotonically increasing integer
- `timestamp_ms` (required): Client-side timestamp (milliseconds since epoch)
- `payload` (required): Base64-encoded binary data
- `meta` (optional): Type-specific metadata (see below)

#### Audio Metadata

For `chunk_type: "audio"`:

```json
{
  "sample_rate": 16000,
  "channels": 1,
  "format": "pcm_s16le",
  "duration_ms": 100
}
```

**Supported sample rates:** 8000, 16000, 22050, 44100, 48000 Hz  
**Supported channels:** 1 (mono), 2 (stereo)  
**Supported formats:** `pcm_s16le`, `pcm_f32le`, `opus`

#### Frame Metadata

For `chunk_type: "frame"`:

```json
{
  "width": 1920,
  "height": 1080,
  "format": "jpeg",
  "quality": 85,
  "is_keyframe": true
}
```

**Supported formats:** `jpeg`, `png`, `yuv420`, `i420`  
**Quality:** 0-100 for JPEG compression

#### IMU Metadata

For `chunk_type: "imu"`:

```json
{
  "sensor_type": "accelerometer",
  "sample_count": 10
}
```

**Supported sensor types:** `accelerometer`, `gyroscope`, `magnetometer`

#### StreamChunkResponse

Acknowledges receipt of a chunk.

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "sequence_number": 0,
  "status": "buffered",
  "message": "Chunk buffered successfully"
}
```

**Status values:**
- `accepted`: Chunk processed immediately
- `buffered`: Chunk stored for later processing
- `error`: Processing failed (see message)

### 3. Turn Completion

#### TurnCompleteRequest

Finalizes a turn and requests agent response.

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_id": "660e8400-e29b-41d4-a716-446655440001",
  "query_text": "What am I looking at?",
  "language": "en",
  "cloud_offload": false,
  "metadata": {
    "location": "37.7749,-122.4194"
  }
}
```

**Fields:**
- `session_id` (required): Session UUID
- `turn_id` (required): Client-generated UUID for this turn
- `query_text` (optional): Explicit text query (if not using audio)
- `language` (optional): ISO 639-1 language code (e.g., "en", "es-MX")
- `cloud_offload` (optional): Whether to use cloud processing (may redact PII)
- `metadata` (optional): Additional turn metadata

#### TurnCompleteResponse

Returns agent response and actions.

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_id": "660e8400-e29b-41d4-a716-446655440001",
  "response": "I can see a coffee shop ahead. Would you like directions?",
  "transcript": "What am I looking at?",
  "actions": [
    {
      "action_type": "NAVIGATE",
      "parameters": {
        "destination": "Starbucks Coffee",
        "distance_meters": 150
      },
      "priority": "normal"
    }
  ],
  "metadata": {
    "processing_time_ms": 342,
    "model_version": "smartglass-v0.1.0"
  }
}
```

**Fields:**
- `session_id` (required): Session UUID
- `turn_id` (required): Turn UUID from request
- `response` (required): Natural language response from agent
- `transcript` (optional): Transcribed audio query
- `actions` (optional): List of actions for client to execute
- `metadata` (optional): Processing metadata

#### Action Types

**Available action types:**
- `NAVIGATE`: Show navigation directions
- `SHOW_TEXT`: Display text overlay
- `PLAY_AUDIO`: Play audio feedback
- `SHOW_IMAGE`: Display an image
- `VIBRATE`: Trigger haptic feedback
- `NOTIFICATION`: Show a notification
- `OPEN_APP`: Launch an application
- `SEARCH`: Perform a search query
- `CUSTOM`: Custom action with arbitrary parameters

**Priority levels:** `low`, `normal`, `high`, `urgent`

### 4. Error Responses

When an error occurs, the server returns an ErrorResponse:

```json
{
  "error": "INVALID_SESSION",
  "message": "Session not found: 550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-12-09T03:00:00Z"
  }
}
```

**Error codes:**
- `INVALID_SESSION`: Session ID not found or expired
- `INVALID_CHUNK`: Malformed chunk data
- `BUFFER_OVERFLOW`: Too much data buffered
- `INVALID_REQUEST`: Request validation failed
- `INTERNAL_ERROR`: Server-side error
- `UNAUTHORIZED`: Authentication failed

## API Endpoints

### POST /dat/session

Initialize a new DAT streaming session.

**Request:** `SessionInitRequest`  
**Response:** `SessionInitResponse`  
**Status Codes:** 200 (success), 401 (unauthorized)

### POST /dat/stream

Submit a stream chunk (audio/frame/IMU).

**Request:** `StreamChunk`  
**Response:** `StreamChunkResponse`  
**Status Codes:** 200 (success), 404 (session not found), 413 (buffer overflow)

### POST /dat/turn/complete

Finalize turn and receive agent response.

**Request:** `TurnCompleteRequest`  
**Response:** `TurnCompleteResponse`  
**Status Codes:** 200 (success), 404 (session not found)

## Kotlin Integration Example

```kotlin
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class SessionInitRequest(
    @Json(name = "device_id") val deviceId: String,
    @Json(name = "client_version") val clientVersion: String,
    val capabilities: ClientCapabilities? = null,
    val metadata: Map<String, Any>? = null
)

@JsonClass(generateAdapter = true)
data class ClientCapabilities(
    @Json(name = "audio_streaming") val audioStreaming: Boolean = true,
    @Json(name = "video_streaming") val videoStreaming: Boolean = true,
    @Json(name = "imu_streaming") val imuStreaming: Boolean = false
)

@JsonClass(generateAdapter = true)
data class StreamChunk(
    @Json(name = "session_id") val sessionId: String,
    @Json(name = "chunk_type") val chunkType: String, // "audio", "frame", "imu"
    @Json(name = "sequence_number") val sequenceNumber: Int,
    @Json(name = "timestamp_ms") val timestampMs: Long,
    val payload: String, // Base64-encoded
    val meta: Map<String, Any>? = null
)

@JsonClass(generateAdapter = true)
data class Action(
    @Json(name = "action_type") val actionType: String,
    val parameters: Map<String, Any>,
    val priority: String = "normal"
)
```

## Best Practices

1. **Sequence Numbers**: Always increment sequence numbers for each chunk within a session
2. **Timestamps**: Use `System.currentTimeMillis()` for consistent timestamps
3. **Chunk Size**: Keep audio chunks ~100-200ms, frames at keyframe intervals
4. **Error Handling**: Always check response status and handle errors gracefully
5. **Session Cleanup**: Delete sessions when done to free server resources
6. **Buffering**: Don't send too many chunks without calling turn/complete
7. **Rate Limiting**: Respect server's `max_chunk_size_bytes` limit

## Files

- `schemas/dat_wire_protocol.json`: JSON Schema definition
- `src/wire/dat_protocol.py`: Pydantic models (Python)
- `src/edge_runtime/server.py`: FastAPI endpoints
- `tests/test_dat_wire_protocol.py`: Protocol tests

## See Also

- [Meta DAT Integration Guide](./meta_dat_integration.md)
- [Android SDK README](../sdk-android/README_DAT_INTEGRATION.md)
- [SmartGlass Agent Documentation](../README.md)

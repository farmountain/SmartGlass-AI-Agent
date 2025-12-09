# DAT Wire Protocol - Android/Kotlin Usage Examples

This document provides practical examples of using the DAT wire protocol from an Android application written in Kotlin.

## Setup

### Dependencies

```kotlin
// build.gradle.kts
dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.moshi:moshi:1.15.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.0")
    kapt("com.squareup.moshi:moshi-kotlin-codegen:1.15.0")
}
```

### Data Classes

```kotlin
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class SessionInitRequest(
    @Json(name = "device_id") val deviceId: String,
    @Json(name = "client_version") val clientVersion: String,
    val capabilities: ClientCapabilities = ClientCapabilities(),
    val metadata: Map<String, Any>? = null
)

@JsonClass(generateAdapter = true)
data class ClientCapabilities(
    @Json(name = "audio_streaming") val audioStreaming: Boolean = true,
    @Json(name = "video_streaming") val videoStreaming: Boolean = true,
    @Json(name = "imu_streaming") val imuStreaming: Boolean = false
)

@JsonClass(generateAdapter = true)
data class SessionInitResponse(
    @Json(name = "session_id") val sessionId: String,
    @Json(name = "server_version") val serverVersion: String,
    @Json(name = "max_chunk_size_bytes") val maxChunkSizeBytes: Int = 1048576,
    val capabilities: ServerCapabilities = ServerCapabilities()
)

@JsonClass(generateAdapter = true)
data class ServerCapabilities(
    @Json(name = "multimodal_queries") val multimodalQueries: Boolean = true,
    @Json(name = "streaming_transcription") val streamingTranscription: Boolean = false
)

@JsonClass(generateAdapter = true)
data class StreamChunk(
    @Json(name = "session_id") val sessionId: String,
    @Json(name = "chunk_type") val chunkType: String,
    @Json(name = "sequence_number") val sequenceNumber: Int,
    @Json(name = "timestamp_ms") val timestampMs: Long,
    val payload: String,
    val meta: Map<String, Any>? = null
)

@JsonClass(generateAdapter = true)
data class StreamChunkResponse(
    @Json(name = "session_id") val sessionId: String,
    @Json(name = "sequence_number") val sequenceNumber: Int,
    val status: String,
    val message: String? = null
)

@JsonClass(generateAdapter = true)
data class TurnCompleteRequest(
    @Json(name = "session_id") val sessionId: String,
    @Json(name = "turn_id") val turnId: String,
    @Json(name = "query_text") val queryText: String? = null,
    val language: String? = null,
    @Json(name = "cloud_offload") val cloudOffload: Boolean = false,
    val metadata: Map<String, Any>? = null
)

@JsonClass(generateAdapter = true)
data class TurnCompleteResponse(
    @Json(name = "session_id") val sessionId: String,
    @Json(name = "turn_id") val turnId: String,
    val response: String,
    val transcript: String? = null,
    val actions: List<Action> = emptyList(),
    val metadata: ResponseMetadata? = null
)

@JsonClass(generateAdapter = true)
data class Action(
    @Json(name = "action_type") val actionType: String,
    val parameters: Map<String, Any>,
    val priority: String = "normal"
)

@JsonClass(generateAdapter = true)
data class ResponseMetadata(
    @Json(name = "processing_time_ms") val processingTimeMs: Int? = null,
    @Json(name = "model_version") val modelVersion: String? = null
)
```

## API Client

```kotlin
import android.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.util.UUID
import java.util.concurrent.TimeUnit

class DatWireProtocolClient(
    private val baseUrl: String,
    private val httpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()
) {
    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()
    
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()
    
    // Adapters
    private val sessionInitRequestAdapter = moshi.adapter(SessionInitRequest::class.java)
    private val sessionInitResponseAdapter = moshi.adapter(SessionInitResponse::class.java)
    private val streamChunkAdapter = moshi.adapter(StreamChunk::class.java)
    private val streamChunkResponseAdapter = moshi.adapter(StreamChunkResponse::class.java)
    private val turnCompleteRequestAdapter = moshi.adapter(TurnCompleteRequest::class.java)
    private val turnCompleteResponseAdapter = moshi.adapter(TurnCompleteResponse::class.java)
    
    /**
     * Initialize a new DAT streaming session.
     */
    suspend fun initSession(deviceId: String): SessionInitResponse = withContext(Dispatchers.IO) {
        val request = SessionInitRequest(
            deviceId = deviceId,
            clientVersion = "1.0.0"
        )
        
        val json = sessionInitRequestAdapter.toJson(request)
        val httpRequest = Request.Builder()
            .url("$baseUrl/dat/session")
            .post(json.toRequestBody(jsonMediaType))
            .build()
        
        val response = httpClient.newCall(httpRequest).execute()
        if (!response.isSuccessful) {
            throw Exception("Session init failed: ${response.code}")
        }
        
        sessionInitResponseAdapter.fromJson(response.body!!.source())!!
    }
    
    /**
     * Send an audio chunk.
     */
    suspend fun sendAudioChunk(
        sessionId: String,
        sequenceNumber: Int,
        audioData: ByteArray,
        sampleRate: Int = 16000
    ): StreamChunkResponse = withContext(Dispatchers.IO) {
        val base64Audio = Base64.encodeToString(audioData, Base64.NO_WRAP)
        
        val chunk = StreamChunk(
            sessionId = sessionId,
            chunkType = "audio",
            sequenceNumber = sequenceNumber,
            timestampMs = System.currentTimeMillis(),
            payload = base64Audio,
            meta = mapOf(
                "sample_rate" to sampleRate,
                "channels" to 1,
                "format" to "pcm_s16le"
            )
        )
        
        sendStreamChunk(chunk)
    }
    
    /**
     * Send a video frame chunk.
     */
    suspend fun sendFrameChunk(
        sessionId: String,
        sequenceNumber: Int,
        jpegData: ByteArray,
        width: Int,
        height: Int
    ): StreamChunkResponse = withContext(Dispatchers.IO) {
        val base64Frame = Base64.encodeToString(jpegData, Base64.NO_WRAP)
        
        val chunk = StreamChunk(
            sessionId = sessionId,
            chunkType = "frame",
            sequenceNumber = sequenceNumber,
            timestampMs = System.currentTimeMillis(),
            payload = base64Frame,
            meta = mapOf(
                "width" to width,
                "height" to height,
                "format" to "jpeg",
                "is_keyframe" to true
            )
        )
        
        sendStreamChunk(chunk)
    }
    
    /**
     * Send a stream chunk (internal).
     */
    private suspend fun sendStreamChunk(chunk: StreamChunk): StreamChunkResponse = withContext(Dispatchers.IO) {
        val json = streamChunkAdapter.toJson(chunk)
        val httpRequest = Request.Builder()
            .url("$baseUrl/dat/stream")
            .post(json.toRequestBody(jsonMediaType))
            .build()
        
        val response = httpClient.newCall(httpRequest).execute()
        if (!response.isSuccessful) {
            throw Exception("Stream chunk failed: ${response.code}")
        }
        
        streamChunkResponseAdapter.fromJson(response.body!!.source())!!
    }
    
    /**
     * Complete a turn and get agent response.
     */
    suspend fun completeTurn(
        sessionId: String,
        queryText: String? = null,
        language: String = "en"
    ): TurnCompleteResponse = withContext(Dispatchers.IO) {
        val request = TurnCompleteRequest(
            sessionId = sessionId,
            turnId = UUID.randomUUID().toString(),
            queryText = queryText,
            language = language
        )
        
        val json = turnCompleteRequestAdapter.toJson(request)
        val httpRequest = Request.Builder()
            .url("$baseUrl/dat/turn/complete")
            .post(json.toRequestBody(jsonMediaType))
            .build()
        
        val response = httpClient.newCall(httpRequest).execute()
        if (!response.isSuccessful) {
            throw Exception("Turn complete failed: ${response.code}")
        }
        
        turnCompleteResponseAdapter.fromJson(response.body!!.source())!!
    }
}
```

## Usage Example

```kotlin
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class DatStreamingExample {
    private val client = DatWireProtocolClient(baseUrl = "http://10.0.2.2:8000")
    private var sessionId: String? = null
    private var sequenceNumber = 0
    
    fun startSession() {
        CoroutineScope(Dispatchers.Main).launch {
            try {
                // 1. Initialize session
                val sessionResponse = client.initSession(deviceId = "rayban-meta-12345")
                sessionId = sessionResponse.sessionId
                println("Session started: $sessionId")
                
            } catch (e: Exception) {
                println("Error starting session: ${e.message}")
            }
        }
    }
    
    fun sendAudio(audioData: ByteArray) {
        val currentSessionId = sessionId ?: return
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                // 2. Send audio chunk
                val response = client.sendAudioChunk(
                    sessionId = currentSessionId,
                    sequenceNumber = sequenceNumber++,
                    audioData = audioData,
                    sampleRate = 16000
                )
                println("Audio chunk sent: ${response.status}")
                
            } catch (e: Exception) {
                println("Error sending audio: ${e.message}")
            }
        }
    }
    
    fun sendFrame(jpegData: ByteArray, width: Int, height: Int) {
        val currentSessionId = sessionId ?: return
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                // 3. Send frame chunk
                val response = client.sendFrameChunk(
                    sessionId = currentSessionId,
                    sequenceNumber = sequenceNumber++,
                    jpegData = jpegData,
                    width = width,
                    height = height
                )
                println("Frame chunk sent: ${response.status}")
                
            } catch (e: Exception) {
                println("Error sending frame: ${e.message}")
            }
        }
    }
    
    fun finalizeTurn(queryText: String? = null) {
        val currentSessionId = sessionId ?: return
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                // 4. Complete turn and get response
                val turnResponse = client.completeTurn(
                    sessionId = currentSessionId,
                    queryText = queryText,
                    language = "en"
                )
                
                println("Agent response: ${turnResponse.response}")
                if (turnResponse.transcript != null) {
                    println("Transcript: ${turnResponse.transcript}")
                }
                
                // Execute actions
                for (action in turnResponse.actions) {
                    handleAction(action)
                }
                
                // Reset sequence number for next turn
                sequenceNumber = 0
                
            } catch (e: Exception) {
                println("Error completing turn: ${e.message}")
            }
        }
    }
    
    private fun handleAction(action: Action) {
        when (action.actionType) {
            "NAVIGATE" -> {
                val destination = action.parameters["destination"] as? String
                println("Navigate to: $destination")
                // Launch navigation
            }
            "SHOW_TEXT" -> {
                val text = action.parameters["text"] as? String
                println("Show text: $text")
                // Display text overlay
            }
            "PLAY_AUDIO" -> {
                println("Play audio action")
                // Play audio feedback
            }
            else -> {
                println("Unknown action: ${action.actionType}")
            }
        }
    }
}
```

## Integration with DatSmartGlassController

The `DatSmartGlassController` from the SmartGlass SDK can be integrated with this wire protocol client:

```kotlin
class IntegratedDatController(
    private val rayBanManager: MetaRayBanManager,
    private val wireClient: DatWireProtocolClient
) {
    private var sessionId: String? = null
    private var sequenceNumber = 0
    
    suspend fun start(deviceId: String) {
        // Initialize session
        val response = wireClient.initSession(deviceId)
        sessionId = response.sessionId
        
        // Start streaming from glasses
        rayBanManager.startStreaming { videoFrame ->
            // Send frame via wire protocol
            CoroutineScope(Dispatchers.IO).launch {
                sessionId?.let { sid ->
                    wireClient.sendFrameChunk(
                        sessionId = sid,
                        sequenceNumber = sequenceNumber++,
                        jpegData = videoFrame.jpegData,
                        width = videoFrame.width,
                        height = videoFrame.height
                    )
                }
            }
        }
        
        // Handle audio from glasses
        rayBanManager.setAudioCallback { audioBuffer ->
            CoroutineScope(Dispatchers.IO).launch {
                sessionId?.let { sid ->
                    wireClient.sendAudioChunk(
                        sessionId = sid,
                        sequenceNumber = sequenceNumber++,
                        audioData = audioBuffer,
                        sampleRate = 16000
                    )
                }
            }
        }
    }
    
    suspend fun finalizeTurn(): TurnCompleteResponse? {
        return sessionId?.let { sid ->
            wireClient.completeTurn(sessionId = sid)
        }
    }
}
```

## Best Practices

1. **Error Handling**: Always wrap API calls in try-catch blocks
2. **Coroutines**: Use appropriate coroutine dispatchers (IO for network calls)
3. **Sequence Numbers**: Track sequence numbers per session, reset after turn completion
4. **Session Lifecycle**: Initialize session once, reuse for multiple turns
5. **Chunk Size**: Keep audio chunks ~100-200ms for responsiveness
6. **Base64 Encoding**: Use `Base64.NO_WRAP` flag to avoid newlines in payload
7. **Timestamps**: Use `System.currentTimeMillis()` for consistency
8. **Action Handling**: Implement action handlers for all supported action types

## Testing

```kotlin
@Test
fun testSessionInit() = runBlocking {
    val client = DatWireProtocolClient("http://localhost:8000")
    val response = client.initSession("test-device-123")
    
    assertTrue(response.sessionId.isNotEmpty())
    assertTrue(response.sessionId.matches(Regex("[0-9a-f-]{36}")))
    assertEquals("0.1.0", response.serverVersion)
}

@Test
fun testAudioStreaming() = runBlocking {
    val client = DatWireProtocolClient("http://localhost:8000")
    
    // Init session
    val session = client.initSession("test-device-123")
    
    // Send audio chunk
    val audioData = ByteArray(3200) // 100ms at 16kHz mono
    val response = client.sendAudioChunk(
        sessionId = session.sessionId,
        sequenceNumber = 0,
        audioData = audioData
    )
    
    assertEquals("buffered", response.status)
}
```

## See Also

- [DAT Wire Protocol Documentation](./dat_wire_protocol.md)
- [SmartGlass Android SDK](../sdk-android/README.md)
- [Meta DAT Integration Guide](./meta_dat_integration.md)

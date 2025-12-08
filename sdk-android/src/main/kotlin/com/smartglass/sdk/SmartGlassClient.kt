package com.smartglass.sdk

import com.squareup.moshi.Json
import com.squareup.moshi.JsonAdapter
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response

private const val JSON_MEDIA_TYPE = "application/json; charset=utf-8"
private const val DEFAULT_BASE_URL = "http://127.0.0.1:8000"
private const val DEFAULT_TIMEOUT_SECONDS = 30L
private const val DEFAULT_QUERY_TEXT = "Query from SmartGlass"
private const val AUDIO_QUERY_TEMPLATE = "Audio input received (%d chunks)"

/**
 * HTTP client for the SmartGlass Agent Python backend.
 *
 * This client provides a streaming-style API for sending audio chunks and frames to the backend,
 * then finalizing the turn to receive the agent's response. It follows the pattern:
 *
 * 1. [startSession] - Create a new session and receive a [SessionHandle]
 * 2. [sendAudioChunk] - Send audio data with timestamp (can be called multiple times)
 * 3. [sendFrame] - Send JPEG-encoded frame with timestamp (can be called multiple times)
 * 4. [finalizeTurn] - Process all accumulated data and receive [AgentResult]
 *
 * Example usage:
 * ```kotlin
 * val client = SmartGlassClient(baseUrl = "http://10.0.2.2:8000")
 * val session = client.startSession()
 *
 * // Send audio and visual data
 * client.sendAudioChunk(session, audioData, System.currentTimeMillis())
 * client.sendFrame(session, jpegBytes, System.currentTimeMillis())
 *
 * // Get the agent's response
 * val result = client.finalizeTurn(session)
 * println("Response: ${result.response}")
 * ```
 *
 * The client handles:
 * - Network timeouts (configurable via OkHttpClient)
 * - Error responses from the server (throws [IOException])
 * - Concurrent access to session state (thread-safe)
 *
 * @param baseUrl Base URL of the Python backend (e.g., "http://localhost:8000")
 * @param httpClient Optional custom OkHttpClient for advanced configuration
 * @param moshi Optional custom Moshi instance for JSON serialization
 */
class SmartGlassClient @JvmOverloads constructor(
    baseUrl: String = DEFAULT_BASE_URL,
    private val httpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(DEFAULT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .readTimeout(DEFAULT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .writeTimeout(DEFAULT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .build(),
    moshi: Moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build(),
) {
    private val resolvedBaseUrl = baseUrl.trimEnd('/')
    private val jsonMediaType = JSON_MEDIA_TYPE.toMediaType()

    // Session state management
    private val sessionMutex = Mutex()
    private val sessionStates = mutableMapOf<String, SessionState>()

    private val mapType = Types.newParameterizedType(Map::class.java, String::class.java, Any::class.java)
    private val ingestRequestAdapter: JsonAdapter<IngestRequest> = moshi.adapter(IngestRequest::class.java)
    private val ingestResponseAdapter: JsonAdapter<IngestResponse> = moshi.adapter(IngestResponse::class.java)
    private val answerRequestAdapter: JsonAdapter<AnswerRequest> = moshi.adapter(AnswerRequest::class.java)
    private val agentResultAdapter: JsonAdapter<AgentResult> = moshi.adapter(AgentResult::class.java)
    private val mapAdapter: JsonAdapter<Map<String, Any>> = moshi.adapter(mapType)
    private val errorAdapter: JsonAdapter<ErrorResponse> = moshi.adapter(ErrorResponse::class.java)

    /**
     * Start a new SmartGlass session.
     *
     * Creates a new session on the backend and returns a [SessionHandle] that can be used
     * to send audio chunks, frames, and finalize the turn.
     *
     * @return SessionHandle for subsequent API calls
     * @throws IOException if the network request fails or returns an error
     */
    suspend fun startSession(): SessionHandle {
        val payload = ingestRequestAdapter.toJson(IngestRequest(text = ""))
        val request = Request.Builder()
            .url("$resolvedBaseUrl/ingest")
            .post(payload.toRequestBody(jsonMediaType))
            .build()

        val response = execute(request)
        val sessionId = response.use { parseBody(it, ingestResponseAdapter).sessionId }

        // Initialize session state
        sessionMutex.withLock {
            sessionStates[sessionId] = SessionState()
        }

        return SessionHandle(sessionId)
    }

    /**
     * Send an audio chunk to the session.
     *
     * Audio data is accumulated in the session state. The backend will process all
     * accumulated audio when [finalizeTurn] is called.
     *
     * @param session Session handle from [startSession]
     * @param data Raw audio bytes (PCM format recommended)
     * @param timestampMs Timestamp in milliseconds when the audio was captured
     * @throws IOException if the session is invalid
     */
    suspend fun sendAudioChunk(session: SessionHandle, data: ByteArray, timestampMs: Long) {
        sessionMutex.withLock {
            val state = sessionStates[session.sessionId]
                ?: throw IOException("Invalid session: ${session.sessionId}")

            state.audioChunks.add(AudioChunk(data, timestampMs))
        }
    }

    /**
     * Send a frame to the session.
     *
     * Frame data is accumulated in the session state for future use.
     *
     * **Note**: The current backend expects file paths rather than inline image data.
     * Frame data is accumulated but not yet transmitted to the backend. Future versions
     * will support frame upload once the backend API is extended to accept base64-encoded
     * images or a file upload endpoint is added.
     *
     * @param session Session handle from [startSession]
     * @param jpegBytes JPEG-encoded image data
     * @param timestampMs Timestamp in milliseconds when the frame was captured
     * @throws IOException if the session is invalid
     */
    suspend fun sendFrame(session: SessionHandle, jpegBytes: ByteArray, timestampMs: Long) {
        sessionMutex.withLock {
            val state = sessionStates[session.sessionId]
                ?: throw IOException("Invalid session: ${session.sessionId}")

            state.frames.add(FrameData(jpegBytes, timestampMs))
        }
    }

    /**
     * Finalize the turn and receive the agent's response.
     *
     * This method sends all accumulated audio chunks and frames to the backend,
     * processes the multimodal query, and returns the agent's response with any
     * associated actions.
     *
     * After finalization, the session state is cleared but the session remains valid
     * for subsequent turns.
     *
     * @param session Session handle from [startSession]
     * @return AgentResult containing the response text, actions, and raw metadata
     * @throws IOException if the network request fails, session is invalid, or server returns an error
     */
    suspend fun finalizeTurn(session: SessionHandle): AgentResult {
        // Get and clear session state
        val state = sessionMutex.withLock {
            val state = sessionStates[session.sessionId]
                ?: throw IOException("Invalid session: ${session.sessionId}")

            // Create a copy and clear the state for the next turn
            val stateCopy = state.copy()
            state.clear()
            stateCopy
        }

        // Build the query text from audio (TODO: integrate actual transcription pipeline)
        // For now, we send a placeholder that indicates audio was received
        val queryText = if (state.audioChunks.isNotEmpty()) {
            String.format(AUDIO_QUERY_TEMPLATE, state.audioChunks.size)
        } else {
            DEFAULT_QUERY_TEXT
        }

        // TODO: Implement frame upload to backend
        // The current backend expects a file path, not inline bytes.
        // Options: 1) Extend backend to accept base64 frames, 2) Upload to temp file first
        val imagePath: String? = null

        val payload = answerRequestAdapter.toJson(
            AnswerRequest(sessionId = session.sessionId, text = queryText, imagePath = imagePath),
        )
        val request = Request.Builder()
            .url("$resolvedBaseUrl/answer")
            .post(payload.toRequestBody(jsonMediaType))
            .build()

        val response = execute(request)
        return response.use { parseAgentResult(it) }
    }

    /**
     * Legacy method: Start a new SmartGlass session (simple API).
     *
     * @deprecated Use [startSession] without parameters and the new streaming API instead
     */
    @Deprecated("Use startSession() without parameters", ReplaceWith("startSession()"))
    suspend fun startSession(text: String? = null, imagePath: String? = null): String {
        val payload = ingestRequestAdapter.toJson(IngestRequest(text = text, imagePath = imagePath))
        val request = Request.Builder()
            .url("$resolvedBaseUrl/ingest")
            .post(payload.toRequestBody(jsonMediaType))
            .build()

        val response = execute(request)
        return response.use { parseBody(it, ingestResponseAdapter).sessionId }
    }

    /**
     * Legacy method: Send a prompt and optional image for an existing session.
     *
     * @deprecated Use the new streaming API with [sendAudioChunk], [sendFrame], and [finalizeTurn]
     */
    @Deprecated("Use sendAudioChunk/sendFrame/finalizeTurn", ReplaceWith("finalizeTurn(SessionHandle(sessionId))"))
    suspend fun answer(sessionId: String, text: String? = null, imagePath: String? = null): SmartGlassResponse {
        val payload = answerRequestAdapter.toJson(
            AnswerRequest(sessionId = sessionId, text = text, imagePath = imagePath),
        )
        val request = Request.Builder()
            .url("$resolvedBaseUrl/answer")
            .post(payload.toRequestBody(jsonMediaType))
            .build()

        val response = execute(request)
        response.use { return parseLegacyResponse(it) }
    }

    private suspend fun execute(request: Request): Response {
        return withContext(Dispatchers.IO) {
            try {
                httpClient.newCall(request).execute()
            } catch (exc: CancellationException) {
                throw exc
            } catch (exc: Exception) {
                throw IOException("Failed to execute HTTP request: ${exc.message}", exc)
            }
        }
    }

    private fun <T> parseBody(response: Response, adapter: JsonAdapter<T>): T {
        if (!response.isSuccessful) {
            val errorBody = response.body?.string()
            val errorMessage = errorBody?.let { body ->
                errorAdapter.fromJson(body)?.detail ?: errorAdapter.fromJson(body)?.error
            }
            val message = errorMessage ?: errorBody ?: "HTTP ${response.code}"
            throw IOException("SmartGlass server error: ${response.code}: $message")
        }

        val bodyString = response.body?.string() ?: throw IOException("Empty response body")
        return adapter.fromJson(bodyString) ?: throw IOException("Failed to parse response body")
    }

    private fun parseAgentResult(response: Response): AgentResult {
        if (!response.isSuccessful) {
            throwHttpError(response)
        }

        val bodyString = response.body?.string() ?: throw IOException("Empty response body")

        // Try parsing as AgentResult first
        agentResultAdapter.fromJson(bodyString)?.let { return it }

        // Fallback: parse as a generic map and construct AgentResult
        val rawMap = mapAdapter.fromJson(bodyString) ?: emptyMap()
        val responseText = rawMap["response"] as? String ?: ""
        val actions = parseActions(rawMap["actions"])

        return AgentResult(
            response = responseText,
            actions = actions,
            raw = rawMap,
        )
    }

    private fun parseLegacyResponse(response: Response): SmartGlassResponse {
        if (!response.isSuccessful) {
            throwHttpError(response)
        }

        val bodyString = response.body?.string() ?: throw IOException("Empty response body")
        val rawMap = mapAdapter.fromJson(bodyString) ?: emptyMap()
        val responseText = rawMap["response"] as? String ?: ""
        val actions = parseActions(rawMap["actions"])

        return SmartGlassResponse(
            response = responseText,
            actions = actions,
            raw = rawMap,
        )
    }

    private fun parseActions(actionsData: Any?): List<Action> {
        return (actionsData as? List<*>)?.mapNotNull { action ->
            when (action) {
                is Map<*, *> -> {
                    val type = action["type"] as? String ?: return@mapNotNull null
                    val payload = (action["payload"] as? Map<*, *>)?.mapNotNull {
                        val key = it.key as? String
                        val value = it.value
                        if (key != null) key to value else null
                    }?.toMap() ?: emptyMap()
                    Action(type = type, payload = payload)
                }
                else -> null
            }
        } ?: emptyList()
    }

    private fun throwHttpError(response: Response): Nothing {
        val errorBody = response.body?.string()
        val errorMessage = errorBody?.let { body ->
            errorAdapter.fromJson(body)?.detail ?: errorAdapter.fromJson(body)?.error
        }
        val message = errorMessage ?: errorBody ?: "HTTP ${response.code}"
        throw IOException("SmartGlass server error: ${response.code}: $message")
    }
}

/**
 * Handle for an active SmartGlass session.
 *
 * Obtained from [SmartGlassClient.startSession] and used for all subsequent
 * operations on that session.
 *
 * @property sessionId Unique identifier for the session
 */
data class SessionHandle(
    val sessionId: String,
)

/**
 * Result from the agent after processing a turn.
 *
 * Contains the agent's text response, any actions to execute, and raw metadata
 * from the backend. Actions can be executed using [ActionExecutor.execute].
 *
 * @property response Human-readable response text from the agent
 * @property actions List of actions the agent recommends (e.g., NAVIGATE, SHOW_TEXT)
 * @property raw Raw metadata from the backend (latencies, model info, etc.)
 */
data class AgentResult(
    val response: String = "",
    val actions: List<Action> = emptyList(),
    val raw: Map<String, Any> = emptyMap(),
)

/**
 * An action recommended by the agent.
 *
 * Actions have a type (e.g., "NAVIGATE", "SHOW_TEXT") and a payload with
 * type-specific parameters. Use [ActionExecutor.execute] to handle built-in actions.
 *
 * @property type Action type identifier (uppercase recommended)
 * @property payload Action-specific parameters
 */
data class Action(
    val type: String,
    val payload: Map<String, Any> = emptyMap(),
)

/**
 * Legacy response type for backward compatibility.
 *
 * @deprecated Use [AgentResult] with the new streaming API
 */
@Deprecated("Use AgentResult", ReplaceWith("AgentResult"))
data class SmartGlassResponse(
    val response: String = "",
    val actions: List<Action> = emptyList(),
    val raw: Map<String, Any> = emptyMap(),
)

// Internal data classes

private data class SessionState(
    val audioChunks: MutableList<AudioChunk> = mutableListOf(),
    val frames: MutableList<FrameData> = mutableListOf(),
) {
    fun copy() = SessionState(
        audioChunks = audioChunks.toMutableList(),
        frames = frames.toMutableList(),
    )

    fun clear() {
        audioChunks.clear()
        frames.clear()
    }
}

private data class AudioChunk(
    val data: ByteArray,
    val timestampMs: Long,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        other as AudioChunk
        if (!data.contentEquals(other.data)) return false
        if (timestampMs != other.timestampMs) return false
        return true
    }

    override fun hashCode(): Int {
        var result = data.contentHashCode()
        result = 31 * result + timestampMs.hashCode()
        return result
    }
}

private data class FrameData(
    val jpegBytes: ByteArray,
    val timestampMs: Long,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        other as FrameData
        if (!jpegBytes.contentEquals(other.jpegBytes)) return false
        if (timestampMs != other.timestampMs) return false
        return true
    }

    override fun hashCode(): Int {
        var result = jpegBytes.contentHashCode()
        result = 31 * result + timestampMs.hashCode()
        return result
    }
}

private data class IngestRequest(
    val text: String? = null,
    @Json(name = "image_path") val imagePath: String? = null,
)

private data class IngestResponse(
    @Json(name = "session_id") val sessionId: String,
)

private data class AnswerRequest(
    @Json(name = "session_id") val sessionId: String,
    val text: String? = null,
    @Json(name = "image_path") val imagePath: String? = null,
)

private data class ErrorResponse(
    val detail: String? = null,
    val error: String? = null,
)

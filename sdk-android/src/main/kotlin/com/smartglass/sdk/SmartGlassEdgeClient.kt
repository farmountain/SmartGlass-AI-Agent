package com.smartglass.sdk

import com.squareup.moshi.Json
import com.squareup.moshi.JsonAdapter
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.io.IOException
import java.util.Base64
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response

private const val JSON_MEDIA_TYPE = "application/json; charset=utf-8"
private const val DEFAULT_BASE_URL = "http://127.0.0.1:8765"

/**
 * Lightweight HTTP client for the SmartGlass edge runtime.
 */
class SmartGlassEdgeClient @JvmOverloads constructor(
    baseUrl: String = DEFAULT_BASE_URL,
    private val httpClient: OkHttpClient = OkHttpClient.Builder().build(),
    moshi: Moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build(),
) {
    private val resolvedBaseUrl = baseUrl.trimEnd('/')
    private val jsonMediaType = JSON_MEDIA_TYPE.toMediaType()

    private val createSessionAdapter: JsonAdapter<CreateSessionResponse> =
        moshi.adapter(CreateSessionResponse::class.java)
    private val edgeResponseAdapter: JsonAdapter<EdgeResponse> = moshi.adapter(EdgeResponse::class.java)
    private val errorAdapter: JsonAdapter<ErrorResponse> = moshi.adapter(ErrorResponse::class.java)
    private val audioAdapter: JsonAdapter<AudioRequest> = moshi.adapter(AudioRequest::class.java)
    private val frameAdapter: JsonAdapter<FrameRequest> = moshi.adapter(FrameRequest::class.java)
    private val queryAdapter: JsonAdapter<QueryRequest> = moshi.adapter(QueryRequest::class.java)

    /**
     * Create a new session on the edge runtime.
     */
    suspend fun createSession(): String {
        val requestBody = "{}".toRequestBody(jsonMediaType)
        val request = Request.Builder()
            .url("$resolvedBaseUrl/sessions")
            .post(requestBody)
            .build()

        val response = execute(request)
        response.use {
            val payload = parseBody(it, createSessionAdapter)
            return payload.sessionId
        }
    }

    /**
     * Send an audio chunk for transcription.
     */
    suspend fun sendAudioChunk(
        sessionId: String,
        bytes: ByteArray,
        sampleRate: Int,
        language: String? = null,
    ): EdgeResponse {
        val audioBase64 = Base64.getEncoder().encodeToString(bytes)
        val payload = audioAdapter.toJson(
            AudioRequest(audioBase64 = audioBase64, sampleRate = sampleRate, language = language),
        )
        val request = Request.Builder()
            .url("$resolvedBaseUrl/sessions/$sessionId/audio")
            .post(payload.toRequestBody(jsonMediaType))
            .build()

        val response = execute(request)
        response.use { return parseBody(it, edgeResponseAdapter) }
    }

    /**
     * Send a JPEG frame to the edge runtime.
     */
    suspend fun sendFrame(
        sessionId: String,
        jpegBytes: ByteArray,
        width: Int? = null,
        height: Int? = null,
    ): EdgeResponse {
        val frameBase64 = Base64.getEncoder().encodeToString(jpegBytes)
        val payload = frameAdapter.toJson(
            FrameRequest(imageBase64 = frameBase64, width = width, height = height),
        )
        val request = Request.Builder()
            .url("$resolvedBaseUrl/sessions/$sessionId/frame")
            .post(payload.toRequestBody(jsonMediaType))
            .build()

        val response = execute(request)
        response.use { return parseBody(it, edgeResponseAdapter) }
    }

    /**
     * Run a multimodal query using any stored context for the session.
     */
    suspend fun runQuery(
        sessionId: String,
        textQuery: String? = null,
        audioBytes: ByteArray? = null,
        imageBytes: ByteArray? = null,
        sampleRate: Int? = null,
        language: String? = null,
        cloudOffload: Boolean = false,
    ): EdgeResponse {
        if (textQuery == null && audioBytes == null) {
            throw IllegalArgumentException("Provide either textQuery or audioBytes")
        }

        val resolvedSampleRate = if (audioBytes != null) {
            sampleRate ?: throw IllegalArgumentException("Provide sampleRate when audioBytes is provided")
        } else {
            null
        }

        val payload = queryAdapter.toJson(
            QueryRequest(
                textQuery = textQuery,
                audioBase64 = audioBytes?.let { Base64.getEncoder().encodeToString(it) },
                sampleRate = resolvedSampleRate,
                imageBase64 = imageBytes?.let { Base64.getEncoder().encodeToString(it) },
                language = language,
                cloudOffload = cloudOffload,
            ),
        )
        val request = Request.Builder()
            .url("$resolvedBaseUrl/sessions/$sessionId/query")
            .post(payload.toRequestBody(jsonMediaType))
            .build()

        val response = execute(request)
        response.use { return parseBody(it, edgeResponseAdapter) }
    }

    /**
     * Close and clean up a session.
     */
    suspend fun closeSession(sessionId: String): EdgeResponse {
        val request = Request.Builder()
            .url("$resolvedBaseUrl/sessions/$sessionId")
            .delete()
            .build()

        val response = execute(request)
        response.use { return parseBody(it, edgeResponseAdapter) }
    }

    private suspend fun execute(request: Request): Response {
        return withContext(Dispatchers.IO) {
            try {
                httpClient.newCall(request).execute()
            } catch (exc: CancellationException) {
                throw exc
            } catch (exc: Exception) {
                throw IOException("Failed to execute HTTP request", exc)
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
            throw IOException("Edge runtime error: ${response.code}: $message")
        }

        val bodyString = response.body?.string()
            ?: throw IOException("Empty response body")
        return adapter.fromJson(bodyString) ?: throw IOException("Failed to parse response body")
    }
}

/** Edge runtime response envelope. */
data class EdgeResponse(
    @Json(name = "session_id") val sessionId: String? = null,
    val transcript: String? = null,
    val response: String? = null,
    val query: String? = null,
    @Json(name = "visual_context") val visualContext: String? = null,
    val overlays: List<Overlay>? = null,
    val metadata: EdgeMetadata? = null,
    val redaction: RedactionSummary? = null,
    val status: String? = null,
    val error: String? = null,
)

private data class CreateSessionResponse(
    @Json(name = "session_id") val sessionId: String,
)

/** Structured overlay payload rendered by SmartGlass UI layers. */
data class Overlay(
    val type: String,
    val content: String? = null,
    val text: String? = null,
    val box: List<Int>? = null,
    val boxes: List<List<Int>>? = null,
    val conf: List<Double>? = null,
    @Json(name = "by_word") val byWord: List<OverlayWord>? = null,
)

/** Per-word OCR overlay details. */
data class OverlayWord(
    val text: String,
    val box: List<Int> = emptyList(),
    val conf: Double? = null,
)

/** Additional context about the edge response for client-side handling. */
data class EdgeMetadata(
    @Json(name = "cloud_offload") val cloudOffload: Boolean? = null,
    @Json(name = "redaction_summary") val redactionSummary: RedactionSummary? = null,
    @Json(name = "latency_ms") val latencyMs: Double? = null,
)

/** Summary of deterministic redaction performed on visual inputs. */
data class RedactionSummary(
    @Json(name = "faces_masked") val facesMasked: Int = 0,
    @Json(name = "plates_masked") val platesMasked: Int = 0,
    @Json(name = "total_masked_area") val totalMaskedArea: Int = 0,
)

private data class AudioRequest(
    @Json(name = "audio_base64") val audioBase64: String,
    @Json(name = "sample_rate") val sampleRate: Int? = null,
    val language: String? = null,
)

private data class FrameRequest(
    @Json(name = "image_base64") val imageBase64: String,
    val width: Int? = null,
    val height: Int? = null,
)

private data class QueryRequest(
    @Json(name = "text_query") val textQuery: String? = null,
    @Json(name = "audio_base64") val audioBase64: String? = null,
    @Json(name = "sample_rate") val sampleRate: Int? = null,
    @Json(name = "image_base64") val imageBase64: String? = null,
    val language: String? = null,
    @Json(name = "cloud_offload") val cloudOffload: Boolean = false,
)

private data class ErrorResponse(
    val detail: String? = null,
    val error: String? = null,
)

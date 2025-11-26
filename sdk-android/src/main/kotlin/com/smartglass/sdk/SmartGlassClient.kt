package com.smartglass.sdk

import com.squareup.moshi.Json
import com.squareup.moshi.JsonAdapter
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.io.IOException
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response

private const val JSON_MEDIA_TYPE = "application/json; charset=utf-8"
private const val DEFAULT_BASE_URL = "http://127.0.0.1:8000"

/**
 * Lightweight HTTP client for the SmartGlass Agent server.
 */
class SmartGlassClient @JvmOverloads constructor(
    baseUrl: String = DEFAULT_BASE_URL,
    private val httpClient: OkHttpClient = OkHttpClient.Builder().build(),
    moshi: Moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build(),
) {
    private val resolvedBaseUrl = baseUrl.trimEnd('/')
    private val jsonMediaType = JSON_MEDIA_TYPE.toMediaType()

    private val mapType = Types.newParameterizedType(Map::class.java, String::class.java, Any::class.java)
    private val ingestRequestAdapter: JsonAdapter<IngestRequest> = moshi.adapter(IngestRequest::class.java)
    private val ingestResponseAdapter: JsonAdapter<IngestResponse> = moshi.adapter(IngestResponse::class.java)
    private val answerRequestAdapter: JsonAdapter<AnswerRequest> = moshi.adapter(AnswerRequest::class.java)
    private val smartGlassResponseAdapter: JsonAdapter<SmartGlassResponse> = moshi.adapter(SmartGlassResponse::class.java)
    private val mapAdapter: JsonAdapter<Map<String, Any>> = moshi.adapter(mapType)
    private val errorAdapter: JsonAdapter<ErrorResponse> = moshi.adapter(ErrorResponse::class.java)

    /**
     * Start a new SmartGlass session.
     */
    suspend fun startSession(text: String? = null, imagePath: String? = null): String {
        val payload = ingestRequestAdapter.toJson(IngestRequest(text = text, imagePath = imagePath))
        val request = Request.Builder()
            .url("$resolvedBaseUrl/ingest")
            .post(payload.toRequestBody(jsonMediaType))
            .build()

        val response = execute(request)
        response.use { return parseBody(it, ingestResponseAdapter).sessionId }
    }

    /**
     * Send a prompt and optional image for an existing session.
     */
    suspend fun answer(sessionId: String, text: String? = null, imagePath: String? = null): SmartGlassResponse {
        val payload = answerRequestAdapter.toJson(
            AnswerRequest(sessionId = sessionId, text = text, imagePath = imagePath),
        )
        val request = Request.Builder()
            .url("$resolvedBaseUrl/answer")
            .post(payload.toRequestBody(jsonMediaType))
            .build()

        val response = execute(request)
        response.use { return parseBody(it, smartGlassResponseAdapter) }
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
            throw IOException("SmartGlass server error: ${response.code}: $message")
        }

        val bodyString = response.body?.string() ?: throw IOException("Empty response body")
        val parsed = adapter.fromJson(bodyString)
        if (parsed != null) {
            return parsed
        }

        // Fallback attempt to coerce responses with arbitrary payloads for robustness.
        if (adapter == smartGlassResponseAdapter) {
            val rawMap = mapAdapter.fromJson(bodyString) ?: emptyMap()
            val responseText = rawMap["response"] as? String
            val actions = (rawMap["actions"] as? List<*>)?.mapNotNull { action ->
                when (action) {
                    is Map<*, *> -> Action(
                        type = action["type"] as? String ?: "",
                        payload = (action["payload"] as? Map<*, *>)?.mapNotNull {
                            val key = it.key as? String
                            val value = it.value
                            if (key != null) key to value else null
                        }?.toMap() ?: emptyMap(),
                    )

                    else -> null
                }
            } ?: emptyList()
            return SmartGlassResponse(
                response = responseText ?: "",
                actions = actions,
                raw = rawMap,
            ) as T
        }

        throw IOException("Failed to parse response body")
    }
}

data class Action(
    val type: String,
    val payload: Map<String, Any> = emptyMap(),
)

data class SmartGlassResponse(
    val response: String = "",
    val actions: List<Action> = emptyList(),
    val raw: Map<String, Any> = emptyMap(),
)

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

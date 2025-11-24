package com.smartglass.sdk

import java.io.IOException
import java.util.Base64
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.json.JSONObject
import org.junit.After
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class SmartGlassEdgeClientTest {
    private lateinit var server: MockWebServer
    private lateinit var client: SmartGlassEdgeClient

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        client = SmartGlassEdgeClient(server.url("/").toString())
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun createSessionRequestsCorrectEndpointAndParsesResponse() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"session123"}"""))

        val sessionId = client.createSession()
        val recorded = server.takeRequest()

        assertEquals("/sessions", recorded.path)
        assertEquals("{}", recorded.body.readUtf8())
        assertEquals("session123", sessionId)
    }

    @Test
    fun sendAudioChunkSendsPayloadAndParsesEdgeResponse() = runBlocking {
        server.enqueue(successfulEdgeResponse())
        val bytes = "audio-bytes".toByteArray()

        val response = client.sendAudioChunk("session123", bytes, sampleRate = 16000, language = "en-US")
        val recorded = server.takeRequest()
        val body = JSONObject(recorded.body.readUtf8())

        assertEquals("/sessions/session123/audio", recorded.path)
        assertEquals(Base64.getEncoder().encodeToString(bytes), body.getString("audio_base64"))
        assertEquals(16000, body.getInt("sample_rate"))
        assertEquals("en-US", body.getString("language"))
        assertParsedEdgeResponse(response)
    }

    @Test
    fun sendFrameSendsPayloadAndParsesEdgeResponse() = runBlocking {
        server.enqueue(successfulEdgeResponse())
        val frameBytes = byteArrayOf(1, 2, 3, 4)

        val response = client.sendFrame("session123", frameBytes, width = 640, height = 480)
        val recorded = server.takeRequest()
        val body = JSONObject(recorded.body.readUtf8())

        assertEquals("/sessions/session123/frame", recorded.path)
        assertEquals(Base64.getEncoder().encodeToString(frameBytes), body.getString("image_base64"))
        assertEquals(640, body.getInt("width"))
        assertEquals(480, body.getInt("height"))
        assertParsedEdgeResponse(response)
    }

    @Test
    fun runQuerySendsPayloadAndParsesEdgeResponse() = runBlocking {
        server.enqueue(successfulEdgeResponse())
        val audioBytes = "query-audio".toByteArray()
        val imageBytes = byteArrayOf(9, 8, 7)

        val response = client.runQuery(
            sessionId = "session123",
            textQuery = "What do you see?",
            audioBytes = audioBytes,
            imageBytes = imageBytes,
            sampleRate = 44100,
            language = "en",
            cloudOffload = true,
        )
        val recorded = server.takeRequest()
        val body = JSONObject(recorded.body.readUtf8())

        assertEquals("/sessions/session123/query", recorded.path)
        assertEquals("What do you see?", body.getString("text_query"))
        assertEquals(Base64.getEncoder().encodeToString(audioBytes), body.getString("audio_base64"))
        assertEquals(44100, body.getInt("sample_rate"))
        assertEquals(Base64.getEncoder().encodeToString(imageBytes), body.getString("image_base64"))
        assertEquals("en", body.getString("language"))
        assertEquals(true, body.getBoolean("cloud_offload"))
        assertParsedEdgeResponse(response)
    }

    @Test
    fun closeSessionHitsEndpointAndParsesEdgeResponse() = runBlocking {
        server.enqueue(successfulEdgeResponse())

        val response = client.closeSession("session123")
        val recorded = server.takeRequest()

        assertEquals("/sessions/session123", recorded.path)
        assertEquals("", recorded.body.readUtf8())
        assertParsedEdgeResponse(response)
    }

    @Test
    fun nonSuccessResponsesSurfaceEdgeErrorDetails() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(400).setBody("""{"detail":"Invalid session"}"""))

        val error = assertFailsWith<IOException> { client.closeSession("bad-session") }
        val recorded = server.takeRequest()

        assertEquals("/sessions/bad-session", recorded.path)
        assertTrue(error.message!!.contains("400"))
        assertTrue(error.message!!.contains("Invalid session"))
    }

    private fun successfulEdgeResponse(): MockResponse {
        val json = """
            {
              "session_id": "session123",
              "transcript": "heard text",
              "response": "assistant reply",
              "query": "user query",
              "visual_context": "some-visual",
              "overlays": [
                {
                  "type": "box",
                  "content": "detected",
                  "text": "overlay text",
                  "box": [1, 2, 3, 4],
                  "boxes": [[5, 6, 7, 8]],
                  "conf": [0.9],
                  "by_word": [
                    {
                      "text": "word",
                      "box": [9, 10],
                      "conf": 0.8
                    }
                  ]
                }
              ],
              "metadata": {
                "cloud_offload": true,
                "redaction_summary": {
                  "faces_masked": 2,
                  "plates_masked": 1,
                  "total_masked_area": 3
                },
                "latency_ms": 42.5
              },
              "redaction": {
                "faces_masked": 1,
                "plates_masked": 0,
                "total_masked_area": 5
              },
              "status": "ok",
              "error": null
            }
        """
        return MockResponse().setResponseCode(200).setBody(json.trimIndent())
    }

    private fun assertParsedEdgeResponse(response: EdgeResponse) {
        assertEquals("session123", response.sessionId)
        assertEquals("heard text", response.transcript)
        assertEquals("assistant reply", response.response)
        assertEquals("user query", response.query)
        assertEquals("some-visual", response.visualContext)
        assertEquals("ok", response.status)
        assertNull(response.error)

        val overlay = assertNotNull(response.overlays).first()
        assertEquals("box", overlay.type)
        assertEquals("detected", overlay.content)
        assertEquals("overlay text", overlay.text)
        assertEquals(listOf(1, 2, 3, 4), overlay.box)
        assertEquals(listOf(listOf(5, 6, 7, 8)), overlay.boxes)
        assertEquals(listOf(0.9), overlay.conf)

        val overlayWord = assertNotNull(overlay.byWord).first()
        assertEquals("word", overlayWord.text)
        assertEquals(listOf(9, 10), overlayWord.box)
        assertEquals(0.8, overlayWord.conf)

        val metadata = assertNotNull(response.metadata)
        assertEquals(true, metadata.cloudOffload)
        assertEquals(42.5, metadata.latencyMs)

        val redactionSummary = assertNotNull(metadata.redactionSummary)
        assertEquals(2, redactionSummary.facesMasked)
        assertEquals(1, redactionSummary.platesMasked)
        assertEquals(3, redactionSummary.totalMaskedArea)

        val redaction = assertNotNull(response.redaction)
        assertEquals(1, redaction.facesMasked)
        assertEquals(0, redaction.platesMasked)
        assertEquals(5, redaction.totalMaskedArea)
    }
}

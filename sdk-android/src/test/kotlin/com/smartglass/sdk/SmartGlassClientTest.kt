package com.smartglass.sdk

import java.io.IOException
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
import kotlin.test.assertTrue

class SmartGlassClientTest {
    private lateinit var server: MockWebServer
    private lateinit var client: SmartGlassClient

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        client = SmartGlassClient(server.url("/").toString())
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun startSessionCreatesNewSessionAndReturnsHandle() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"test-session-123"}"""))

        val session = client.startSession()
        val recorded = server.takeRequest()

        assertEquals("/ingest", recorded.path)
        assertEquals("test-session-123", session.sessionId)

        // Verify the request body contains empty or minimal text
        val body = JSONObject(recorded.body.readUtf8())
        assertTrue(body.has("text"))
    }

    @Test
    fun sendAudioChunkAccumulatesAudioData() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"session-123"}"""))

        val session = client.startSession()
        server.takeRequest() // consume the startSession request

        // Send multiple audio chunks
        val audioData1 = "audio-chunk-1".toByteArray()
        val audioData2 = "audio-chunk-2".toByteArray()
        val timestamp1 = System.currentTimeMillis()
        val timestamp2 = timestamp1 + 100

        client.sendAudioChunk(session, audioData1, timestamp1)
        client.sendAudioChunk(session, audioData2, timestamp2)

        // No network request should be made during sendAudioChunk
        assertEquals(0, server.requestCount - 1)
    }

    @Test
    fun sendFrameAccumulatesFrameData() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"session-456"}"""))

        val session = client.startSession()
        server.takeRequest() // consume the startSession request

        // Send multiple frames
        val frameData1 = byteArrayOf(1, 2, 3, 4)
        val frameData2 = byteArrayOf(5, 6, 7, 8)
        val timestamp1 = System.currentTimeMillis()
        val timestamp2 = timestamp1 + 33

        client.sendFrame(session, frameData1, timestamp1)
        client.sendFrame(session, frameData2, timestamp2)

        // No network request should be made during sendFrame
        assertEquals(0, server.requestCount - 1)
    }

    @Test
    fun finalizeTurnSendsAccumulatedDataAndReturnsResult() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"session-789"}"""))
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """
                {
                  "response": "I see a coffee cup on the table.",
                  "actions": [
                    {
                      "type": "SHOW_TEXT",
                      "payload": {"message": "Coffee detected"}
                    }
                  ],
                  "raw": {
                    "latency_ms": 250,
                    "model": "gpt-4o-mini"
                  }
                }
                """.trimIndent(),
            ),
        )

        val session = client.startSession()
        server.takeRequest() // consume startSession

        // Send audio and frame
        client.sendAudioChunk(session, "audio-data".toByteArray(), System.currentTimeMillis())
        client.sendFrame(session, byteArrayOf(1, 2, 3), System.currentTimeMillis())

        // Finalize turn
        val result = client.finalizeTurn(session)
        val recorded = server.takeRequest()

        assertEquals("/answer", recorded.path)
        assertEquals("I see a coffee cup on the table.", result.response)
        assertEquals(1, result.actions.size)
        assertEquals("SHOW_TEXT", result.actions[0].type)
        assertEquals("Coffee detected", result.actions[0].payload["message"])

        val body = JSONObject(recorded.body.readUtf8())
        assertEquals("session-789", body.getString("session_id"))
        assertTrue(body.has("text"))
    }

    @Test
    fun finalizeTurnClearsSessionStateForNextTurn() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"session-clear"}"""))
        server.enqueue(successfulAgentResponse())
        server.enqueue(successfulAgentResponse())

        val session = client.startSession()
        server.takeRequest()

        // First turn
        client.sendAudioChunk(session, "turn1-audio".toByteArray(), System.currentTimeMillis())
        client.finalizeTurn(session)
        server.takeRequest()

        // Second turn - state should be cleared
        client.sendAudioChunk(session, "turn2-audio".toByteArray(), System.currentTimeMillis())
        val result = client.finalizeTurn(session)
        server.takeRequest()

        assertNotNull(result)
    }

    @Test
    fun finalizeTurnWithInvalidSessionThrowsException() = runBlocking {
        val invalidSession = SessionHandle("invalid-session-id")

        val error = assertFailsWith<IOException> {
            client.finalizeTurn(invalidSession)
        }

        assertTrue(error.message!!.contains("Invalid session"))
    }

    @Test
    fun sendAudioChunkWithInvalidSessionThrowsException() = runBlocking {
        val invalidSession = SessionHandle("invalid-session-id")

        val error = assertFailsWith<IOException> {
            client.sendAudioChunk(invalidSession, byteArrayOf(1, 2, 3), System.currentTimeMillis())
        }

        assertTrue(error.message!!.contains("Invalid session"))
    }

    @Test
    fun sendFrameWithInvalidSessionThrowsException() = runBlocking {
        val invalidSession = SessionHandle("invalid-session-id")

        val error = assertFailsWith<IOException> {
            client.sendFrame(invalidSession, byteArrayOf(1, 2, 3), System.currentTimeMillis())
        }

        assertTrue(error.message!!.contains("Invalid session"))
    }

    @Test
    fun nonSuccessResponseSurfacesErrorDetails() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"error-session"}"""))
        server.enqueue(MockResponse().setResponseCode(404).setBody("""{"detail":"Session not found"}"""))

        val session = client.startSession()
        server.takeRequest()

        client.sendAudioChunk(session, "audio".toByteArray(), System.currentTimeMillis())

        val error = assertFailsWith<IOException> {
            client.finalizeTurn(session)
        }

        assertTrue(error.message!!.contains("404"))
        assertTrue(error.message!!.contains("Session not found"))
    }

    @Test
    fun agentResultParsesActionsCorrectly() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"action-session"}"""))
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """
                {
                  "response": "Navigate to coffee shop",
                  "actions": [
                    {
                      "type": "NAVIGATE",
                      "payload": {"destination": "Starbucks"}
                    },
                    {
                      "type": "SHOW_TEXT",
                      "payload": {"message": "Opening maps"}
                    }
                  ],
                  "raw": {}
                }
                """.trimIndent(),
            ),
        )

        val session = client.startSession()
        server.takeRequest()

        val result = client.finalizeTurn(session)
        server.takeRequest()

        assertEquals("Navigate to coffee shop", result.response)
        assertEquals(2, result.actions.size)

        val navigateAction = result.actions[0]
        assertEquals("NAVIGATE", navigateAction.type)
        assertEquals("Starbucks", navigateAction.payload["destination"])

        val showTextAction = result.actions[1]
        assertEquals("SHOW_TEXT", showTextAction.type)
        assertEquals("Opening maps", showTextAction.payload["message"])
    }

    @Test
    fun emptyActionsArrayIsParsedCorrectly() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"empty-actions"}"""))
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """
                {
                  "response": "Just a response",
                  "actions": [],
                  "raw": {}
                }
                """.trimIndent(),
            ),
        )

        val session = client.startSession()
        server.takeRequest()

        val result = client.finalizeTurn(session)
        server.takeRequest()

        assertEquals("Just a response", result.response)
        assertEquals(0, result.actions.size)
    }

    @Test
    fun rawMetadataIsPreserved() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"raw-metadata"}"""))
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """
                {
                  "response": "Response text",
                  "actions": [],
                  "raw": {
                    "latency_ms": 123.45,
                    "model": "test-model",
                    "token_count": 42
                  }
                }
                """.trimIndent(),
            ),
        )

        val session = client.startSession()
        server.takeRequest()

        val result = client.finalizeTurn(session)
        server.takeRequest()

        assertTrue(result.raw.containsKey("latency_ms"))
        assertEquals("test-model", result.raw["model"])
    }

    @Test
    @Suppress("DEPRECATION")
    fun legacyStartSessionApiStillWorks() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"session_id":"legacy-123"}"""))

        val sessionId = client.startSession(text = "Hello", imagePath = null)

        assertEquals("legacy-123", sessionId)

        val recorded = server.takeRequest()
        val body = JSONObject(recorded.body.readUtf8())
        assertEquals("Hello", body.getString("text"))
    }

    @Test
    @Suppress("DEPRECATION")
    fun legacyAnswerApiStillWorks() = runBlocking {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """
                {
                  "response": "Legacy response",
                  "actions": [],
                  "raw": {}
                }
                """.trimIndent(),
            ),
        )

        val response = client.answer(sessionId = "legacy-456", text = "Question")

        assertEquals("Legacy response", response.response)

        val recorded = server.takeRequest()
        val body = JSONObject(recorded.body.readUtf8())
        assertEquals("legacy-456", body.getString("session_id"))
        assertEquals("Question", body.getString("text"))
    }

    private fun successfulAgentResponse(): MockResponse {
        val json = """
            {
              "response": "Sample response",
              "actions": [],
              "raw": {}
            }
        """
        return MockResponse().setResponseCode(200).setBody(json.trimIndent())
    }
}

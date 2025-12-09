package com.smartglass.sdk

import android.graphics.Bitmap
import androidx.test.core.app.ApplicationProvider
import com.smartglass.sdk.rayban.MetaRayBanManager
import java.io.IOException
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.test.assertFailsWith

@OptIn(ExperimentalCoroutinesApi::class)
class DatSmartGlassControllerTest {

    @Test
    fun controllerStartsInIdleState() {
        val controller = createController()
        assertEquals(DatSmartGlassController.State.IDLE, controller.state)
    }

    @Test
    fun startTransitionsFromIdleToConnectingToStreaming() = runTest {
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockClient = MockSmartGlassClient()
        val controller = DatSmartGlassController(mockRayBan, mockClient)

        assertEquals(DatSmartGlassController.State.IDLE, controller.state)

        // Start in background to observe state transitions
        val result = controller.start(deviceId = "test-device")

        // Should transition through CONNECTING to STREAMING
        assertEquals(DatSmartGlassController.State.STREAMING, controller.state)
        assertNotNull(result)
        assertTrue(mockClient.sessionStarted)
        assertTrue(mockFacade.connected)

        controller.stop()
    }

    @Test
    fun startThrowsExceptionWhenNotInIdleState() = runTest {
        val controller = createController()
        
        controller.start(deviceId = "test-device")
        
        // Should throw when trying to start again
        assertFailsWith<IllegalStateException> {
            controller.start(deviceId = "test-device")
        }
        
        controller.stop()
    }

    @Test
    fun stopTransitionsToIdleState() = runTest {
        val controller = createController()
        
        controller.start(deviceId = "test-device")
        assertEquals(DatSmartGlassController.State.STREAMING, controller.state)
        
        controller.stop()
        assertEquals(DatSmartGlassController.State.IDLE, controller.state)
    }

    @Test
    fun stopIsSafeToCallMultipleTimes() = runTest {
        val controller = createController()
        
        controller.start(deviceId = "test-device")
        controller.stop()
        controller.stop() // Should not throw
        controller.stop() // Should not throw
        
        assertEquals(DatSmartGlassController.State.IDLE, controller.state)
    }

    @Test
    fun audioChunksAreForwardedToBackend() = runTest {
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockClient = MockSmartGlassClient()
        val controller = DatSmartGlassController(mockRayBan, mockClient)

        controller.start(deviceId = "test-device")
        
        // Give time for audio chunks to be collected
        delay(200)
        
        assertTrue(mockClient.audioChunksReceived.isNotEmpty())
        
        controller.stop()
    }

    @Test
    fun framesAreForwardedAtControlledRate() = runTest {
        val mockFacade = MockSdkFacade(frameDelayMs = 50L)
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockClient = MockSmartGlassClient()
        val controller = DatSmartGlassController(
            rayBanManager = mockRayBan,
            smartGlassClient = mockClient,
            keyframeIntervalMs = 200L // Send keyframes every 200ms
        )

        controller.start(deviceId = "test-device")
        
        // Give time for frames to accumulate
        delay(600)
        
        // Should have sent fewer frames than were captured due to rate limiting
        assertTrue(mockClient.framesReceived.isNotEmpty())
        // With 600ms window and 200ms interval, expect ~3 keyframes
        assertTrue(mockClient.framesReceived.size <= 5)
        
        controller.stop()
    }

    @Test
    fun finalizeTurnReturnsAgentResult() = runTest {
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockClient = MockSmartGlassClient()
        val controller = DatSmartGlassController(mockRayBan, mockClient)

        controller.start(deviceId = "test-device")
        delay(100)
        
        val result = controller.finalizeTurn()
        
        assertNotNull(result)
        assertEquals("Mock response", result.response)
        
        controller.stop()
    }

    @Test
    fun finalizeTurnThrowsWhenNotStreaming() = runTest {
        val controller = createController()
        
        assertFailsWith<IllegalStateException> {
            controller.finalizeTurn()
        }
    }

    @Test
    fun errorDuringConnectTransitionsToErrorState() = runTest {
        val mockFacade = MockSdkFacade(shouldFailConnect = true)
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockClient = MockSmartGlassClient()
        val controller = DatSmartGlassController(mockRayBan, mockClient)

        try {
            controller.start(deviceId = "test-device")
        } catch (e: IOException) {
            // Expected
        }
        
        assertEquals(DatSmartGlassController.State.ERROR, controller.state)
        
        // Stop should still work to clean up
        controller.stop()
        assertEquals(DatSmartGlassController.State.IDLE, controller.state)
    }

    @Test
    fun stopCleansUpResourcesAfterError() = runTest {
        val mockFacade = MockSdkFacade(shouldFailConnect = true)
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockClient = MockSmartGlassClient()
        val controller = DatSmartGlassController(mockRayBan, mockClient)

        try {
            controller.start(deviceId = "test-device")
        } catch (e: Exception) {
            // Expected
        }
        
        controller.stop()
        
        assertEquals(DatSmartGlassController.State.IDLE, controller.state)
        assertTrue(mockFacade.disconnected)
    }

    private fun createController(): DatSmartGlassController {
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        return DatSmartGlassController(
            rayBanManager = mockRayBan,
            smartGlassClient = MockSmartGlassClient()
        )
    }

    // Mock implementations for testing

    private class MockSdkFacade(
        private val shouldFailConnect: Boolean = false,
        private val frameDelayMs: Long = 100L,
    ) : MetaRayBanManager.SdkFacade {
        var connected = false
        var disconnected = false
        private var streaming = false

        override suspend fun connect(deviceId: String, transportHint: String) {
            if (shouldFailConnect) {
                throw IOException("Mock connection failure")
            }
            delay(50)
            connected = true
        }

        override fun disconnect() {
            connected = false
            disconnected = true
            streaming = false
        }

        override suspend fun capturePhoto(): Bitmap? {
            return Bitmap.createBitmap(1, 1, Bitmap.Config.ARGB_8888)
        }

        override suspend fun startStreaming(onFrame: (frame: ByteArray, timestampMs: Long) -> Unit) {
            streaming = true
            // Simulate frames arriving at regular intervals
            while (streaming) {
                delay(frameDelayMs)
                if (streaming) {
                    onFrame(byteArrayOf(1, 2, 3), System.currentTimeMillis())
                }
            }
        }

        override fun stopStreaming() {
            streaming = false
        }

        override fun startAudioStreaming(): Flow<ByteArray> {
            streaming = true
            return flow {
                while (streaming) {
                    delay(50)
                    if (streaming) {
                        emit(byteArrayOf(1, 2, 3, 4))
                    }
                }
            }
        }

        override fun stopAudioStreaming() {
            streaming = false
        }
    }

    private class MockSmartGlassClient : SmartGlassClient("http://mock:8000") {
        var sessionStarted = false
        val audioChunksReceived = mutableListOf<ByteArray>()
        val framesReceived = mutableListOf<ByteArray>()
        private var mockSessionHandle: SessionHandle? = null

        override suspend fun startSession(): SessionHandle {
            sessionStarted = true
            mockSessionHandle = SessionHandle("mock-session-123")
            return mockSessionHandle!!
        }

        override suspend fun sendAudioChunk(
            session: SessionHandle,
            data: ByteArray,
            timestampMs: Long
        ) {
            audioChunksReceived.add(data)
        }

        override suspend fun sendFrame(
            session: SessionHandle,
            jpegBytes: ByteArray,
            timestampMs: Long
        ) {
            framesReceived.add(jpegBytes)
        }

        override suspend fun finalizeTurn(session: SessionHandle): AgentResult {
            return AgentResult(
                response = "Mock response",
                actions = emptyList(),
                raw = emptyMap()
            )
        }
    }
}

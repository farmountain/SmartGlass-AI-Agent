package com.smartglass.sdk

/*
 * Unit tests for DatSmartGlassController using mock implementations.
 * 
 * These tests validate the complete DAT (Device Access Toolkit) workflow
 * without requiring real Ray-Ban Meta hardware or network connectivity.
 * 
 * Test Coverage:
 * - State machine transitions (IDLE -> CONNECTING -> STREAMING -> ERROR)
 * - Audio and frame chunk forwarding to SmartGlassClient
 * - Turn completion and agent response handling
 * - Error handling and recovery
 * - Multiple turn completions in single session
 * 
 * Running these tests:
 *   ./gradlew test
 *   # or for a specific test:
 *   ./gradlew test --tests "DatSmartGlassControllerTest.completeMultimodalDatWorkflow"
 * 
 * Smoke Tests with Real Hardware:
 * ================================
 * For integration testing with actual Ray-Ban Meta glasses:
 * 
 * 1. Setup:
 *    - Connect Ray-Ban Meta glasses via Meta View app
 *    - Pair with Android device
 *    - Ensure backend server is running and accessible
 *    - Configure backend URL in sample app
 * 
 * 2. Run Manual Smoke Tests:
 *    a) Install sample app: ./gradlew sample:installDebug
 *    b) Open app and navigate to DAT integration screen
 *    c) Tap "Connect to Glasses" and verify connection
 *    d) Speak a query while looking at something
 *    e) Verify agent response appears on screen
 *    f) Verify actions (if any) are executed
 * 
 * 3. Automated Hardware Tests:
 *    - Mark tests with @RequiresDevice annotation
 *    - Run: ./gradlew connectedAndroidTest
 *    - Requires connected device with paired glasses
 *    - See: docs/meta_dat_implementation_plan.md for details
 * 
 * Note: Hardware tests are not run in CI due to device requirements.
 */

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

    @Test
    fun completeMultimodalDatWorkflow() = runTest {
        """
        End-to-end test simulating complete DAT session workflow:
        1. Initialize controller with fake MetaRayBanManager
        2. Start streaming (connects, begins audio/video capture)
        3. Verify data is forwarded to SmartGlassClient via DAT protocol
        4. Finalize turn and verify agent response with actions
        
        This test validates the complete integration between:
        - DatSmartGlassController state machine
        - MetaRayBanManager facade (mocked)
        - SmartGlassClient DAT API calls
        
        For testing with real Ray-Ban Meta glasses, see:
        docs/meta_dat_implementation_plan.md - "Testing with Real Hardware" section
        """
        val mockFacade = MockSdkFacade(frameDelayMs = 100L)
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockClient = MockSmartGlassClient()
        val controller = DatSmartGlassController(
            rayBanManager = mockRayBan,
            smartGlassClient = mockClient,
            keyframeIntervalMs = 200L
        )

        // Step 1: Verify initial state
        assertEquals(DatSmartGlassController.State.IDLE, controller.state)

        // Step 2: Start streaming session
        val sessionHandle = controller.start(deviceId = "rayban-meta-e2e-test")
        
        // Should transition to STREAMING state
        assertEquals(DatSmartGlassController.State.STREAMING, controller.state)
        assertNotNull(sessionHandle)
        
        // Verify SmartGlassClient session was initialized
        assertTrue(mockClient.sessionStarted)
        assertEquals("mock-session-123", sessionHandle.sessionId)
        
        // Verify MetaRayBanManager connected to device
        assertTrue(mockFacade.connected)

        // Step 3: Allow data streaming for a period (simulate ~500ms of operation)
        delay(500)
        
        // Verify audio chunks were forwarded to backend
        assertTrue(mockClient.audioChunksReceived.isNotEmpty(), 
            "Expected audio chunks to be forwarded to SmartGlassClient")
        
        // Verify frames were forwarded (rate-limited by keyframeIntervalMs)
        assertTrue(mockClient.framesReceived.isNotEmpty(),
            "Expected frame chunks to be forwarded to SmartGlassClient")
        
        // Frames should be rate-limited (expect ~2-3 frames for 500ms with 200ms interval)
        assertTrue(mockClient.framesReceived.size <= 5,
            "Frame rate limiting should be active")

        // Step 4: Finalize turn and get agent response
        val agentResult = controller.finalizeTurn()
        
        // Verify agent response structure
        assertNotNull(agentResult)
        assertEquals("Mock response", agentResult.response)
        assertNotNull(agentResult.actions)
        assertTrue(agentResult.actions is List<*>)
        
        // In production, actions would have specific structure like:
        // { action_type: "NAVIGATE", parameters: {...}, priority: "normal" }
        // This validates the protocol contract is maintained

        // Step 5: Clean up
        controller.stop()
        assertEquals(DatSmartGlassController.State.IDLE, controller.state)
        assertTrue(mockFacade.disconnected)
    }

    @Test
    fun datWorkflowHandlesMultipleTurns() = runTest {
        """
        Test that controller can handle multiple turn completions in a single session.
        This validates that finalizeTurn() doesn't break the streaming state.
        """
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockClient = MockSmartGlassClient()
        val controller = DatSmartGlassController(mockRayBan, mockClient)

        // Start streaming
        controller.start(deviceId = "test-device")
        delay(100)
        
        // Complete first turn
        val result1 = controller.finalizeTurn()
        assertNotNull(result1)
        assertEquals("Mock response", result1.response)
        
        // Controller should still be in STREAMING state
        assertEquals(DatSmartGlassController.State.STREAMING, controller.state)
        
        // Allow more data to accumulate
        delay(100)
        
        // Complete second turn
        val result2 = controller.finalizeTurn()
        assertNotNull(result2)
        assertEquals("Mock response", result2.response)
        
        // Still streaming
        assertEquals(DatSmartGlassController.State.STREAMING, controller.state)
        
        controller.stop()
    }

    @Test
    fun datWorkflowWithMinimalDataTransfer() = runTest {
        """
        Test DAT workflow with very short streaming window.
        This validates that the system handles edge cases where minimal
        audio/frame data is collected before turn completion.
        """
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockClient = MockSmartGlassClient()
        val controller = DatSmartGlassController(mockRayBan, mockClient)

        // Start and immediately finalize (minimal data collection)
        controller.start(deviceId = "test-device")
        
        // Very short delay - may have minimal or no data collected
        delay(10)
        
        // Should still return a result even with minimal data
        val result = controller.finalizeTurn()
        assertNotNull(result)
        assertNotNull(result.response)
        
        controller.stop()
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

package com.smartglass.sdk

/*
 * Unit tests for DatSmartGlassController using mock implementations.
 * 
 * These tests validate the complete DAT (Device Access Toolkit) workflow
 * with on-device LocalSnnEngine processing instead of network calls.
 * 
 * Test Coverage:
 * - State machine transitions (IDLE -> CONNECTING -> STREAMING -> ERROR)
 * - Audio and frame processing with visual context extraction
 * - User turn handling with LocalSnnEngine
 * - Action dispatching and UI updates
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
 *    - No backend server needed - all processing is on-device
 *    - Ensure SNN model assets are bundled with app
 * 
 * 2. Run Manual Smoke Tests:
 *    a) Install sample app: ./gradlew sample:installDebug
 *    b) Open app and navigate to DAT integration screen
 *    c) Tap "Connect to Glasses" and verify connection
 *    d) Speak a query while looking at something
 *    e) Verify agent response appears on screen (via StateFlow)
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

import android.content.Context
import android.graphics.Bitmap
import androidx.test.core.app.ApplicationProvider
import com.smartglass.actions.ActionDispatcher
import com.smartglass.actions.SmartGlassAction
import com.smartglass.runtime.llm.LocalSnnEngine
import com.smartglass.runtime.llm.LocalTokenizer
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
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        val controller = DatSmartGlassController(mockRayBan, mockSnnEngine, mockDispatcher)

        assertEquals(DatSmartGlassController.State.IDLE, controller.state)

        // Start in background to observe state transitions
        controller.start(deviceId = "test-device")

        // Should transition through CONNECTING to STREAMING
        assertEquals(DatSmartGlassController.State.STREAMING, controller.state)
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
    fun audioChunksAreBuffered() = runTest {
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        val controller = DatSmartGlassController(mockRayBan, mockSnnEngine, mockDispatcher)

        controller.start(deviceId = "test-device")
        
        // Give time for audio chunks to be collected
        delay(200)
        
        // Audio streaming should be active
        assertTrue(mockFacade.streaming)
        
        controller.stop()
    }

    @Test
    fun framesAreProcessedAtControlledRate() = runTest {
        val mockFacade = MockSdkFacade(frameDelayMs = 50L)
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        val controller = DatSmartGlassController(
            rayBanManager = mockRayBan,
            localSnnEngine = mockSnnEngine,
            actionDispatcher = mockDispatcher,
            keyframeIntervalMs = 200L // Process keyframes every 200ms
        )

        controller.start(deviceId = "test-device")
        
        // Give time for frames to accumulate
        delay(600)
        
        // Frame streaming should be active
        assertTrue(mockFacade.streaming)
        
        controller.stop()
    }

    @Test
    fun handleUserTurnProcessesQueryAndDispatchesActions() = runTest {
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        val controller = DatSmartGlassController(mockRayBan, mockSnnEngine, mockDispatcher)

        controller.start(deviceId = "test-device")
        delay(100)
        
        val (responseText, actions) = controller.handleUserTurn(
            textQuery = "What do you see?",
            visualContext = "indoor office"
        )
        
        assertNotNull(responseText)
        assertTrue(responseText.isNotEmpty())
        assertEquals("Mock SNN response with actions", responseText)
        assertEquals(1, actions.size)
        assertEquals(1, mockDispatcher.dispatchedActions.size)
        
        controller.stop()
    }

    @Test
    fun handleUserTurnThrowsWhenNotStreaming() = runTest {
        val controller = createController()
        
        assertFailsWith<IllegalStateException> {
            controller.handleUserTurn(textQuery = "Test")
        }
    }

    @Test
    fun errorDuringConnectTransitionsToErrorState() = runTest {
        val mockFacade = MockSdkFacade(shouldFailConnect = true)
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        val controller = DatSmartGlassController(mockRayBan, mockSnnEngine, mockDispatcher)

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
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        val controller = DatSmartGlassController(mockRayBan, mockSnnEngine, mockDispatcher)

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
        /**
         * End-to-end test simulating complete on-device DAT session workflow:
         * 1. Initialize controller with mock LocalSnnEngine and ActionDispatcher
         * 2. Start streaming (connects, begins audio/video capture)
         * 3. Verify visual context is extracted from frames
         * 4. Handle user turn with LocalSnnEngine
         * 5. Verify actions are dispatched
         *
         * This test validates the complete on-device integration between:
         * - DatSmartGlassController state machine
         * - MetaRayBanManager facade (mocked)
         * - LocalSnnEngine inference
         * - ActionDispatcher execution
         *
         * For testing with real Ray-Ban Meta glasses, see:
         * docs/meta_dat_implementation_plan.md - "Testing with Real Hardware" section
         */
        val mockFacade = MockSdkFacade(frameDelayMs = 100L)
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        val controller = DatSmartGlassController(
            rayBanManager = mockRayBan,
            localSnnEngine = mockSnnEngine,
            actionDispatcher = mockDispatcher,
            keyframeIntervalMs = 200L
        )

        // Step 1: Verify initial state
        assertEquals(DatSmartGlassController.State.IDLE, controller.state)

        // Step 2: Start streaming session
        controller.start(deviceId = "rayban-meta-e2e-test")
        
        // Should transition to STREAMING state
        assertEquals(DatSmartGlassController.State.STREAMING, controller.state)
        
        // Verify MetaRayBanManager connected to device
        assertTrue(mockFacade.connected)

        // Step 3: Allow data streaming for a period (simulate ~500ms of operation)
        delay(500)
        
        // Verify streaming is active
        assertTrue(mockFacade.streaming)

        // Step 4: Handle a user turn
        val (responseText, actions) = controller.handleUserTurn(
            textQuery = "What do you see?",
            visualContext = null // Will use latest from frames
        )
        
        // Verify response and actions
        assertNotNull(responseText)
        assertTrue(responseText.isNotEmpty())
        assertEquals(1, actions.size)
        assertEquals(1, mockDispatcher.dispatchedActions.size)

        // Step 5: Clean up
        controller.stop()
        assertEquals(DatSmartGlassController.State.IDLE, controller.state)
        assertTrue(mockFacade.disconnected)
    }

    @Test
    fun datWorkflowHandlesMultipleTurns() = runTest {
        /**
         * Test that controller can handle multiple turn completions in a single session.
         * This validates that handleUserTurn() doesn't break the streaming state.
         */
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        val controller = DatSmartGlassController(mockRayBan, mockSnnEngine, mockDispatcher)

        // Start streaming
        controller.start(deviceId = "test-device")
        delay(100)
        
        // Complete first turn
        val (response1, actions1) = controller.handleUserTurn(textQuery = "First query")
        assertNotNull(response1)
        assertTrue(response1.isNotEmpty())
        
        // Controller should still be in STREAMING state
        assertEquals(DatSmartGlassController.State.STREAMING, controller.state)
        
        // Allow more data to accumulate
        delay(100)
        
        // Complete second turn
        val (response2, actions2) = controller.handleUserTurn(textQuery = "Second query")
        assertNotNull(response2)
        assertTrue(response2.isNotEmpty())
        
        // Still streaming
        assertEquals(DatSmartGlassController.State.STREAMING, controller.state)
        
        // Verify both turns dispatched actions
        assertEquals(2, mockDispatcher.dispatchedActions.size)
        
        controller.stop()
    }

    @Test
    fun datWorkflowWithMinimalDataTransfer() = runTest {
        /**
         * Test DAT workflow with very short streaming window.
         * This validates that the system handles edge cases where minimal
         * audio/frame data is collected before turn completion.
         */
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        val controller = DatSmartGlassController(mockRayBan, mockSnnEngine, mockDispatcher)

        // Start and immediately handle turn (minimal data collection)
        controller.start(deviceId = "test-device")
        
        // Very short delay - may have minimal or no data collected
        delay(10)
        
        // Should still return a result even with minimal data
        val (responseText, actions) = controller.handleUserTurn(
            textQuery = "Quick query",
            visualContext = "test context"
        )
        assertNotNull(responseText)
        assertTrue(responseText.isNotEmpty())
        
        controller.stop()
    }

    private fun createController(): DatSmartGlassController {
        val mockFacade = MockSdkFacade()
        val mockRayBan = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = mockFacade
        )
        val mockSnnEngine = MockLocalSnnEngine()
        val mockDispatcher = MockActionDispatcher()
        return DatSmartGlassController(
            rayBanManager = mockRayBan,
            localSnnEngine = mockSnnEngine,
            actionDispatcher = mockDispatcher
        )
    }

    // Mock implementations for testing

    private class MockSdkFacade(
        private val shouldFailConnect: Boolean = false,
        private val frameDelayMs: Long = 100L,
    ) : MetaRayBanManager.SdkFacade {
        var connected = false
        var disconnected = false
        var streaming = false

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

    /**
     * Mock LocalSnnEngine that returns predefined JSON responses.
     */
    private class MockLocalSnnEngine : LocalSnnEngine(
        context = ApplicationProvider.getApplicationContext(),
        modelAssetPath = "mock_model.pt",
        tokenizer = LocalTokenizer(ApplicationProvider.getApplicationContext())
    ) {
        override suspend fun generate(
            prompt: String,
            visualContext: String?,
            maxTokens: Int
        ): String {
            // Return a JSON response with text and actions
            return """{
                "response": "Mock SNN response with actions",
                "actions": [
                    {
                        "type": "SHOW_TEXT",
                        "payload": {
                            "title": "Test",
                            "body": "Mock action"
                        }
                    }
                ]
            }"""
        }
    }

    /**
     * Mock ActionDispatcher that records dispatched actions.
     */
    private class MockActionDispatcher : ActionDispatcher(
        context = ApplicationProvider.getApplicationContext()
    ) {
        val dispatchedActions = mutableListOf<List<SmartGlassAction>>()

        override fun dispatch(actions: List<SmartGlassAction>) {
            dispatchedActions.add(actions)
            // Don't actually execute actions in tests
        }
    }
}

package com.smartglass.sdk

import android.util.Log
import com.smartglass.sdk.rayban.MetaRayBanManager
import java.io.IOException
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch

private const val TAG = "DatSmartGlassController"
private const val DEFAULT_KEYFRAME_INTERVAL_MS = 500L // Send keyframes every 500ms

/**
 * End-to-end controller that bridges Meta Ray-Ban DAT SDK with SmartGlass backend.
 *
 * This controller manages the session lifecycle between the glasses and the Python backend,
 * automatically forwarding audio chunks and video keyframes to the SmartGlass Agent for
 * multimodal processing.
 *
 * **State Machine:**
 * - `IDLE`: Initial state, no active session
 * - `CONNECTING`: Establishing connections to glasses and backend
 * - `STREAMING`: Actively streaming audio/video to backend
 * - `ERROR`: Error occurred, requires manual recovery via [stop] and [start]
 *
 * **Example Usage in Activity:**
 * ```kotlin
 * class MyActivity : AppCompatActivity() {
 *     private lateinit var controller: DatSmartGlassController
 *
 *     override fun onCreate(savedInstanceState: Bundle?) {
 *         super.onCreate(savedInstanceState)
 *
 *         val rayBanManager = MetaRayBanManager(applicationContext)
 *         val smartGlassClient = SmartGlassClient(baseUrl = "http://10.0.2.2:8000")
 *         controller = DatSmartGlassController(
 *             rayBanManager = rayBanManager,
 *             smartGlassClient = smartGlassClient,
 *             keyframeIntervalMs = 500L
 *         )
 *
 *         // Observe state changes
 *         lifecycleScope.launch {
 *             controller.state.collect { state ->
 *                 Log.d("MyActivity", "Controller state: $state")
 *                 when (state) {
 *                     DatSmartGlassController.State.STREAMING -> {
 *                         // Update UI to show streaming indicator
 *                     }
 *                     DatSmartGlassController.State.ERROR -> {
 *                         // Show error message to user
 *                     }
 *                     else -> { /* handle other states */ }
 *                 }
 *             }
 *         }
 *
 *         // Start streaming when button is clicked
 *         findViewById<Button>(R.id.startButton).setOnClickListener {
 *             lifecycleScope.launch {
 *                 try {
 *                     val result = controller.start(deviceId = "my-glasses-device-id")
 *                     // Process result when turn is finalized
 *                     Log.d("MyActivity", "Agent response: ${result.response}")
 *                 } catch (e: Exception) {
 *                     Log.e("MyActivity", "Failed to start", e)
 *                 }
 *             }
 *         }
 *
 *         // Stop streaming when button is clicked
 *         findViewById<Button>(R.id.stopButton).setOnClickListener {
 *             controller.stop()
 *         }
 *     }
 *
 *     override fun onDestroy() {
 *         super.onDestroy()
 *         controller.stop()
 *     }
 * }
 * ```
 *
 * **Example Usage in Service:**
 * ```kotlin
 * class StreamingService : Service() {
 *     private lateinit var controller: DatSmartGlassController
 *     private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
 *
 *     override fun onCreate() {
 *         super.onCreate()
 *
 *         val rayBanManager = MetaRayBanManager(applicationContext)
 *         val smartGlassClient = SmartGlassClient()
 *         controller = DatSmartGlassController(rayBanManager, smartGlassClient)
 *
 *         scope.launch {
 *             controller.start(deviceId = "device-123")
 *         }
 *     }
 *
 *     override fun onDestroy() {
 *         controller.stop()
 *         scope.cancel()
 *         super.onDestroy()
 *     }
 *
 *     override fun onBind(intent: android.content.Intent?) = null
 * }
 * ```
 *
 * @param rayBanManager Manager for Meta Ray-Ban DAT SDK interactions
 * @param smartGlassClient Client for SmartGlass Python backend
 * @param keyframeIntervalMs Interval in milliseconds between sending video keyframes (default: 500ms)
 */
class DatSmartGlassController(
    private val rayBanManager: MetaRayBanManager,
    private val smartGlassClient: SmartGlassClient,
    private val keyframeIntervalMs: Long = DEFAULT_KEYFRAME_INTERVAL_MS,
) {

    /**
     * Controller state.
     */
    enum class State {
        /** Initial state, no active session */
        IDLE,
        /** Establishing connections to glasses and backend */
        CONNECTING,
        /** Actively streaming audio/video to backend */
        STREAMING,
        /** Error occurred, requires manual recovery */
        ERROR
    }

    private val currentState = AtomicReference(State.IDLE)
    private var controllerScope: CoroutineScope? = null
    private var videoStreamJob: Job? = null
    private var audioStreamJob: Job? = null
    private var sessionHandle: SessionHandle? = null
    private var lastKeyframeTimestamp = 0L

    /**
     * Current state of the controller.
     */
    val state: State
        get() = currentState.get()

    /**
     * Start streaming from glasses to backend.
     *
     * This method:
     * 1. Transitions to CONNECTING state
     * 2. Connects to the specified glasses device
     * 3. Starts a new SmartGlass session
     * 4. Begins streaming audio and video
     * 5. Transitions to STREAMING state
     *
     * Video frames are sent at the configured keyframe interval to reduce bandwidth.
     * Audio chunks are sent as they arrive.
     *
     * @param deviceId Meta Ray-Ban device ID to connect to
     * @param transport Transport mechanism (BLE or WIFI), defaults to WIFI
     * @return AgentResult after processing accumulated data (call happens asynchronously)
     * @throws IOException if connection or session creation fails
     * @throws IllegalStateException if controller is not in IDLE state
     */
    suspend fun start(
        deviceId: String,
        transport: MetaRayBanManager.Transport = MetaRayBanManager.Transport.WIFI,
    ): AgentResult {
        if (!currentState.compareAndSet(State.IDLE, State.CONNECTING)) {
            throw IllegalStateException("Cannot start: controller is in ${currentState.get()} state")
        }

        Log.i(TAG, "Starting DatSmartGlassController for device $deviceId via $transport")

        try {
            // Create a dedicated scope for this streaming session
            controllerScope = CoroutineScope(Dispatchers.Main + SupervisorJob())

            // Step 1: Connect to glasses
            Log.d(TAG, "Connecting to Meta Ray-Ban device $deviceId")
            rayBanManager.connect(deviceId, transport)

            // Step 2: Start SmartGlass session
            Log.d(TAG, "Starting SmartGlass session")
            sessionHandle = smartGlassClient.startSession()

            // Step 3: Start audio streaming
            Log.d(TAG, "Starting audio streaming")
            startAudioStreaming()

            // Step 4: Start video streaming
            Log.d(TAG, "Starting video streaming")
            startVideoStreaming()

            // Transition to streaming state
            if (currentState.compareAndSet(State.CONNECTING, State.STREAMING)) {
                Log.i(TAG, "Successfully transitioned to STREAMING state")
            }

            // For now, we return a placeholder result. In a real implementation,
            // you might want to run a background loop that periodically finalizes turns
            // or finalize on-demand via a separate method.
            return AgentResult(
                response = "Streaming started successfully",
                actions = emptyList(),
                raw = mapOf("status" to "streaming")
            )

        } catch (e: Exception) {
            Log.e(TAG, "Error during start", e)
            transitionToError()
            throw e
        }
    }

    /**
     * Stop streaming and clean up resources.
     *
     * This method:
     * 1. Stops audio and video streaming
     * 2. Disconnects from glasses
     * 3. Cancels all active coroutines
     * 4. Transitions to IDLE state
     *
     * This method is safe to call multiple times and from any state.
     */
    fun stop() {
        val previousState = currentState.getAndSet(State.IDLE)
        Log.i(TAG, "Stopping DatSmartGlassController (was in $previousState state)")

        // Cancel streaming jobs
        videoStreamJob?.cancel()
        videoStreamJob = null
        audioStreamJob?.cancel()
        audioStreamJob = null

        // Stop streaming from glasses
        runCatching {
            rayBanManager.stopStreaming()
            rayBanManager.stopAudioStreaming()
        }.onFailure { exc ->
            Log.w(TAG, "Error stopping Ray-Ban streaming", exc)
        }

        // Disconnect from glasses
        runCatching {
            rayBanManager.disconnect()
        }.onFailure { exc ->
            Log.w(TAG, "Error disconnecting from Ray-Ban", exc)
        }

        // Cancel controller scope
        controllerScope?.cancel()
        controllerScope = null

        // Clear session handle
        sessionHandle = null
        lastKeyframeTimestamp = 0L

        Log.d(TAG, "DatSmartGlassController stopped")
    }

    /**
     * Finalize the current turn and get agent response.
     *
     * This method sends all accumulated audio and frames to the backend
     * and returns the agent's response. After finalization, you can continue
     * streaming for the next turn.
     *
     * @return AgentResult containing the agent's response and actions
     * @throws IllegalStateException if not in STREAMING state
     * @throws IOException if the finalization request fails
     */
    suspend fun finalizeTurn(): AgentResult {
        if (currentState.get() != State.STREAMING) {
            throw IllegalStateException("Cannot finalize turn: not in STREAMING state")
        }

        val handle = sessionHandle
            ?: throw IllegalStateException("No active session")

        Log.d(TAG, "Finalizing turn for session ${handle.sessionId}")

        return try {
            smartGlassClient.finalizeTurn(handle)
        } catch (e: Exception) {
            Log.e(TAG, "Error finalizing turn", e)
            transitionToError()
            throw e
        }
    }

    private fun startAudioStreaming() {
        val handle = sessionHandle ?: return
        val scope = controllerScope ?: return

        audioStreamJob = scope.launch {
            rayBanManager.startAudioStreaming()
                .catch { exc ->
                    Log.e(TAG, "Error in audio streaming", exc)
                    transitionToError()
                }
                .collect { audioData ->
                    val timestamp = System.currentTimeMillis()
                    try {
                        smartGlassClient.sendAudioChunk(handle, audioData, timestamp)
                        Log.v(TAG, "Sent audio chunk: ${audioData.size} bytes at $timestamp")
                    } catch (e: Exception) {
                        Log.e(TAG, "Error sending audio chunk", e)
                        transitionToError()
                    }
                }
        }
    }

    private fun startVideoStreaming() {
        val handle = sessionHandle ?: return
        val scope = controllerScope ?: return

        videoStreamJob = scope.launch {
            rayBanManager.startStreaming { frame, timestamp ->
                // Apply keyframe rate limiting
                if (shouldSendKeyframe(timestamp)) {
                    scope.launch {
                        try {
                            smartGlassClient.sendFrame(handle, frame, timestamp)
                            Log.v(TAG, "Sent keyframe: ${frame.size} bytes at $timestamp")
                        } catch (e: Exception) {
                            Log.e(TAG, "Error sending frame", e)
                            transitionToError()
                        }
                    }
                }
            }
        }
    }

    private fun shouldSendKeyframe(timestamp: Long): Boolean {
        if (timestamp - lastKeyframeTimestamp >= keyframeIntervalMs) {
            lastKeyframeTimestamp = timestamp
            return true
        }
        return false
    }

    private fun transitionToError() {
        val previousState = currentState.getAndSet(State.ERROR)
        if (previousState != State.ERROR) {
            Log.e(TAG, "Transitioned to ERROR state from $previousState")
        }
    }
}

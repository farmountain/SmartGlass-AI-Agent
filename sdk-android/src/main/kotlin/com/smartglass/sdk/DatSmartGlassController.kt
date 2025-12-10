package com.smartglass.sdk

import android.util.Log
import com.smartglass.actions.ActionDispatcher
import com.smartglass.actions.SmartGlassAction
import com.smartglass.runtime.llm.LocalSnnEngine
import com.smartglass.sdk.rayban.MetaRayBanManager
import java.io.IOException
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

private const val TAG = "DatSmartGlassController"
private const val DEFAULT_KEYFRAME_INTERVAL_MS = 500L // Send keyframes every 500ms
private const val MAX_RESPONSE_LENGTH = 200 // Maximum length for response text display

/**
 * End-to-end controller that bridges Meta Ray-Ban DAT SDK with on-device SNN inference.
 *
 * This controller manages the session lifecycle between the glasses and local processing,
 * using LocalSnnEngine for on-device inference and ActionDispatcher for executing actions.
 * No network calls are made - everything runs locally.
 *
 * **State Machine:**
 * - `IDLE`: Initial state, no active session
 * - `CONNECTING`: Establishing connections to glasses
 * - `STREAMING`: Actively streaming audio/video and processing locally
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
 *         val tokenizer = LocalTokenizer(applicationContext, "snn_student_ts.pt")
 *         val snnEngine = LocalSnnEngine(applicationContext, "snn_student_ts.pt", tokenizer)
 *         val actionDispatcher = ActionDispatcher(applicationContext)
 *         
 *         controller = DatSmartGlassController(
 *             rayBanManager = rayBanManager,
 *             localSnnEngine = snnEngine,
 *             actionDispatcher = actionDispatcher,
 *             keyframeIntervalMs = 500L
 *         )
 *
 *         // Observe agent responses
 *         lifecycleScope.launch {
 *             controller.agentResponse.collect { response ->
 *                 textView.text = response
 *             }
 *         }
 *
 *         // Start streaming when button is clicked
 *         findViewById<Button>(R.id.startButton).setOnClickListener {
 *             lifecycleScope.launch {
 *                 try {
 *                     controller.start(deviceId = "my-glasses-device-id")
 *                 } catch (e: Exception) {
 *                     Log.e("MyActivity", "Failed to start", e)
 *                 }
 *             }
 *         }
 *
 *         // Handle user turn
 *         findViewById<Button>(R.id.queryButton).setOnClickListener {
 *             lifecycleScope.launch {
 *                 controller.handleUserTurn(textQuery = "What do you see?", visualContext = null)
 *             }
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
 * @param rayBanManager Manager for Meta Ray-Ban DAT SDK interactions
 * @param localSnnEngine On-device SNN inference engine
 * @param actionDispatcher Dispatcher for executing actions locally
 * @param keyframeIntervalMs Interval in milliseconds between processing video keyframes (default: 500ms)
 */
class DatSmartGlassController(
    private val rayBanManager: MetaRayBanManager,
    private val localSnnEngine: LocalSnnEngine,
    private val actionDispatcher: ActionDispatcher,
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
    private var lastKeyframeTimestamp = 0L
    
    // Buffer for storing recent visual context
    private var latestVisualContext: String? = null
    
    // StateFlow for exposing agent responses to UI
    private val _agentResponse = MutableStateFlow<String>("")
    val agentResponse: StateFlow<String> = _agentResponse.asStateFlow()

    /**
     * Current state of the controller.
     */
    val state: State
        get() = currentState.get()

    /**
     * Start streaming from glasses and processing locally.
     *
     * This method:
     * 1. Transitions to CONNECTING state
     * 2. Connects to the specified glasses device
     * 3. Begins streaming audio and video
     * 4. Processes frames locally to build visual context
     * 5. Transitions to STREAMING state
     *
     * Video frames are processed at the configured keyframe interval.
     * Audio chunks are buffered as they arrive.
     *
     * @param deviceId Meta Ray-Ban device ID to connect to
     * @param transport Transport mechanism (BLE or WIFI), defaults to WIFI
     * @throws IOException if connection fails
     * @throws IllegalStateException if controller is not in IDLE state
     */
    suspend fun start(
        deviceId: String,
        transport: MetaRayBanManager.Transport = MetaRayBanManager.Transport.WIFI,
    ) {
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

            // Step 2: Start audio streaming
            Log.d(TAG, "Starting audio streaming")
            startAudioStreaming()

            // Step 3: Start video streaming
            Log.d(TAG, "Starting video streaming")
            startVideoStreaming()

            // Transition to streaming state
            if (currentState.compareAndSet(State.CONNECTING, State.STREAMING)) {
                Log.i(TAG, "Successfully transitioned to STREAMING state")
            }

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

        // Clear state
        latestVisualContext = null
        lastKeyframeTimestamp = 0L

        Log.d(TAG, "DatSmartGlassController stopped")
    }

    /**
     * Handle a user turn with optional text query and visual context.
     *
     * This method:
     * 1. Builds a prompt combining text query and visual context
     * 2. Calls LocalSnnEngine to generate a JSON response
     * 3. Parses the JSON to extract response text and actions
     * 4. Updates the UI via StateFlow with the response text
     * 5. Dispatches actions via ActionDispatcher
     *
     * All processing happens on-device without network calls.
     *
     * @param textQuery Optional text query from user (e.g., from voice or UI)
     * @param visualContext Optional visual context (if null, uses latest from frames)
     * @return Pair of response text and list of actions executed
     * @throws IllegalStateException if not in STREAMING state
     */
    suspend fun handleUserTurn(
        textQuery: String?,
        visualContext: String? = null
    ): Pair<String, List<SmartGlassAction>> = withContext(Dispatchers.Default) {
        if (currentState.get() != State.STREAMING) {
            throw IllegalStateException("Cannot handle user turn: not in STREAMING state")
        }

        try {
            // Use provided visual context or fall back to latest from frames
            val effectiveVisualContext = visualContext ?: latestVisualContext
            
            // Build the prompt
            val prompt = buildPrompt(textQuery, effectiveVisualContext)
            
            Log.d(TAG, "Handling user turn with prompt: $prompt")
            
            // Call LocalSnnEngine to generate response
            val rawResponse = localSnnEngine.generate(
                prompt = prompt,
                visualContext = effectiveVisualContext,
                maxTokens = 128
            )
            
            Log.d(TAG, "SNN generated response: $rawResponse")
            
            // Parse JSON response
            val (responseText, actions) = parseResponse(rawResponse)
            
            // Update UI via StateFlow
            _agentResponse.value = responseText
            
            // Dispatch actions
            actionDispatcher.dispatch(actions)
            
            Log.i(TAG, "User turn completed: $responseText, ${actions.size} actions dispatched")
            
            return@withContext Pair(responseText, actions)
            
        } catch (e: Exception) {
            Log.e(TAG, "Error handling user turn", e)
            val errorMessage = "I'm having trouble processing that right now."
            _agentResponse.value = errorMessage
            return@withContext Pair(errorMessage, emptyList())
        }
    }
    
    /**
     * Build a prompt string from text query and visual context.
     */
    private fun buildPrompt(textQuery: String?, visualContext: String?): String {
        val parts = mutableListOf<String>()
        
        if (!textQuery.isNullOrBlank()) {
            parts.add("User: $textQuery")
        }
        
        if (!visualContext.isNullOrBlank()) {
            parts.add("[Visual Context: $visualContext]")
        }
        
        if (parts.isEmpty()) {
            parts.add("User: Hello")
        }
        
        return parts.joinToString("\n")
    }
    
    /**
     * Parse the SNN response to extract text and actions.
     * 
     * Expected JSON format:
     * {
     *   "response": "Here's what I see...",
     *   "actions": [
     *     {"type": "SHOW_TEXT", "payload": {"title": "...", "body": "..."}},
     *     ...
     *   ]
     * }
     */
    private fun parseResponse(rawResponse: String): Pair<String, List<SmartGlassAction>> {
        return try {
            // Try to parse as JSON
            val json = JSONObject(rawResponse)
            val responseText = json.optString("response", "")
            val actionsArray = json.optJSONArray("actions")
            
            val actions = if (actionsArray != null) {
                // Parse actions directly from JSONArray without string conversion
                parseActionsFromJson(actionsArray)
            } else {
                emptyList()
            }
            
            // If no response text found, use the raw response as fallback
            val finalText = if (responseText.isBlank()) {
                rawResponse.take(MAX_RESPONSE_LENGTH)
            } else {
                responseText
            }
            
            Pair(finalText, actions)
            
        } catch (e: Exception) {
            Log.w(TAG, "Failed to parse JSON response, using raw text", e)
            // If not valid JSON, treat entire response as text
            Pair(rawResponse.take(MAX_RESPONSE_LENGTH), emptyList())
        }
    }
    
    /**
     * Parse actions from JSONArray without intermediate string conversion.
     */
    private fun parseActionsFromJson(jsonArray: org.json.JSONArray): List<SmartGlassAction> {
        val actions = mutableListOf<SmartGlassAction>()
        for (i in 0 until jsonArray.length()) {
            val actionObj = jsonArray.optJSONObject(i) ?: continue
            val type = actionObj.optString("type", "").uppercase()
            val payload = actionObj.optJSONObject("payload")
            
            if (type.isBlank() || payload == null) continue
            
            val action = when (type) {
                "SHOW_TEXT" -> {
                    val title = payload.optString("title", "")
                    val body = payload.optString("body", "")
                    if (title.isNotBlank() && body.isNotBlank()) {
                        SmartGlassAction.ShowText(title, body)
                    } else null
                }
                "TTS_SPEAK" -> {
                    val text = payload.optString("text", "")
                    if (text.isNotBlank()) SmartGlassAction.TtsSpeak(text) else null
                }
                "NAVIGATE" -> {
                    val destinationLabel = payload.optString("destinationLabel", null)
                    val latitude = if (payload.has("latitude")) payload.optDouble("latitude") else null
                    val longitude = if (payload.has("longitude")) payload.optDouble("longitude") else null
                    if (destinationLabel != null || (latitude != null && longitude != null)) {
                        SmartGlassAction.Navigate(destinationLabel, latitude, longitude)
                    } else null
                }
                "REMEMBER_NOTE" -> {
                    val note = payload.optString("note", "")
                    if (note.isNotBlank()) SmartGlassAction.RememberNote(note) else null
                }
                "OPEN_APP" -> {
                    val packageName = payload.optString("packageName", "")
                    if (packageName.isNotBlank()) SmartGlassAction.OpenApp(packageName) else null
                }
                "SYSTEM_HINT" -> {
                    val hint = payload.optString("hint", "")
                    if (hint.isNotBlank()) SmartGlassAction.SystemHint(hint) else null
                }
                else -> {
                    Log.w(TAG, "Unknown action type: $type")
                    null
                }
            }
            
            if (action != null) {
                actions.add(action)
            }
        }
        return actions
    }

    private fun startAudioStreaming() {
        val scope = controllerScope ?: return

        audioStreamJob = scope.launch {
            rayBanManager.startAudioStreaming()
                .catch { exc ->
                    Log.e(TAG, "Error in audio streaming", exc)
                    transitionToError()
                }
                .collect { audioData ->
                    // Audio data is buffered for potential future use
                    // Currently we don't process audio chunks directly
                    // Voice commands would be handled via textQuery parameter in handleUserTurn
                    Log.v(TAG, "Received audio chunk: ${audioData.size} bytes")
                }
        }
    }

    private fun startVideoStreaming() {
        val scope = controllerScope ?: return

        videoStreamJob = scope.launch {
            rayBanManager.startStreaming { frame, timestamp ->
                // Apply keyframe rate limiting
                if (shouldSendKeyframe(timestamp)) {
                    try {
                        // Process frame to extract visual context
                        val sceneLabel = extractSceneLabel(frame)
                        latestVisualContext = sceneLabel
                        Log.v(TAG, "Processed keyframe at $timestamp: $sceneLabel")
                    } catch (e: Exception) {
                        Log.e(TAG, "Error processing frame", e)
                    }
                }
            }
        }
    }
    
    /**
     * Extract scene label from frame data.
     * 
     * This is a lightweight heuristic for determining visual context.
     * In a production system, this could use:
     * - ML Kit for object detection
     * - TensorFlow Lite for scene classification
     * - Simple brightness/color analysis
     * 
     * For now, provides basic placeholder context.
     */
    private fun extractSceneLabel(frameBytes: ByteArray): String {
        // Simple heuristic based on frame size
        // In production, this would use actual image analysis
        return when {
            frameBytes.isEmpty() -> "no visual input"
            frameBytes.size < 10000 -> "low quality frame"
            frameBytes.size < 50000 -> "indoor scene"
            else -> "outdoor scene"
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

package com.smartglass.sample

import android.app.Application
import android.content.Context
import android.speech.tts.TextToSpeech
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.smartglass.actions.ActionDispatcher
import com.smartglass.actions.SmartGlassAction
import com.smartglass.runtime.llm.LocalSnnEngine
import com.smartglass.runtime.llm.LocalTokenizer
import com.smartglass.sample.ui.ConnectionState
import com.smartglass.sample.ui.Message
import com.smartglass.sample.ui.StreamingMetrics
import com.smartglass.sdk.rayban.MetaRayBanManager
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.Locale

/**
 * ViewModel for managing SmartGlass conversation state and business logic.
 *
 * Responsibilities:
 * - Manage connection lifecycle with smart glasses
 * - Process video frames and generate AI responses
 * - Execute actions via ActionDispatcher
 * - Track streaming metrics
 */
class SmartGlassViewModel(application: Application) : AndroidViewModel(application) {
    private val context: Context = application.applicationContext

    companion object {
        private const val TAG = "SmartGlassViewModel"
        private const val SNN_MODEL_ASSET_PATH = "snn_student_ts.pt"
        private const val FRAME_PROCESSING_INTERVAL = 5 // Process every 5th frame (~5fps at 30fps stream)
        private const val METRICS_UPDATE_INTERVAL = 30 // Update metrics every 30 frames
        private const val RECENT_MESSAGE_TIMEOUT_MS = 5000L // 5 seconds
        private const val MOCK_DEVICE_ID = "MOCK-001" // Mock device for testing without real hardware
        
        /**
         * Regex pattern for extracting JSON action arrays from AI responses.
         * Matches: ```json [...] ``` or ``` [...] ```
         */
        private val JSON_ACTION_PATTERN = """```(?:json)?\s*(\[.*?\])\s*```""".toRegex(RegexOption.DOT_MATCHES_ALL)
    }

    // Dependencies
    private val rayBanManager = MetaRayBanManager(context)
    private var localSnnEngine: LocalSnnEngine? = null
    private var actionDispatcher: ActionDispatcher? = null
    private var textToSpeech: TextToSpeech? = null

    // State flows
    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _streamingMetrics = MutableStateFlow<StreamingMetrics?>(null)
    val streamingMetrics: StateFlow<StreamingMetrics?> = _streamingMetrics.asStateFlow()

    // Streaming state
    private var streamingJob: Job? = null
    private var frameCount = 0
    private var startTime = 0L

    init {
        initializeDependencies()
    }

    private fun initializeDependencies() {
        // Initialize TextToSpeech
        textToSpeech = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                textToSpeech?.language = Locale.getDefault()
                Log.d(TAG, "TextToSpeech initialized successfully")
                
                // Now that TTS is ready, initialize ActionDispatcher
                actionDispatcher = ActionDispatcher(context, textToSpeech)
            } else {
                Log.w(TAG, "TextToSpeech initialization failed")
                // Initialize dispatcher without TTS
                actionDispatcher = ActionDispatcher(context, null)
            }
        }

        // Initialize LocalSnnEngine (lazy, as it may not be needed immediately)
        viewModelScope.launch {
            try {
                val tokenizer = LocalTokenizer(context, SNN_MODEL_ASSET_PATH)
                localSnnEngine = LocalSnnEngine(context, SNN_MODEL_ASSET_PATH, tokenizer)
                Log.d(TAG, "LocalSnnEngine initialized successfully")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to initialize LocalSnnEngine", e)
            }
        }
    }

    /**
     * Connect to smart glasses and start streaming.
     */
    fun connect() {
        viewModelScope.launch {
            try {
                _connectionState.value = ConnectionState.CONNECTING

                // Use mock device for testing (no real hardware required)
                rayBanManager.connect(MOCK_DEVICE_ID, MetaRayBanManager.Transport.WIFI)

                _connectionState.value = ConnectionState.CONNECTED

                // Add system message
                addMessage(
                    Message(
                        content = "Connected to smart glasses. Start streaming to begin.",
                        isFromUser = false
                    )
                )

                // Automatically start streaming
                startStreaming()

            } catch (e: Exception) {
                Log.e(TAG, "Connection failed", e)
                _connectionState.value = ConnectionState.ERROR
                addMessage(
                    Message(
                        content = "Connection failed: ${e.message}",
                        isFromUser = false
                    )
                )
            }
        }
    }

    /**
     * Start video streaming from glasses.
     */
    private fun startStreaming() {
        _connectionState.value = ConnectionState.STREAMING
        startTime = System.currentTimeMillis()
        frameCount = 0

        streamingJob = viewModelScope.launch {
            try {
                rayBanManager.startStreaming { videoFrame, timestamp ->
                    frameCount++

                    // Update metrics every METRICS_UPDATE_INTERVAL frames
                    if (frameCount % METRICS_UPDATE_INTERVAL == 0) {
                        val elapsedSeconds = (System.currentTimeMillis() - startTime) / 1000f
                        val fps = if (elapsedSeconds > 0) frameCount / elapsedSeconds else 0f
                        _streamingMetrics.value = StreamingMetrics(
                            fps = fps,
                            latencyMs = (System.currentTimeMillis() - timestamp).toInt(),
                            framesProcessed = frameCount
                        )
                    }

                    // Process frame at reduced rate
                    if (frameCount % FRAME_PROCESSING_INTERVAL == 0) {
                        processFrame(videoFrame)
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Streaming failed", e)
                _connectionState.value = ConnectionState.ERROR
                addMessage(
                    Message(
                        content = "Streaming error: ${e.message}",
                        isFromUser = false
                    )
                )
            }
        }
    }

    /**
     * Process a video frame and potentially generate a response.
     */
    private suspend fun processFrame(videoFrame: MetaRayBanManager.VideoFrame) {
        try {
            // Generate visual context (simplified - real implementation would use CLIP or similar)
            val visualContext = generateVisualContext(videoFrame)

            // Only generate response if user asked a question recently
            val recentUserMessage = _messages.value.lastOrNull { it.isFromUser }
            if (recentUserMessage != null &&
                System.currentTimeMillis() - recentUserMessage.timestamp < RECENT_MESSAGE_TIMEOUT_MS
            ) {
                val prompt = recentUserMessage.content
                val engine = localSnnEngine

                if (engine != null) {
                    val response = engine.generate(prompt, visualContext)

                    // Parse actions from response
                    val actions = extractActions(response)

                    addMessage(
                        Message(
                            content = response,
                            isFromUser = false,
                            visualContext = visualContext,
                            actions = actions
                        )
                    )

                    // Execute actions
                    actionDispatcher?.dispatch(actions)
                } else {
                    Log.w(TAG, "LocalSnnEngine not initialized")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Frame processing failed", e)
        }
    }

    /**
     * Send a text message and get AI response.
     */
    fun sendMessage(text: String) {
        if (text.isBlank()) return

        // Add user message
        addMessage(
            Message(
                content = text,
                isFromUser = true
            )
        )

        // Process immediately if connected
        if (_connectionState.value == ConnectionState.CONNECTED ||
            _connectionState.value == ConnectionState.STREAMING
        ) {
            viewModelScope.launch {
                try {
                    val engine = localSnnEngine
                    if (engine != null) {
                        val response = engine.generate(text, "")
                        val actions = extractActions(response)

                        addMessage(
                            Message(
                                content = response,
                                isFromUser = false,
                                actions = actions
                            )
                        )

                        actionDispatcher?.dispatch(actions)
                    } else {
                        addMessage(
                            Message(
                                content = "AI engine not initialized. Please wait...",
                                isFromUser = false
                            )
                        )
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Message processing failed", e)
                    addMessage(
                        Message(
                            content = "Error: ${e.message}",
                            isFromUser = false
                        )
                    )
                }
            }
        } else {
            addMessage(
                Message(
                    content = "Please connect to smart glasses first.",
                    isFromUser = false
                )
            )
        }
    }

    /**
     * Disconnect from smart glasses.
     */
    fun disconnect() {
        streamingJob?.cancel()
        streamingJob = null

        viewModelScope.launch {
            rayBanManager.disconnect()
            _connectionState.value = ConnectionState.DISCONNECTED
            _streamingMetrics.value = null

            addMessage(
                Message(
                    content = "Disconnected from smart glasses.",
                    isFromUser = false
                )
            )
        }
    }

    /**
     * Add a message to the conversation.
     */
    private fun addMessage(message: Message) {
        _messages.value = _messages.value + message
    }

    /**
     * Generate visual context from video frame.
     * 
     * This is a simplified placeholder. A real implementation would use:
     * - CLIP or similar vision-language model for semantic understanding
     * - Object detection for identifying items in the scene
     * - OCR for reading text in the frame
     */
    private fun generateVisualContext(videoFrame: MetaRayBanManager.VideoFrame): String {
        return "Frame ${videoFrame.width}x${videoFrame.height}"
    }

    /**
     * Extract SmartGlassAction instances from AI response.
     *
     * Looks for JSON blocks in the format:
     * ```json
     * [{"type": "TTS_SPEAK", "payload": {"text": "..."}}]
     * ```
     */
    private fun extractActions(response: String): List<SmartGlassAction> {
        // Look for JSON blocks in response
        val match = JSON_ACTION_PATTERN.find(response)

        return if (match != null) {
            try {
                SmartGlassAction.fromJsonArray(match.groupValues[1])
            } catch (e: Exception) {
                Log.e(TAG, "Failed to parse actions", e)
                emptyList()
            }
        } else {
            emptyList()
        }
    }

    override fun onCleared() {
        super.onCleared()
        disconnect()
        textToSpeech?.shutdown()
    }
}

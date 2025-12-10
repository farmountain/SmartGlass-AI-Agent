package com.smartglass.sample

import android.content.Intent
import android.graphics.Bitmap
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.smartglass.actions.ActionDispatcher
import com.smartglass.sdk.ActionExecutor
import com.smartglass.sdk.DatSmartGlassController
import com.smartglass.sdk.PrivacyPreferences
import com.smartglass.sdk.SmartGlassClient
import com.smartglass.sdk.rayban.MetaRayBanManager
import com.smartglass.runtime.llm.LocalSnnEngine
import com.smartglass.runtime.llm.LocalTokenizer
import java.io.File
import java.io.FileOutputStream
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class SampleActivity : AppCompatActivity() {

    private lateinit var deviceIdInput: EditText
    private lateinit var promptInput: EditText
    private lateinit var responseText: TextView
    private lateinit var rayBanManager: MetaRayBanManager

    private val actionExecutor = ActionExecutor
    private val client = SmartGlassClient()
    private var audioStreamJob: Job? = null
    private var lastSessionId: String? = null
    
    // End-to-end controller for streaming glasses data to local processing
    private var datController: DatSmartGlassController? = null
    
    companion object {
        private const val SNN_MODEL_ASSET_PATH = "snn_student_ts.pt"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_sample)

        deviceIdInput = findViewById(R.id.deviceIdInput)
        promptInput = findViewById(R.id.promptInput)
        responseText = findViewById(R.id.responseText)
        rayBanManager = MetaRayBanManager(applicationContext)

        findViewById<Button>(R.id.sendButton).setOnClickListener {
            sendPrompt()
        }

        findViewById<Button>(R.id.connectButton).setOnClickListener {
            connectGlasses()
        }

        findViewById<Button>(R.id.captureButton).setOnClickListener {
            captureAndSend()
        }

        findViewById<Button>(R.id.startAudioButton).setOnClickListener {
            startAudioStreaming()
        }

        findViewById<Button>(R.id.stopAudioButton).setOnClickListener {
            stopAudioStreaming()
        }
        
        findViewById<Button>(R.id.privacySettingsButton).setOnClickListener {
            openPrivacySettings()
        }
        
        // DatSmartGlassController demo buttons (if they exist in layout)
        findViewById<Button>(R.id.startControllerButton)?.setOnClickListener {
            startControllerStreaming()
        }
        
        findViewById<Button>(R.id.stopControllerButton)?.setOnClickListener {
            stopControllerStreaming()
        }
        
        findViewById<Button>(R.id.finalizeControllerButton)?.setOnClickListener {
            handleUserTurnController()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopAudioStreaming()
        stopControllerStreaming()
        rayBanManager.disconnect()
    }
    
    private fun openPrivacySettings() {
        val intent = Intent(this, PrivacySettingsActivity::class.java)
        startActivity(intent)
    }

    private fun sendPrompt() {
        val prompt = promptInput.text.toString()
        if (prompt.isBlank()) {
            Toast.makeText(this, R.string.prompt_required, Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            setStatus(getString(R.string.starting_session))
            try {
                // Load privacy preferences and start session
                val privacyPrefs = PrivacyPreferences.load(this@SampleActivity)
                
                // Start session with privacy preferences
                // Note: Using deprecated API for simple text prompts; new streaming API
                // is better suited for audio/video streaming use cases
                @Suppress("DEPRECATION")
                val sessionId = client.startSession(privacyPrefs, text = prompt)
                lastSessionId = sessionId
                
                @Suppress("DEPRECATION")
                val response = client.answer(sessionId = sessionId, text = prompt)
                actionExecutor.execute(response.actions, this@SampleActivity)

                val actionsSummary = response.actions.takeIf { it.isNotEmpty() }
                    ?.joinToString(prefix = "\nActions:\n", separator = "\n") { action ->
                        "• ${action.type}: ${action.payload}"
                    } ?: ""

                val responseSummary = buildString {
                    append(getString(R.string.response_prefix, response.response))
                    if (actionsSummary.isNotBlank()) append(actionsSummary)
                }

                setStatus(responseSummary)
            } catch (exc: Exception) {
                setStatus(getString(R.string.response_error, exc.message))
            }
        }
    }

    private fun connectGlasses() {
        val deviceId = resolveDeviceId()
        lifecycleScope.launch {
            setStatus(getString(R.string.connecting_glasses))
            try {
                rayBanManager.connect(deviceId = deviceId, transport = MetaRayBanManager.Transport.BLE)
                setStatus(getString(R.string.glasses_connected, deviceId))
            } catch (exc: Exception) {
                Log.e("SampleActivity", "Failed to connect to glasses", exc)
                setStatus(getString(R.string.connect_error, exc.message))
                rayBanManager.disconnect()
            }
        }
    }

    private fun captureAndSend() {
        lifecycleScope.launch {
            setStatus(getString(R.string.capturing_photo))
            try {
                val capturedBitmap = rayBanManager.capturePhoto()
                if (capturedBitmap == null) {
                    setStatus(getString(R.string.capture_failed))
                    return@launch
                }

                val imageFile = saveBitmapToTempFile(capturedBitmap)
                val sessionId = lastSessionId ?: client.startSession(imagePath = imageFile.absolutePath).also {
                    lastSessionId = it
                }

                val response = client.answer(sessionId = sessionId, imagePath = imageFile.absolutePath)
                actionExecutor.execute(response.actions, this@SampleActivity)

                val actionsSummary = response.actions.takeIf { it.isNotEmpty() }
                    ?.joinToString(prefix = "\nActions:\n", separator = "\n") { action ->
                        "• ${action.type}: ${action.payload}"
                    } ?: ""

                val responseSummary = buildString {
                    append(getString(R.string.response_prefix, response.response))
                    if (actionsSummary.isNotBlank()) append(actionsSummary)
                }

                setStatus(responseSummary)
            } catch (exc: Exception) {
                Log.e("SampleActivity", "Failed to capture and send photo", exc)
                setStatus(getString(R.string.capture_error, exc.message))
            }
        }
    }

    private fun startAudioStreaming() {
        val deviceId = resolveDeviceId()
        lifecycleScope.launch {
            setStatus(getString(R.string.starting_audio_stream))
            audioStreamJob?.cancel()
            audioStreamJob = launch(start = CoroutineStart.UNDISPATCHED) {
                try {
                    rayBanManager.connect(deviceId = deviceId, transport = MetaRayBanManager.Transport.BLE)
                    rayBanManager.startAudioStreaming().collect { chunk ->
                        Log.d("SampleActivity", "Received ${chunk.size} bytes of audio")
                    }
                } catch (exc: Exception) {
                    Log.e("SampleActivity", "Audio streaming failed", exc)
                    setStatus(getString(R.string.stream_error, exc.message))
                } finally {
                    setStatus(getString(R.string.stream_stopped))
                }
            }
        }
    }

    private fun stopAudioStreaming() {
        audioStreamJob?.cancel()
        audioStreamJob = null
        rayBanManager.stopAudioStreaming()
    }

    private suspend fun saveBitmapToTempFile(bitmap: Bitmap): File =
        withContext(Dispatchers.IO) {
            val imageFile = File.createTempFile("rayban_capture", ".jpg", cacheDir)
            FileOutputStream(imageFile).use { output ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 90, output)
            }
            imageFile
        }

    private fun resolveDeviceId(): String =
        deviceIdInput.text.toString().ifBlank { getString(R.string.default_device_id) }

    private suspend fun setStatus(message: String) {
        withContext(Dispatchers.Main) {
            responseText.text = message
            Toast.makeText(this@SampleActivity, message, Toast.LENGTH_SHORT).show()
        }
    }
    
    // ========================================================================
    // DatSmartGlassController Example Usage
    // ========================================================================
    
    /**
     * Start end-to-end streaming using DatSmartGlassController with on-device processing.
     * 
     * This method demonstrates the simplified API for connecting glasses
     * and processing audio/video locally using LocalSnnEngine.
     */
    private fun startControllerStreaming() {
        val deviceId = resolveDeviceId()
        
        lifecycleScope.launch {
            setStatus("Starting end-to-end streaming with DatSmartGlassController...")
            
            try {
                // Create controller if not already created
                if (datController == null) {
                    // Initialize LocalSnnEngine and ActionDispatcher for on-device processing
                    val tokenizer = LocalTokenizer(applicationContext, SNN_MODEL_ASSET_PATH)
                    val snnEngine = LocalSnnEngine(applicationContext, SNN_MODEL_ASSET_PATH, tokenizer)
                    val actionDispatcher = ActionDispatcher(applicationContext)
                    
                    datController = DatSmartGlassController(
                        rayBanManager = rayBanManager,
                        localSnnEngine = snnEngine,
                        actionDispatcher = actionDispatcher,
                        keyframeIntervalMs = 500L // Process keyframes every 500ms
                    )
                }
                
                // Monitor state changes
                launch {
                    val controller = datController ?: return@launch
                    while (true) {
                        val state = controller.state
                        Log.d("SampleActivity", "Controller state: $state")
                        when (state) {
                            DatSmartGlassController.State.STREAMING -> {
                                setStatus("🎥 Streaming and processing locally...")
                            }
                            DatSmartGlassController.State.CONNECTING -> {
                                setStatus("🔌 Connecting to glasses...")
                            }
                            DatSmartGlassController.State.ERROR -> {
                                setStatus("❌ Controller error - please stop and restart")
                                return@launch
                            }
                            DatSmartGlassController.State.IDLE -> {
                                // Stopped
                                return@launch
                            }
                        }
                        kotlinx.coroutines.delay(1000)
                    }
                }
                
                // Observe agent responses
                launch {
                    datController?.agentResponse?.collect { response ->
                        if (response.isNotEmpty()) {
                            setStatus("Agent: $response")
                        }
                    }
                }
                
                // Start streaming
                datController!!.start(
                    deviceId = deviceId,
                    transport = MetaRayBanManager.Transport.WIFI
                )
                
                Log.d("SampleActivity", "Controller started successfully")
                
            } catch (exc: Exception) {
                Log.e("SampleActivity", "Failed to start controller", exc)
                setStatus("Controller error: ${exc.message}")
            }
        }
    }
    
    /**
     * Stop end-to-end streaming and clean up resources.
     */
    private fun stopControllerStreaming() {
        datController?.stop()
        datController = null
        lifecycleScope.launch {
            setStatus("Controller streaming stopped")
        }
    }
    
    /**
     * Handle a user turn with text query and visual context.
     * 
     * This processes the query using on-device LocalSnnEngine and dispatches
     * any resulting actions.
     */
    private fun handleUserTurnController() {
        lifecycleScope.launch {
            try {
                setStatus("Processing query...")
                
                val controller = datController
                if (controller == null || controller.state != DatSmartGlassController.State.STREAMING) {
                    setStatus("Controller not streaming - start streaming first")
                    return@launch
                }
                
                // Get text query from input
                val textQuery = promptInput.text.toString().takeIf { it.isNotBlank() }
                    ?: "What do you see?"
                
                val (responseText, actions) = controller.handleUserTurn(
                    textQuery = textQuery,
                    visualContext = null // Will use latest visual context from frames
                )
                
                // Display response
                val actionsSummary = actions.takeIf { it.isNotEmpty() }
                    ?.joinToString(prefix = "\nActions:\n", separator = "\n") { action ->
                        "• $action"
                    } ?: ""
                
                val responseSummary = buildString {
                    append("Agent Response: $responseText")
                    if (actionsSummary.isNotBlank()) append(actionsSummary)
                }
                
                setStatus(responseSummary)
                
            } catch (exc: Exception) {
                Log.e("SampleActivity", "Failed to handle user turn", exc)
                setStatus("Query error: ${exc.message}")
            }
        }
    }
}

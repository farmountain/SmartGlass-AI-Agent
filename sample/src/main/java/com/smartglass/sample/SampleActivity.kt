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
import com.smartglass.sdk.ActionExecutor
import com.smartglass.sdk.DatSmartGlassController
import com.smartglass.sdk.PrivacyPreferences
import com.smartglass.sdk.SmartGlassClient
import com.smartglass.sdk.rayban.MetaRayBanManager
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
    
    // End-to-end controller for streaming glasses data to backend
    private var datController: DatSmartGlassController? = null

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
            finalizeControllerTurn()
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
     * Start end-to-end streaming using DatSmartGlassController.
     * 
     * This method demonstrates the simplified API for connecting glasses
     * and streaming audio/video to the backend in one call.
     */
    private fun startControllerStreaming() {
        val deviceId = resolveDeviceId()
        
        lifecycleScope.launch {
            setStatus("Starting end-to-end streaming with DatSmartGlassController...")
            
            try {
                // Create controller if not already created
                if (datController == null) {
                    datController = DatSmartGlassController(
                        rayBanManager = rayBanManager,
                        smartGlassClient = client,
                        keyframeIntervalMs = 500L // Send keyframes every 500ms
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
                                setStatus("🎥 Streaming audio and video to backend...")
                            }
                            DatSmartGlassController.State.CONNECTING -> {
                                setStatus("🔌 Connecting to glasses and backend...")
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
                
                // Start streaming
                val result = datController!!.start(
                    deviceId = deviceId,
                    transport = MetaRayBanManager.Transport.WIFI
                )
                
                Log.d("SampleActivity", "Controller started: ${result.response}")
                
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
     * Finalize the current turn and get agent response.
     * 
     * This sends all accumulated audio and video frames to the backend
     * and receives the agent's response with recommended actions.
     */
    private fun finalizeControllerTurn() {
        lifecycleScope.launch {
            try {
                setStatus("Finalizing turn...")
                
                val controller = datController
                if (controller == null || controller.state != DatSmartGlassController.State.STREAMING) {
                    setStatus("Controller not streaming - start streaming first")
                    return@launch
                }
                
                val result = controller.finalizeTurn()
                
                // Execute any recommended actions
                actionExecutor.execute(result.actions, this@SampleActivity)
                
                // Display response
                val actionsSummary = result.actions.takeIf { it.isNotEmpty() }
                    ?.joinToString(prefix = "\nActions:\n", separator = "\n") { action ->
                        "• ${action.type}: ${action.payload}"
                    } ?: ""
                
                val responseSummary = buildString {
                    append("Agent Response: ${result.response}")
                    if (actionsSummary.isNotBlank()) append(actionsSummary)
                }
                
                setStatus(responseSummary)
                
            } catch (exc: Exception) {
                Log.e("SampleActivity", "Failed to finalize turn", exc)
                setStatus("Finalize error: ${exc.message}")
            }
        }
    }
}

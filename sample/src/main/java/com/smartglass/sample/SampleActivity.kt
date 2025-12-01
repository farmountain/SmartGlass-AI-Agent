package com.smartglass.sample

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
    }

    override fun onDestroy() {
        super.onDestroy()
        stopAudioStreaming()
        rayBanManager.disconnect()
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
                val sessionId = client.startSession(text = prompt)
                lastSessionId = sessionId
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
}

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
import com.smartglass.sdk.SmartGlassClient
import com.smartglass.sdk.rayban.MetaRayBanManager
import java.io.File
import java.io.FileOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class SampleActivity : AppCompatActivity() {

    private lateinit var promptInput: EditText
    private lateinit var responseText: TextView
    private lateinit var rayBanManager: MetaRayBanManager

    private val client = SmartGlassClient()
    private var lastSessionId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_sample)

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
                // Stubbed image handling for now; only text is sent.
                val sessionId = client.startSession(text = prompt)
                lastSessionId = sessionId
                val response = client.answer(sessionId = sessionId, text = prompt)

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
        lifecycleScope.launch {
            setStatus(getString(R.string.connecting_glasses))
            try {
                // TODO: Replace the stubbed connect call with the Meta Ray-Ban SDK discovery/connection
                //  once available. Device identifiers and transports should be provided by the real
                //  SDK APIs instead of hard-coded placeholders.
                rayBanManager.connect(deviceId = "demo-device-id", transport = MetaRayBanManager.Transport.BLE)
                setStatus(getString(R.string.glasses_connected_stub))
            } catch (exc: Exception) {
                Log.e("SampleActivity", "Failed to connect to glasses", exc)
                setStatus(getString(R.string.connect_error, exc.message))
            }
        }
    }

    private fun captureAndSend() {
        lifecycleScope.launch {
            setStatus(getString(R.string.capturing_photo))
            try {
                // TODO: Replace the placeholder capture with the Meta Ray-Ban SDK camera stream once
                //  the official SDK is available. The resulting JPEG or encoded bytes should be
                //  forwarded through SmartGlassClient.answer for processing.
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

    private suspend fun saveBitmapToTempFile(bitmap: Bitmap): File =
        withContext(Dispatchers.IO) {
            val imageFile = File.createTempFile("rayban_capture", ".jpg", cacheDir)
            FileOutputStream(imageFile).use { output ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 90, output)
            }
            imageFile
        }

    private suspend fun setStatus(message: String) {
        withContext(Dispatchers.Main) {
            responseText.text = message
            Toast.makeText(this@SampleActivity, message, Toast.LENGTH_SHORT).show()
        }
    }
}

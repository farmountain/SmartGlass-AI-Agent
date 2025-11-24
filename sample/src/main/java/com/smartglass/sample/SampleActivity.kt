package com.smartglass.sample

import android.os.Bundle
import android.util.Base64
import android.util.Log
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.smartglass.sdk.SmartGlassEdgeClient
import com.smartglass.sdk.EdgeResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class SampleActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private val client = SmartGlassEdgeClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_sample)

        statusText = findViewById(R.id.statusText)
        findViewById<Button>(R.id.startSessionButton).setOnClickListener {
            runDemoWorkflow()
        }
    }

    private fun runDemoWorkflow() {
        lifecycleScope.launch {
            setStatus("Creating SmartGlass session…")
            try {
                val sessionId = client.createSession()
                logStatus("Session created: $sessionId")

                val audioBytes = ByteArray(3200) { (it % 50).toByte() }
                val audioResponse = client.sendAudioChunk(sessionId, audioBytes, sampleRate = 16000)
                logEdgeResponse("Audio response", audioResponse)

                val imageBytes = Base64.decode(MOCK_JPEG_BASE64, Base64.DEFAULT)
                val frameResponse = client.sendFrame(sessionId, imageBytes, width = 1, height = 1)
                logEdgeResponse("Frame response", frameResponse)

                val queryResponse = client.runQuery(
                    sessionId = sessionId,
                    textQuery = getString(R.string.session_prompt),
                )
                logEdgeResponse("Query response", queryResponse)

                val closeResponse = client.closeSession(sessionId)
                logEdgeResponse("Session closed", closeResponse)
                setStatus("Finished session: $sessionId")
            } catch (exc: Exception) {
                Log.e(TAG, "Failed to run sample workflow", exc)
                setStatus("Error: ${exc.message}")
            }
        }
    }

    private suspend fun setStatus(message: String) {
        withContext(Dispatchers.Main) {
            statusText.text = message
            Toast.makeText(this@SampleActivity, message, Toast.LENGTH_SHORT).show()
        }
        Log.i(TAG, message)
    }

    private fun logStatus(message: String) {
        statusText.text = message
        Log.i(TAG, message)
    }

    private fun logEdgeResponse(label: String, response: EdgeResponse) {
        val summary = buildString {
            append(label)
            response.sessionId?.let { append(" | session=" + it) }
            response.transcript?.let { append(" | transcript=" + it) }
            response.response?.let { append(" | response=" + it) }
            response.status?.let { append(" | status=" + it) }
            response.error?.let { append(" | error=" + it) }
        }
        statusText.text = summary
        Log.i(TAG, summary)
    }

    companion object {
        private const val TAG = "SmartGlassSample"
        private const val MOCK_JPEG_BASE64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxISEhUTEhIVFRUVFRUVFRUVFRUVFRUWFhUVFRUYHSggGBolHRUVITEhJSkrLi4uFx8zODMtNygtLisBCgoKDg0OGhAQGi0lHyUtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAKgBLAMBIgACEQEDEQH/xAAWAAEBAQAAAAAAAAAAAAAAAAAABQf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAQL/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCfYA//2Q=="
    }
}

package com.smartglass.sdk.examples

import android.app.Activity
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import androidx.lifecycle.lifecycleScope
import com.smartglass.sdk.SmartGlassClient
import com.smartglass.sdk.rayban.MetaRayBanManager
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream

/**
 * Example Activity demonstrating DAT SDK integration with SmartGlass AI backend.
 * 
 * This example shows:
 * 1. Connecting to Meta Ray-Ban glasses via DAT SDK
 * 2. Starting continuous video streaming
 * 3. Sending frames to SmartGlass AI backend
 * 4. Processing and displaying AI responses
 * 
 * NOTE: This is an example/reference implementation. In a production app:
 * - Add proper permission handling (see TODO comments)
 * - Add error recovery logic
 * - Implement settings UI for video quality, etc.
 * - Add proper lifecycle management
 * - Add analytics and telemetry
 */
class DatIntegrationExample : Activity() {

    private lateinit var raybanManager: MetaRayBanManager
    private lateinit var aiClient: SmartGlassClient
    private var aiSessionHandle: SmartGlassClient.SessionHandle? = null
    private var isStreaming = false
    private var frameCount = 0

    // UI components
    private lateinit var statusText: TextView
    private lateinit var responseText: TextView
    private lateinit var connectButton: Button
    private lateinit var streamButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // TODO: Replace with your actual layout
        // setContentView(R.layout.activity_dat_example)
        
        // Initialize managers
        raybanManager = MetaRayBanManager(this)
        aiClient = SmartGlassClient(
            baseUrl = "http://192.168.1.100:8765", // TODO: Configure backend URL
            apiKey = null // TODO: Add API key if required
        )
        
        // TODO: Initialize UI components
        // statusText = findViewById(R.id.statusText)
        // responseText = findViewById(R.id.responseText)
        // connectButton = findViewById(R.id.connectButton)
        // streamButton = findViewById(R.id.streamButton)
        
        setupClickListeners()
    }

    private fun setupClickListeners() {
        // TODO: Replace with actual button references
        // connectButton.setOnClickListener {
        //     lifecycleScope.launch {
        //         handleConnect()
        //     }
        // }
        
        // streamButton.setOnClickListener {
        //     lifecycleScope.launch {
        //         if (isStreaming) {
        //             stopStreaming()
        //         } else {
        //             startStreaming()
        //         }
        //     }
        // }
    }

    /**
     * Connect to Meta Ray-Ban glasses.
     * 
     * TODO: Before calling this:
     * 1. Check if user has paired glasses via Meta AI app
     * 2. Request necessary permissions (camera, bluetooth)
     * 3. Handle permission denial gracefully
     */
    private suspend fun handleConnect() {
        try {
            updateStatus("Connecting to glasses...")
            
            // TODO: In production, discover and select device from available list
            // For now, using a placeholder device ID
            raybanManager.connect(
                deviceId = "RAYBAN-001", // TODO: Get from device discovery
                transport = MetaRayBanManager.Transport.BLE
            )
            
            updateStatus("Connected! Ready to stream.")
            // TODO: Enable stream button in UI
            
        } catch (e: Exception) {
            Log.e(TAG, "Connection failed", e)
            updateStatus("Connection failed: ${e.message}")
            // TODO: Show error dialog to user
        }
    }

    /**
     * Start video streaming and AI processing.
     * 
     * This starts:
     * 1. Video streaming from glasses (24 fps)
     * 2. AI session on backend
     * 3. Frame processing pipeline
     */
    private suspend fun startStreaming() {
        try {
            // Create AI session
            aiSessionHandle = aiClient.startSession()
            updateStatus("AI session started: ${aiSessionHandle?.sessionId}")
            
            // Start video streaming from glasses
            raybanManager.startStreaming { frameBytes, timestamp ->
                lifecycleScope.launch {
                    handleFrame(frameBytes, timestamp)
                }
            }
            
            isStreaming = true
            frameCount = 0
            updateStatus("Streaming active")
            // TODO: Update stream button text to "Stop"
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start streaming", e)
            updateStatus("Streaming failed: ${e.message}")
            // TODO: Show error dialog
        }
    }

    /**
     * Process a single frame from the glasses.
     * 
     * Frames are received at ~24 fps. We downsample to ~5 fps for AI processing
     * to balance responsiveness with backend load.
     */
    private suspend fun handleFrame(frameBytes: ByteArray, timestamp: Long) {
        frameCount++
        
        // Downsample: Send every 5th frame (~5 fps from 24 fps stream)
        if (frameCount % 5 != 0) {
            return
        }
        
        try {
            val handle = aiSessionHandle ?: return
            
            // Send frame to AI backend
            aiClient.sendFrame(handle, frameBytes)
            
            // Every 10th frame, finalize turn and get response
            if (frameCount % 50 == 0) {
                val result = aiClient.finalizeTurn(handle)
                
                // Display AI response
                updateResponse(result.response ?: "No response")
                
                // Execute any actions
                result.actions.forEach { action ->
                    executeAction(action)
                }
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Frame processing failed", e)
            // Continue streaming even if one frame fails
        }
    }

    /**
     * Stop video streaming.
     */
    private suspend fun stopStreaming() {
        try {
            // Stop glasses streaming
            raybanManager.stopStreaming()
            
            // Close AI session
            aiSessionHandle?.let { handle ->
                // Get final response
                val result = aiClient.finalizeTurn(handle)
                updateResponse(result.response ?: "Session ended")
            }
            aiSessionHandle = null
            
            isStreaming = false
            updateStatus("Streaming stopped")
            // TODO: Update stream button text to "Start"
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to stop streaming", e)
            updateStatus("Stop failed: ${e.message}")
        }
    }

    /**
     * Execute an action returned by the AI backend.
     * 
     * TODO: Implement action execution based on your app's requirements.
     * Examples:
     * - NAVIGATE: Start navigation to a location
     * - SHOW_TEXT: Display text on screen or via TTS
     * - CAPTURE_PHOTO: Take a photo
     * - NOTIFICATION: Show a notification
     */
    private fun executeAction(action: SmartGlassClient.Action) {
        Log.i(TAG, "Executing action: ${action.type}")
        when (action.type) {
            "NAVIGATE" -> {
                val destination = action.payload["destination"] as? String
                Log.i(TAG, "Navigate to: $destination")
                // TODO: Launch navigation app
            }
            "SHOW_TEXT" -> {
                val text = action.payload["text"] as? String
                Log.i(TAG, "Show text: $text")
                updateResponse(text ?: "")
                // TODO: Optionally use TTS
            }
            "CAPTURE_PHOTO" -> {
                lifecycleScope.launch {
                    val bitmap = raybanManager.capturePhoto()
                    Log.i(TAG, "Captured photo: ${bitmap?.width}x${bitmap?.height}")
                    // TODO: Save or display photo
                }
            }
            else -> {
                Log.w(TAG, "Unknown action type: ${action.type}")
            }
        }
    }

    /**
     * Handle photo capture from glasses.
     * 
     * Photos can be captured during or independent of video streaming.
     */
    private suspend fun capturePhoto() {
        try {
            val bitmap = raybanManager.capturePhoto()
            if (bitmap != null) {
                Log.i(TAG, "Photo captured: ${bitmap.width}x${bitmap.height}")
                
                // Convert to JPEG and send to backend
                val stream = ByteArrayOutputStream()
                bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 90, stream)
                val jpegBytes = stream.toByteArray()
                
                aiSessionHandle?.let { handle ->
                    aiClient.sendFrame(handle, jpegBytes)
                }
                
                // TODO: Display or save photo
            } else {
                Log.w(TAG, "Photo capture returned null")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Photo capture failed", e)
            // TODO: Show error to user
        }
    }

    // UI update helpers
    private fun updateStatus(message: String) {
        Log.i(TAG, "Status: $message")
        runOnUiThread {
            // TODO: Update status text view
            // statusText.text = message
        }
    }

    private fun updateResponse(message: String) {
        Log.i(TAG, "Response: $message")
        runOnUiThread {
            // TODO: Update response text view
            // responseText.text = message
        }
    }

    override fun onPause() {
        super.onPause()
        // Stop streaming when app goes to background
        if (isStreaming) {
            lifecycleScope.launch {
                stopStreaming()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        // Clean up
        raybanManager.disconnect()
    }

    companion object {
        private const val TAG = "DatIntegrationExample"
    }
}

/**
 * Example integration with audio streaming.
 * 
 * This shows how to collect audio chunks and send them to the backend
 * alongside video frames for multimodal AI processing.
 */
suspend fun exampleAudioIntegration(
    manager: MetaRayBanManager,
    client: SmartGlassClient,
    sessionHandle: SmartGlassClient.SessionHandle
) {
    // Start audio streaming
    manager.startAudioStreaming().collect { audioChunk ->
        // Send audio to backend
        // TODO: Determine sample rate from glasses
        client.sendAudioChunk(sessionHandle, audioChunk, sampleRate = 16000)
    }
}

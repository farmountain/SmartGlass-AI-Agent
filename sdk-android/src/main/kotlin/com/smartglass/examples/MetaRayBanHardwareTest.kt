package com.smartglass.examples

import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.smartglass.actions.ActionDispatcher
import com.smartglass.runtime.llm.LocalSnnEngine
import com.smartglass.sdk.DatSmartGlassController
import com.smartglass.sdk.rayban.MetaRayBanManager
import kotlinx.coroutines.launch

/**
 * Example Activity for testing Meta DAT SDK integration with physical hardware.
 * 
 * This demonstrates the complete workflow from hardware connection to AI inference.
 */
class MetaRayBanHardwareTest : AppCompatActivity() {
    
    private lateinit var controller: DatSmartGlassController
    private lateinit var statusText: TextView
    private lateinit var connectButton: Button
    private lateinit var queryButton: Button
    
    companion object {
        private const val TAG = "MetaRayBanHardwareTest"
        private const val DEVICE_ID = "your-meta-rayban-device-id" // Replace with actual device ID
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize UI (you'll need to create the layout)
        setupUI()
        
        // Initialize DAT SDK components
        initializeDatSdk()
        
        setupEventHandlers()
    }
    
    private fun setupUI() {
        // Create simple test UI
        setContentView(android.R.layout.activity_list_item) // Placeholder - create proper layout
        
        statusText = TextView(this).apply {
            text = "Meta Ray-Ban Hardware Test - Ready"
        }
        
        connectButton = Button(this).apply {
            text = "Connect to Glasses"
        }
        
        queryButton = Button(this).apply {
            text = "Test Query"
            isEnabled = false
        }
    }
    
    private fun initializeDatSdk() {
        try {
            Log.i(TAG, "Initializing Meta DAT SDK components...")
            
            // Step 1: Initialize Meta Ray-Ban Manager
            val rayBanManager = MetaRayBanManager(applicationContext)
            updateStatus("✅ MetaRayBanManager initialized")
            
            // Step 2: Initialize SNN Engine (mock for now)
            val snnEngine = LocalSnnEngine(applicationContext, "mock_model.pt")
            updateStatus("✅ LocalSnnEngine initialized")
            
            // Step 3: Initialize Action Dispatcher
            val actionDispatcher = ActionDispatcher(applicationContext)
            updateStatus("✅ ActionDispatcher initialized")
            
            // Step 4: Create DAT Controller
            controller = DatSmartGlassController(
                rayBanManager = rayBanManager,
                localSnnEngine = snnEngine,
                actionDispatcher = actionDispatcher,
                keyframeIntervalMs = 500L
            )
            updateStatus("✅ DatSmartGlassController ready")
            
            // Step 5: Observe AI responses
            lifecycleScope.launch {
                controller.agentResponse.collect { response ->
                    updateStatus("🤖 AI Response: $response")
                }
            }
            
            // Note: state is not a StateFlow, it's a property
            // We'll check state manually during connection
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize DAT SDK", e)
            updateStatus("❌ Initialization failed: ${e.message}")
        }
    }
    
    private fun setupEventHandlers() {
        connectButton.setOnClickListener {
            lifecycleScope.launch {
                connectToGlasses()
            }
        }
        
        queryButton.setOnClickListener {
            lifecycleScope.launch {
                testQuery()
            }
        }
    }
    
    private suspend fun connectToGlasses() {
        try {
            updateStatus("🔄 Connecting to Meta Ray-Ban glasses...")
            
            // Attempt connection using WIFI transport (preferred)
            controller.start(
                deviceId = DEVICE_ID,
                transport = MetaRayBanManager.Transport.WIFI
            )
            
                updateStatus("✅ Connected to glasses - streaming active!")
            connectButton.isEnabled = false
            queryButton.isEnabled = true        } catch (e: Exception) {
            Log.e(TAG, "Connection failed", e)
            updateStatus("❌ Connection failed: ${e.message}")
            
            // Try BLE as fallback
            try {
                updateStatus("🔄 Trying BLE connection as fallback...")
                controller.start(
                    deviceId = DEVICE_ID,
                    transport = MetaRayBanManager.Transport.BLE
                )
                updateStatus("✅ Connected via BLE - streaming active!")
                connectButton.isEnabled = false
                queryButton.isEnabled = true
            } catch (bleException: Exception) {
                Log.e(TAG, "BLE connection also failed", bleException)
                updateStatus("❌ Both WIFI and BLE connections failed")
            }
        }
    }
    
    private suspend fun testQuery() {
        try {
            updateStatus("🎤 Processing test query...")
            
            // Test with a simple visual query
            controller.handleUserTurn(
                textQuery = "What do you see?",
                visualContext = null // Will use live camera feed
            )
            
            updateStatus("✅ Query processed - waiting for AI response...")
            
        } catch (e: Exception) {
            Log.e(TAG, "Query failed", e)
            updateStatus("❌ Query failed: ${e.message}")
        }
    }
    
    private fun updateStatus(message: String) {
        runOnUiThread {
            Log.i(TAG, message)
            statusText.text = message
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        // Clean up resources
        if (::controller.isInitialized) {
            controller.stop()
        }
    }
}
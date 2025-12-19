package rayskillkit.core.companion

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.smartglass.actions.ActionDispatcher
import com.smartglass.runtime.llm.LocalSnnEngine
import com.smartglass.sdk.DatSmartGlassController
import com.smartglass.sdk.rayban.MetaRayBanManager
import com.smartglass.examples.MetaRayBanHardwareTest
import com.smartglass.integrations.MetaAIIntegration
import kotlinx.coroutines.launch

/**
 * SmartGlass AI Companion App for OPPO Reno 12 Pro
 * 
 * This is the main companion app for testing Meta AI integration with Meta Ray-Ban smart glasses.
 * Optimized for OPPO Reno 12 Pro specifications and Android performance.
 */
class SmartGlassCompanionActivity : AppCompatActivity() {
    
    private lateinit var statusText: TextView
    private lateinit var deviceIdInput: EditText
    private lateinit var connectButton: Button
    private lateinit var disconnectButton: Button
    private lateinit var testQueryButton: Button
    private lateinit var hardwareTestButton: Button
    private lateinit var metaAiButton: Button
    private lateinit var responseText: TextView
    private lateinit var progressBar: ProgressBar
    
    private var controller: DatSmartGlassController? = null
    private var metaAI: MetaAIIntegration? = null
    private var isConnected = false
    
    companion object {
        private const val TAG = "SmartGlassCompanion"
        private const val PERMISSION_REQUEST_CODE = 1001
        private val REQUIRED_PERMISSIONS = arrayOf(
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_ADMIN,
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.POST_NOTIFICATIONS
        )
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        try {
            Log.i(TAG, "Starting SmartGlass AI Companion Activity")
            setContentView(createCompanionUI())
            
            initializeViews()
            checkPermissions()
            initializeSmartGlassComponents()
            
            Log.i(TAG, "SmartGlass AI Companion Activity initialized successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Fatal error during onCreate", e)
            // Create a simple error UI if main UI fails
            createErrorUI("App initialization failed: ${e.message}")
        }
    }
    
    private fun createCompanionUI(): View {
        val mainLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }
        
        // Title
        val title = TextView(this).apply {
            text = "🤖 SmartGlass AI Companion"
            textSize = 24f
            setPadding(0, 0, 0, 32)
        }
        mainLayout.addView(title)
        
        // Status
        statusText = TextView(this).apply {
            text = "Ready to connect to Meta Ray-Ban glasses"
            setPadding(0, 0, 0, 16)
        }
        mainLayout.addView(statusText)
        
        // Device ID input
        val deviceLabel = TextView(this).apply {
            text = "Meta Ray-Ban Device ID:"
            setPadding(0, 16, 0, 8)
        }
        mainLayout.addView(deviceLabel)
        
        deviceIdInput = EditText(this).apply {
            hint = "Enter device ID or leave empty for auto-discovery"
            setPadding(16, 16, 16, 16)
        }
        mainLayout.addView(deviceIdInput)
        
        // Progress bar
        progressBar = ProgressBar(this).apply {
            visibility = View.GONE
        }
        mainLayout.addView(progressBar)
        
        // Connection buttons
        val buttonLayout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 16, 0, 16)
        }
        
        connectButton = Button(this).apply {
            text = "🔗 Connect Glasses"
            setOnClickListener { connectToGlasses() }
        }
        buttonLayout.addView(connectButton)
        
        disconnectButton = Button(this).apply {
            text = "❌ Disconnect"
            isEnabled = false
            setOnClickListener { disconnectFromGlasses() }
        }
        buttonLayout.addView(disconnectButton)
        
        mainLayout.addView(buttonLayout)
        
        // Test buttons
        val testLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 16, 0, 16)
        }
        
        testQueryButton = Button(this).apply {
            text = "🎤 Test Query: 'What do you see?'"
            isEnabled = false
            setOnClickListener { testQuery() }
        }
        testLayout.addView(testQueryButton)
        
        metaAiButton = Button(this).apply {
            text = "🧠 Test Meta AI Integration"
            isEnabled = false
            setOnClickListener { testMetaAI() }
        }
        testLayout.addView(metaAiButton)
        
        hardwareTestButton = Button(this).apply {
            text = "🔧 Advanced Hardware Test"
            setOnClickListener { launchHardwareTest() }
        }
        testLayout.addView(hardwareTestButton)
        
        mainLayout.addView(testLayout)
        
        // Response area
        val responseLabel = TextView(this).apply {
            text = "AI Response:"
            setPadding(0, 32, 0, 8)
            textSize = 16f
        }
        mainLayout.addView(responseLabel)
        
        responseText = TextView(this).apply {
            text = "Waiting for AI response..."
            setPadding(16, 16, 16, 16)
            setBackgroundColor(0xFFF0F0F0.toInt())
            minHeight = 200
        }
        mainLayout.addView(responseText)
        
        val scrollView = ScrollView(this)
        scrollView.addView(mainLayout)
        return scrollView
    }
    
    private fun initializeViews() {
        Log.i(TAG, "SmartGlass AI Companion initialized for OPPO Reno 12 Pro")
        updateStatus("🚀 SmartGlass AI Companion ready!")
    }
    
    private fun checkPermissions() {
        val missingPermissions = REQUIRED_PERMISSIONS.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        
        if (missingPermissions.isNotEmpty()) {
            updateStatus("⚠️ Requesting permissions...")
            ActivityCompat.requestPermissions(this, missingPermissions.toTypedArray(), PERMISSION_REQUEST_CODE)
        } else {
            updateStatus("✅ All permissions granted")
        }
    }
    
    private fun initializeSmartGlassComponents() {
        lifecycleScope.launch {
            try {
                updateStatus("🔄 Initializing SmartGlass components...")
                
                // Initialize components
                val rayBanManager = MetaRayBanManager(applicationContext)
                val snnEngine = LocalSnnEngine(applicationContext, "mock_model.pt")
                val actionDispatcher = ActionDispatcher(applicationContext)
                
                controller = DatSmartGlassController(
                    rayBanManager = rayBanManager,
                    localSnnEngine = snnEngine,
                    actionDispatcher = actionDispatcher,
                    keyframeIntervalMs = 500L
                )
                
                // Observe AI responses
                controller?.agentResponse?.let { responseFlow ->
                    lifecycleScope.launch {
                        responseFlow.collect { response ->
                            runOnUiThread {
                                responseText.text = response
                                updateStatus("🤖 AI response received")
                            }
                        }
                    }
                }
                
                updateStatus("✅ SmartGlass components initialized")
                
                // Initialize Meta AI integration
                metaAI = MetaAIIntegration(applicationContext)
                val metaAIReady = metaAI?.initialize() ?: false
                if (metaAIReady) {
                    updateStatus("🧠 Meta AI integration ready")
                } else {
                    updateStatus("⚠️ Meta AI using fallback mode")
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to initialize SmartGlass components", e)
                updateStatus("❌ Initialization failed: ${e.message}")
            }
        }
    }
    
    private fun connectToGlasses() {
        lifecycleScope.launch {
            try {
                showProgress(true)
                updateStatus("🔄 Connecting to Meta Ray-Ban glasses...")
                
                val deviceId = deviceIdInput.text.toString().takeIf { it.isNotBlank() }
                    ?: "auto-discover"
                
                controller?.start(
                    deviceId = deviceId,
                    transport = MetaRayBanManager.Transport.WIFI
                )
                
                isConnected = true
                updateConnectionUI(true)
                updateStatus("✅ Connected to Meta Ray-Ban glasses!")
                
            } catch (e: Exception) {
                Log.e(TAG, "Connection failed", e)
                updateStatus("❌ Connection failed: ${e.message}")
                
                // Try BLE fallback
                try {
                    updateStatus("🔄 Trying BLE connection...")
                    val deviceId = deviceIdInput.text.toString().takeIf { it.isNotBlank() }
                        ?: "auto-discover"
                    
                    controller?.start(
                        deviceId = deviceId,
                        transport = MetaRayBanManager.Transport.BLE
                    )
                    
                    isConnected = true
                    updateConnectionUI(true)
                    updateStatus("✅ Connected via BLE!")
                    
                } catch (bleException: Exception) {
                    Log.e(TAG, "BLE connection also failed", bleException)
                    updateStatus("❌ Both WiFi and BLE connections failed")
                }
            } finally {
                showProgress(false)
            }
        }
    }
    
    private fun disconnectFromGlasses() {
        controller?.stop()
        isConnected = false
        updateConnectionUI(false)
        updateStatus("🔌 Disconnected from glasses")
    }
    
    private fun testQuery() {
        lifecycleScope.launch {
            try {
                updateStatus("🎤 Processing test query...")
                
                controller?.handleUserTurn(
                    textQuery = "What do you see?",
                    visualContext = null
                )
                
                updateStatus("✅ Query sent - waiting for AI response...")
                
            } catch (e: Exception) {
                Log.e(TAG, "Query failed", e)
                updateStatus("❌ Query failed: ${e.message}")
            }
        }
    }
    
    private fun testMetaAI() {
        lifecycleScope.launch {
            try {
                updateStatus("🧠 Testing Meta AI integration...")
                
                // Test Meta AI with simulated multimodal input
                val testAudio = "What do you see in front of me?".toByteArray()
                val testImage = ByteArray(1024) // Simulated image data
                
                val response = metaAI?.processMultimodalQuery(
                    audioData = testAudio,
                    imageData = testImage,
                    context = "OPPO Reno 12 Pro testing with Meta Ray-Ban glasses"
                )
                
                if (response?.success == true) {
                    responseText.text = "🧠 Meta AI: ${response.text}\n\nConfidence: ${response.confidence}\nActions: ${response.actions.joinToString(", ")}"
                    updateStatus("✅ Meta AI responded successfully!")
                } else {
                    updateStatus("❌ Meta AI test failed: ${response?.error}")
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Meta AI test failed", e)
                updateStatus("❌ Meta AI test failed: ${e.message}")
            }
        }
    }
    
    private fun launchHardwareTest() {
        startActivity(Intent(this, MetaRayBanHardwareTest::class.java))
    }
    
    private fun updateConnectionUI(connected: Boolean) {
        runOnUiThread {
            connectButton.isEnabled = !connected
            disconnectButton.isEnabled = connected
            testQueryButton.isEnabled = connected
            metaAiButton.isEnabled = connected
            deviceIdInput.isEnabled = !connected
        }
    }
    
    private fun updateStatus(message: String) {
        runOnUiThread {
            Log.i(TAG, message)
            statusText.text = message
        }
    }
    
    private fun showProgress(show: Boolean) {
        runOnUiThread {
            progressBar.visibility = if (show) View.VISIBLE else View.GONE
        }
    }
    
    private fun createErrorUI(errorMessage: String) {
        try {
            val errorLayout = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
            }
            
            val errorTitle = TextView(this).apply {
                text = "⚠️ SmartGlass AI Error"
                textSize = 20f
                setPadding(0, 0, 0, 16)
            }
            errorLayout.addView(errorTitle)
            
            val errorText = TextView(this).apply {
                text = errorMessage
                setPadding(0, 0, 0, 16)
            }
            errorLayout.addView(errorText)
            
            val retryButton = Button(this).apply {
                text = "Retry"
                setOnClickListener { 
                    try {
                        recreate()
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to recreate activity", e)
                    }
                }
            }
            errorLayout.addView(retryButton)
            
            setContentView(errorLayout)
            Log.i(TAG, "Error UI created successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create error UI", e)
            // Last resort: finish the activity
            finish()
        }
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        if (requestCode == PERMISSION_REQUEST_CODE) {
            val allGranted = grantResults.all { it == PackageManager.PERMISSION_GRANTED }
            if (allGranted) {
                updateStatus("✅ All permissions granted")
            } else {
                updateStatus("⚠️ Some permissions denied - functionality may be limited")
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        controller?.stop()
    }
}
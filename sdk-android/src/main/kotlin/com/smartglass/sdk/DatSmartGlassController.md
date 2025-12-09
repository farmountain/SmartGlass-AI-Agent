# DatSmartGlassController

End-to-end controller that bridges Meta Ray-Ban DAT SDK with SmartGlass AI backend.

## Overview

`DatSmartGlassController` provides a simple, high-level API for streaming audio and video from Meta Ray-Ban smart glasses to the SmartGlass Agent Python backend. It manages the session lifecycle, automatically forwards streaming data, and handles errors gracefully.

## Features

- **Unified API**: Single method call to start streaming from glasses to backend
- **Automatic Data Forwarding**: Audio chunks and video keyframes automatically sent to backend
- **Frame Rate Control**: Configurable keyframe interval to optimize bandwidth
- **State Machine**: Clear state transitions (IDLE → CONNECTING → STREAMING → ERROR)
- **Error Handling**: Graceful error recovery with logging
- **Resource Management**: Clean shutdown of all resources

## Architecture

```
┌─────────────────────┐
│  Meta Ray-Ban       │
│  Glasses            │
└──────┬──────────────┘
       │ DAT SDK
       ▼
┌──────────────────────┐
│ MetaRayBanManager    │
│ (Audio/Video Stream) │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ DatSmartGlassController │  ◄─── This component
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ SmartGlassClient     │
│ (HTTP to Backend)    │
└──────┬───────────────┘
       │ HTTP/WebSocket
       ▼
┌──────────────────────┐
│ SmartGlass Agent     │
│ (Python Backend)     │
│ Whisper + CLIP + LLM │
└──────────────────────┘
```

## State Machine

```
      start()
IDLE ─────────► CONNECTING ─────────► STREAMING
  ▲                  │                     │
  │                  │ error()             │ finalizeTurn()
  │                  ▼                     │ (continues streaming)
  │               ERROR                    │
  │                  │                     │
  └──────────────────┴─────────────────────┘
           stop() (from any state)
```

## Usage

### Basic Usage in Activity

```kotlin
class MyActivity : AppCompatActivity() {
    private lateinit var controller: DatSmartGlassController

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val rayBanManager = MetaRayBanManager(applicationContext)
        val smartGlassClient = SmartGlassClient(baseUrl = "http://10.0.2.2:8000")
        
        controller = DatSmartGlassController(
            rayBanManager = rayBanManager,
            smartGlassClient = smartGlassClient,
            keyframeIntervalMs = 500L  // Send keyframes every 500ms
        )

        // Start streaming
        findViewById<Button>(R.id.startButton).setOnClickListener {
            lifecycleScope.launch {
                try {
                    controller.start(deviceId = "my-glasses-device-id")
                    Log.d(TAG, "Streaming started")
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to start", e)
                }
            }
        }

        // Stop streaming
        findViewById<Button>(R.id.stopButton).setOnClickListener {
            controller.stop()
        }
        
        // Finalize turn and get agent response
        findViewById<Button>(R.id.finalizeButton).setOnClickListener {
            lifecycleScope.launch {
                try {
                    val result = controller.finalizeTurn()
                    Log.d(TAG, "Agent response: ${result.response}")
                    // Execute actions
                    ActionExecutor.execute(result.actions, this@MyActivity)
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to finalize", e)
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        controller.stop()
    }
}
```

### Usage in Service

```kotlin
class StreamingService : Service() {
    private lateinit var controller: DatSmartGlassController
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    override fun onCreate() {
        super.onCreate()
        
        val rayBanManager = MetaRayBanManager(applicationContext)
        val smartGlassClient = SmartGlassClient()
        
        controller = DatSmartGlassController(rayBanManager, smartGlassClient)

        scope.launch {
            try {
                controller.start(deviceId = "device-123")
                
                // Run periodic turn finalization
                while (controller.state == DatSmartGlassController.State.STREAMING) {
                    delay(5000) // Every 5 seconds
                    val result = controller.finalizeTurn()
                    processResult(result)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Streaming error", e)
            }
        }
    }

    override fun onDestroy() {
        controller.stop()
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?) = null
    
    private fun processResult(result: AgentResult) {
        // Handle agent response
    }
}
```

### State Monitoring

```kotlin
lifecycleScope.launch {
    while (true) {
        when (controller.state) {
            DatSmartGlassController.State.IDLE -> {
                updateUI("Ready to start")
            }
            DatSmartGlassController.State.CONNECTING -> {
                updateUI("Connecting...")
            }
            DatSmartGlassController.State.STREAMING -> {
                updateUI("Streaming 🎥")
            }
            DatSmartGlassController.State.ERROR -> {
                updateUI("Error - please restart")
                break
            }
        }
        delay(1000)
    }
}
```

## API Reference

### Constructor

```kotlin
DatSmartGlassController(
    rayBanManager: MetaRayBanManager,
    smartGlassClient: SmartGlassClient,
    keyframeIntervalMs: Long = 500L
)
```

**Parameters:**
- `rayBanManager`: Manager for Meta Ray-Ban DAT SDK interactions
- `smartGlassClient`: Client for SmartGlass Python backend
- `keyframeIntervalMs`: Interval in milliseconds between sending video keyframes (default: 500ms)

### Methods

#### `suspend fun start(deviceId: String, transport: MetaRayBanManager.Transport = WIFI): AgentResult`

Start streaming from glasses to backend.

**Parameters:**
- `deviceId`: Meta Ray-Ban device ID to connect to
- `transport`: Transport mechanism (BLE or WIFI), defaults to WIFI

**Returns:** AgentResult after initial setup

**Throws:**
- `IOException`: if connection or session creation fails
- `IllegalStateException`: if controller is not in IDLE state

#### `fun stop()`

Stop streaming and clean up resources. Safe to call multiple times and from any state.

#### `suspend fun finalizeTurn(): AgentResult`

Finalize the current turn and get agent response. Sends all accumulated audio and frames to the backend.

**Returns:** AgentResult containing the agent's response and actions

**Throws:**
- `IllegalStateException`: if not in STREAMING state
- `IOException`: if the finalization request fails

### Properties

#### `val state: State`

Current state of the controller (read-only).

## Configuration

### Keyframe Interval

Control bandwidth usage by adjusting the keyframe interval:

```kotlin
// High quality, more bandwidth
val controller = DatSmartGlassController(
    rayBanManager, 
    client,
    keyframeIntervalMs = 200L  // 5 fps
)

// Lower bandwidth, less frequent frames
val controller = DatSmartGlassController(
    rayBanManager,
    client, 
    keyframeIntervalMs = 1000L  // 1 fps
)
```

### Transport Selection

Choose between BLE and WiFi:

```kotlin
// Use WiFi (faster, but requires WiFi connection)
controller.start(deviceId, transport = MetaRayBanManager.Transport.WIFI)

// Use Bluetooth LE (more portable, slower)
controller.start(deviceId, transport = MetaRayBanManager.Transport.BLE)
```

## Error Handling

The controller transitions to ERROR state when errors occur. Always check state before operations:

```kotlin
try {
    controller.start(deviceId)
} catch (e: IOException) {
    Log.e(TAG, "Connection failed", e)
    // Controller is now in ERROR state
    controller.stop()  // Clean up
    // Can start again after stop
}
```

## Best Practices

1. **Always call `stop()` in cleanup**: Call `stop()` in `onDestroy()` or service cleanup
2. **Monitor state transitions**: Log state changes for debugging
3. **Handle errors gracefully**: Catch exceptions from `start()` and `finalizeTurn()`
4. **Periodic finalization**: Call `finalizeTurn()` periodically to get agent responses
5. **Resource management**: Only create one controller instance per streaming session

## Testing

The controller includes comprehensive unit tests. Run with:

```bash
./gradlew :sdk-android:testDebugUnitTest --tests "com.smartglass.sdk.DatSmartGlassControllerTest"
```

See `DatSmartGlassControllerTest.kt` for example usage patterns.

## See Also

- [MetaRayBanManager](../rayban/MetaRayBanManager.kt) - Low-level DAT SDK interface
- [SmartGlassClient](SmartGlassClient.kt) - Backend HTTP client
- [ActionExecutor](ActionExecutor.kt) - Action execution framework
- [Meta DAT Integration Guide](../../../docs/meta_dat_integration.md)

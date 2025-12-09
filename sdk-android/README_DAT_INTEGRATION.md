# Meta DAT SDK Integration in MetaRayBanManager

This document describes the DAT SDK integration implemented in `MetaRayBanManager`.

## Overview

The `MetaRayBanManager` class now supports the official Meta Wearables Device Access Toolkit (DAT) SDK for Android. The implementation uses a facade pattern with three backend options:

1. **DatSdkFacade** - Official Meta DAT SDK integration (preferred)
2. **ReflectionSdkFacade** - Reflection-based wrapper for other SDK variants
3. **MockSdkFacade** - Mock implementation for testing without hardware

The loader automatically selects the best available option at runtime.

## Architecture

```
MetaRayBanManager
    └── SdkFacade (interface)
            ├── DatSdkFacade (uses Meta DAT SDK)
            ├── ReflectionSdkFacade (generic SDK wrapper)
            └── MockSdkFacade (testing/development)
```

## Public API

The public API remains stable and backward-compatible:

### Connection Management

```kotlin
// Connect to Meta Ray-Ban glasses
suspend fun connect(deviceId: String, transport: Transport)

// Disconnect from glasses
fun disconnect()
```

### Photo Capture

```kotlin
// Capture a single photo
suspend fun capturePhoto(): Bitmap?
```

### Video Streaming (New)

```kotlin
// Start continuous video streaming with frame callbacks
suspend fun startStreaming(onFrame: (frame: ByteArray, timestampMs: Long) -> Unit)

// Stop streaming
fun stopStreaming()
```

### Audio Streaming

```kotlin
// Start audio streaming (returns Flow of audio chunks)
fun startAudioStreaming(): Flow<ByteArray>

// Stop audio streaming
fun stopAudioStreaming()
```

## DAT SDK Integration Details

### Device Registration

The DAT SDK requires users to pair their glasses through the Meta AI companion app. The integration handles this flow:

```kotlin
// Initiates pairing flow via Meta AI app
Wearables.startRegistration(context)

// Monitor registration state
Wearables.registrationState.collect { state ->
    when (state) {
        is RegistrationState.Registered -> // Connected
        is RegistrationState.Unregistered -> // Not connected
        // ... other states
    }
}
```

### Video Streaming

Video streaming uses the DAT SDK's `StreamSession` API:

```kotlin
// Create streaming session with AutoDeviceSelector
val session = Wearables.startStreamSession(
    context,
    AutoDeviceSelector(),
    StreamConfiguration(
        videoQuality = VideoQuality.MEDIUM,
        frameRate = 24
    )
)

// Collect video frames
session.videoStream.collect { videoFrame ->
    // VideoFrame contains I420 format data
    val jpegBytes = convertI420toJpeg(videoFrame)
    onFrame(jpegBytes, timestamp)
}
```

### Photo Capture

Photos are captured during an active streaming session:

```kotlin
session.capturePhoto().onSuccess { photoData ->
    when (photoData) {
        is PhotoData.Bitmap -> // Use bitmap directly
        is PhotoData.HEIC -> // Decode HEIC to bitmap
    }
}
```

### Video Format Conversion

The DAT SDK provides video frames in I420 format (YUV planar). The integration converts these to JPEG for compatibility with the SmartGlass backend:

```kotlin
I420 (YYYYYYYY:UUVV) → NV21 (YYYYYYYY:VUVU) → JPEG
```

## TODO: App-Specific UX Decisions

The following areas require app-specific implementation:

### 1. Permission Management

```kotlin
// TODO: Implement permission request flow
// Check camera permission status
val permissionStatus = Wearables.checkPermissionStatus(Permission.CAMERA)

if (permissionStatus != PermissionStatus.Granted) {
    // Show permission rationale UI
    // Request permission via Meta AI app
    val result = Wearables.requestPermission(Permission.CAMERA)
    // Handle result
}
```

### 2. Device Selection UI

```kotlin
// TODO: Implement device selection screen
// Monitor available devices
Wearables.devices.collect { devices ->
    // Display list of paired glasses
    // Allow user to select preferred device
}
```

### 3. Registration Flow

```kotlin
// TODO: Implement registration UI
// Guide user through pairing:
// 1. Open Meta AI app
// 2. Navigate to Connected Devices
// 3. Add SmartGlass AI Agent
// 4. Wait for registration to complete
```

### 4. Error Handling

```kotlin
// TODO: Implement user-friendly error handling
// - Device offline/out of range
// - Battery too low for streaming
// - Permission denied
// - Network connectivity issues
```

### 5. Settings Screen

```kotlin
// TODO: Implement settings UI
// - Video quality preference (LOW/MEDIUM/HIGH)
// - Frame rate selection
// - Audio streaming toggle
// - Analytics opt-out toggle
```

## Dependencies

### Required (compileOnly in SDK)

```kotlin
dependencies {
    compileOnly("com.meta.wearable:mwdat-core:0.2.1")
    compileOnly("com.meta.wearable:mwdat-camera:0.2.1")
    compileOnly("com.meta.wearable:mwdat-mockdevice:0.2.1")
}
```

### Repository Configuration

```kotlin
repositories {
    maven {
        url = uri("https://maven.pkg.github.com/facebook/meta-wearables-dat-android")
        credentials {
            username = ""
            password = System.getenv("GITHUB_TOKEN") ?: ""
        }
    }
}
```

## AndroidManifest Configuration

### Required Permissions

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.BLUETOOTH" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
```

### Analytics Opt-Out (Optional)

```xml
<application>
    <meta-data
        android:name="com.meta.wearable.mwdat.ANALYTICS_OPT_OUT"
        android:value="true" />
    
    <meta-data
        android:name="com.meta.wearable.mwdat.APPLICATION_ID"
        android:value="your_app_id_from_developer_portal" />
</application>
```

## Testing

### Unit Tests

The test suite includes:
- Connection flow validation
- Photo capture delegation
- Audio streaming lifecycle
- Video streaming with frame callbacks
- Mock fallback behavior

### Mock Device Kit

For development without physical glasses:

```kotlin
val mockProvider = MockDeviceKit.getInstance(context)
// Configure mock device for testing
mockProvider.pairedDevices // Access simulated devices
```

## Usage Example

```kotlin
class MainActivity : AppCompatActivity() {
    private lateinit var manager: MetaRayBanManager
    private var sessionActive = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize manager
        manager = MetaRayBanManager(this)
        
        // Connect button
        findViewById<Button>(R.id.btnConnect).setOnClickListener {
            lifecycleScope.launch {
                connectAndStream()
            }
        }
    }

    private suspend fun connectAndStream() {
        try {
            // Connect to glasses
            manager.connect("RAYBAN-001", MetaRayBanManager.Transport.BLE)
            
            // Start video streaming
            manager.startStreaming { frame, timestamp ->
                lifecycleScope.launch {
                    processFrame(frame, timestamp)
                }
            }
            
            sessionActive = true
        } catch (e: Exception) {
            Log.e("MainActivity", "Connection failed", e)
            // TODO: Show error to user
        }
    }

    private suspend fun processFrame(jpegBytes: ByteArray, timestamp: Long) {
        // Send to SmartGlass AI backend
        val response = aiClient.sendFrame(
            sessionId = sessionId,
            jpegBytes = jpegBytes,
            width = 1280,
            height = 720
        )
        
        // Update UI with response
        runOnUiThread {
            textView.text = response.text
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (sessionActive) {
            manager.stopStreaming()
            manager.disconnect()
        }
    }
}
```

## References

- [Meta Wearables Developer Center](https://developers.meta.com/wearables)
- [DAT SDK Android Repository](https://github.com/facebook/meta-wearables-dat-android)
- [DAT SDK Documentation](https://wearables.developer.meta.com/docs/develop/)
- [SmartGlass Meta DAT Integration Guide](../../docs/meta_dat_integration.md)
- [Hello SmartGlass Quickstart](../../docs/hello_smartglass_quickstart.md)

## Changelog

### v1.1.0 (Current)
- Added DatSdkFacade for official Meta DAT SDK
- Added startStreaming/stopStreaming methods with frame callbacks
- Implemented I420 to JPEG conversion for video frames
- Added PhotoData.HEIC support
- Updated MockSdkFacade for new streaming API
- Maintained backward compatibility with existing API

### v1.0.0 (Previous)
- Initial MetaRayBanManager with mock implementation
- Basic connect/disconnect/capturePhoto API
- Audio streaming via Flow

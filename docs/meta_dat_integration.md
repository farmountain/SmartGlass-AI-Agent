# Meta Wearables Device Access Toolkit (DAT) Integration Guide

This guide provides comprehensive instructions for integrating the Meta Wearables Device Access Toolkit with the SmartGlass-AI-Agent project to enable AI-powered experiences on Ray-Ban Meta and Ray-Ban Display glasses.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Platform Setup](#platform-setup)
4. [Core Concepts](#core-concepts)
5. [Architecture](#architecture)
6. [Getting Started](#getting-started)
7. [Implementation Examples](#implementation-examples)
8. [Privacy and Compliance](#privacy-and-compliance)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Meta Wearables Device Access Toolkit (DAT) enables developers to:
- Access camera streams from Ray-Ban Meta glasses
- Capture photos from the glasses
- Receive microphone audio input
- Use Mock Device Kit for development without physical hardware

### What Lives Under `/docs/develop/`

Based on Meta's announcement and SDK documentation, the Developer Portal contains:

1. **Getting Started**
   - Create Meta Managed Account
   - Create Organization and Project
   - Apply for Developer Preview access
   - Register your app (bundle ID / package name)

2. **Platform Setup**
   - Android SDK configuration
   - iOS SDK configuration
   - Dependencies and authentication

3. **Core Concepts**
   - Connecting to glasses
   - Media streaming
   - Photo capture
   - Error handling
   - Mock Device Kit usage

4. **Permissions & Privacy**
   - Developer Terms
   - Acceptable Use Policy
   - Analytics opt-out
   - User consent requirements

5. **Sample Applications**
   - Camera access examples
   - Basic connection flows
   - UI rendering patterns

---

## Prerequisites

### Developer Account Setup

1. **Meta Managed Account**: Create or access your account at the [Wearables Developer Center](https://developers.meta.com/wearables)
2. **Organization**: Create an organization and add your user
3. **Project**: Create a new project for "SmartGlass-AI-Agent"
4. **Developer Preview Access**: Apply via the interest form
5. **App Registration**: Register your app with bundle ID (iOS) or package name (Android)

### Development Environment

- **Android**: Android Studio with Kotlin support, API level 24+
- **iOS**: Xcode 15+ with Swift 5.9+
- **Python**: 3.9+ (for backend integration)
- **Network**: Access to GitHub Maven repositories

---

## Platform Setup

### Android Configuration

#### 1. Add GitHub Maven Repository

Add the Meta Wearables DAT repository to your `build.gradle.kts`:

```kotlin
repositories {
    maven {
        url = uri("https://maven.pkg.github.com/facebook/meta-wearables-dat-android")
        credentials {
            username = ""  // Leave empty for public access
            password = System.getenv("GITHUB_TOKEN") ?: ""  // Personal access token
        }
    }
}
```

#### 2. Add SDK Dependencies

```kotlin
dependencies {
    implementation("com.meta.wearable:mwdat-core:0.2.1")
    implementation("com.meta.wearable:mwdat-camera:0.2.1")
    implementation("com.meta.wearable:mwdat-mockdevice:0.2.1")
}
```

#### 3. Configure Permissions

Add required permissions to `AndroidManifest.xml`:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.BLUETOOTH" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
    
    <application>
        <!-- Opt-out of analytics (optional) -->
        <meta-data
            android:name="ANALYTICS_OPT_OUT"
            android:value="true" />
    </application>
</manifest>
```

### iOS Configuration

#### 1. Add Swift Package

1. Open Xcode → File → Add Package Dependencies
2. Enter URL: `https://github.com/facebook/meta-wearables-dat-ios`
3. Select `meta-wearables-dat-ios` package
4. Choose version (latest stable recommended)
5. Add to your app target

#### 2. Configure Info.plist

Add analytics opt-out (optional):

```xml
<key>MWDAT</key>
<dict>
    <key>Analytics</key>
    <dict>
        <key>OptOut</key>
        <true/>
    </dict>
</dict>
```

#### 3. Import Framework

```swift
import MetaWearablesDAT
```

---

## Core Concepts

### Runtime Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Mobile App                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  1. Request Connection via Meta AI App               │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  2. User Confirms Permissions in Meta AI             │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  3. Receive Camera Frames / Audio Stream             │  │
│  │     - Get video stream (30 fps typical)              │  │
│  │     - Capture still photos                           │  │
│  │     - Process microphone audio                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  4. Send to SmartGlass AI Backend                    │  │
│  │     - Video/audio via WebSocket or HTTP              │  │
│  │     - Extract features                               │  │
│  │     - Get AI responses                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  5. Handle Errors / Disconnects                      │  │
│  │     - Battery low                                     │  │
│  │     - Bluetooth drop                                  │  │
│  │     - User revoked permission                        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Connection States

- **Disconnected**: No active connection to glasses
- **Connecting**: Establishing connection via Meta AI
- **Connected**: Active connection, ready for streaming
- **Streaming**: Actively receiving camera/audio data
- **Error**: Connection issue requiring user intervention

### Error Handling

Common error scenarios:
- **Permission Denied**: User declined camera/mic access
- **Device Offline**: Glasses out of range or powered off
- **Battery Low**: Glasses battery below threshold
- **Network Error**: Backend connection issues
- **SDK Error**: Internal SDK failures

---

## Architecture

### SmartGlass-AI-Agent + Meta DAT Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Ray-Ban Meta / Ray-Ban Display                  │
│                        (Camera + Microphone)                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Bluetooth / WiFi
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                       Mobile App (Edge Sensor Hub)                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Meta DAT SDK Integration                                    │   │
│  │  - Camera stream handler                                     │   │
│  │  - Microphone stream handler                                 │   │
│  │  - Photo capture manager                                     │   │
│  │  - Connection state manager                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                             ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Frame Processing & Batching                                 │   │
│  │  - Downsample to 2-5 fps for AI processing                  │   │
│  │  - JPEG compression                                          │   │
│  │  - Audio chunking (16kHz PCM)                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                             ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Backend Communication Layer                                  │   │
│  │  - WebSocket for real-time streaming                        │   │
│  │  - HTTP/REST for request-response                           │   │
│  │  - SmartGlassEdgeClient (existing SDK)                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTP/WebSocket
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                   SmartGlass AI Backend                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  FastAPI / Edge Runtime Server                               │   │
│  │  - Session management                                        │   │
│  │  - Audio ingestion (Whisper)                                │   │
│  │  - Frame ingestion (CLIP/DeepSeek-Vision)                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                             ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  SmartGlassAgent Core                                        │   │
│  │  - Multimodal query processing                              │   │
│  │  - AUREUS/HipCortex reasoning                               │   │
│  │  - Do-Attention goal selection                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                             ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Response Generation                                         │   │
│  │  - SNNLLMBackend (on-device capable)                        │   │
│  │  - GPT-2 / Llama-3.2-3B (cloud)                            │   │
│  │  - Action commands (navigation, notifications)              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Response (Text + Actions)
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                       Mobile App UI                                 │
│  - Display AI responses                                             │
│  - TTS for audio output (optional)                                  │
│  - Execute actions (navigation, notifications)                      │
│  - Update connection status                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### 1. Mobile App (Edge Sensor Hub)
- **Role**: Interface with glasses hardware via Meta DAT SDK
- **Responsibilities**:
  - Manage connection lifecycle
  - Stream camera and microphone data
  - Batch and compress data for backend
  - Display responses and execute actions
  - Handle offline/error states

#### 2. SmartGlass AI Backend
- **Role**: Process multimodal inputs and generate intelligent responses
- **Responsibilities**:
  - Transcribe audio (Whisper)
  - Analyze visual scenes (CLIP/DeepSeek-Vision)
  - Reason about context (AUREUS/Do-Attention)
  - Generate responses (SNN/LLM)
  - Emit structured actions

#### 3. Meta DAT SDK
- **Role**: Hardware abstraction layer
- **Responsibilities**:
  - Camera streaming
  - Microphone streaming
  - Photo capture
  - Connection management

---

## Getting Started

### Step 1: Clone Sample SDK

Choose your target platform:

**Android:**
```bash
git clone https://github.com/facebook/meta-wearables-dat-android.git
cd meta-wearables-dat-android/samples/CameraAccess
```

**iOS:**
```bash
git clone https://github.com/facebook/meta-wearables-dat-ios.git
cd meta-wearables-dat-ios/samples/CameraAccess
```

### Step 2: Build and Run Sample

Verify the sample app builds and runs:
- Connect to Mock Device (no hardware needed)
- Observe simulated camera frames
- Test capture functionality

### Step 3: Add AI Agent Hook

Integrate with SmartGlass backend in the frame callback:

**Android (Kotlin):**
```kotlin
import com.smartglass.sdk.SmartGlassEdgeClient

class CameraHandler {
    private val client = SmartGlassEdgeClient(
        baseUrl = "http://192.168.1.50:8765"
    )
    private var sessionId: String? = null
    private var frameCount = 0
    
    suspend fun onFrameReceived(frame: CameraFrame) {
        // Initialize session on first frame
        if (sessionId == null) {
            sessionId = client.createSession()
        }
        
        // Send every 5th frame (approx 6 fps from 30 fps stream)
        frameCount++
        if (frameCount % 5 == 0) {
            val jpegBytes = frame.toJpegBytes()
            val response = client.sendFrame(
                sessionId = sessionId!!,
                jpegBytes = jpegBytes,
                width = frame.width,
                height = frame.height
            )
            
            // Log response for debugging
            Log.d("SmartGlass", "Backend response: ${response.response}")
        }
    }
    
    suspend fun onAudioChunk(audio: AudioChunk) {
        if (sessionId != null) {
            client.sendAudioChunk(
                sessionId = sessionId!!,
                audioData = audio.pcmData,
                sampleRate = audio.sampleRate
            )
        }
    }
}
```

**iOS (Swift):**
```swift
import MetaWearablesDAT

class CameraHandler {
    let client: SmartGlassEdgeClient
    var sessionId: String?
    var frameCount = 0
    
    init(baseURL: String) {
        self.client = SmartGlassEdgeClient(baseUrl: baseURL)
    }
    
    func onFrameReceived(frame: CameraFrame) async throws {
        // Initialize session on first frame
        if sessionId == nil {
            sessionId = try await client.createSession()
        }
        
        // Send every 5th frame
        frameCount += 1
        if frameCount % 5 == 0 {
            guard let jpegData = frame.jpegRepresentation() else { return }
            
            let response = try await client.sendFrame(
                sessionId: sessionId!,
                jpegBytes: jpegData,
                width: frame.width,
                height: frame.height
            )
            
            print("Backend response: \(response.response ?? "")")
        }
    }
}
```

### Step 4: Start Backend Server

Run the SmartGlass AI backend:

```bash
cd SmartGlass-AI-Agent

# Using edge runtime (recommended)
export PROVIDER=meta
python -m src.edge_runtime.server --host 0.0.0.0 --port 8765

# Or using Python HTTP server
export SDK_PYTHON_DUMMY_AGENT=1
python -m sdk_python.server --host 0.0.0.0 --port 8000
```

### Step 5: Test End-to-End

1. Run mobile app with Mock Device
2. Observe frames being sent to backend
3. Check backend logs for processing
4. Verify responses return to mobile app

---

## Implementation Examples

### Example 1: Basic Frame Streaming

**Android Activity:**
```kotlin
class MainActivity : AppCompatActivity() {
    private lateinit var metaManager: MetaRayBanManager
    private lateinit var aiClient: SmartGlassEdgeClient
    private var sessionId: String? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        // Initialize Meta DAT SDK wrapper
        metaManager = MetaRayBanManager(this)
        
        // Initialize AI backend client
        aiClient = SmartGlassEdgeClient(
            baseUrl = getString(R.string.backend_url)
        )
        
        setupUI()
    }
    
    private fun setupUI() {
        findViewById<Button>(R.id.btnConnect).setOnClickListener {
            lifecycleScope.launch {
                connectToGlasses()
            }
        }
        
        findViewById<Button>(R.id.btnCapture).setOnClickListener {
            lifecycleScope.launch {
                captureAndProcess()
            }
        }
    }
    
    private suspend fun connectToGlasses() {
        try {
            // Connect to glasses
            metaManager.connect(
                deviceId = "RAYBAN-001",
                transport = "ble"
            )
            
            // Create AI session
            sessionId = aiClient.createSession()
            
            // Start streaming
            startCameraStream()
            
            Toast.makeText(this, "Connected!", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Log.e("MainActivity", "Connection failed", e)
            Toast.makeText(this, "Connection failed: ${e.message}", 
                Toast.LENGTH_LONG).show()
        }
    }
    
    private suspend fun startCameraStream() {
        metaManager.startCameraStreaming { frame ->
            lifecycleScope.launch {
                processFrame(frame)
            }
        }
    }
    
    private suspend fun processFrame(frame: Bitmap) {
        try {
            val stream = ByteArrayOutputStream()
            frame.compress(Bitmap.CompressFormat.JPEG, 80, stream)
            val jpegBytes = stream.toByteArray()
            
            val response = aiClient.sendFrame(
                sessionId = sessionId!!,
                jpegBytes = jpegBytes,
                width = frame.width,
                height = frame.height
            )
            
            // Update UI with AI response
            runOnUiThread {
                findViewById<TextView>(R.id.tvResponse).text = 
                    response.response ?: "Processing..."
            }
        } catch (e: Exception) {
            Log.e("MainActivity", "Frame processing failed", e)
        }
    }
    
    private suspend fun captureAndProcess() {
        try {
            val photo = metaManager.capturePhoto()
            processFrame(photo)
        } catch (e: Exception) {
            Log.e("MainActivity", "Capture failed", e)
        }
    }
}
```

### Example 2: Audio + Vision Multimodal Query

**Python Backend Integration:**
```python
from src.smartglass_agent import SmartGlassAgent
from src.llm_snn_backend import SNNLLMBackend
import numpy as np

# Initialize agent
snn_backend = SNNLLMBackend(model_path="artifacts/snn_student/student.pt")
agent = SmartGlassAgent(
    whisper_model="base",
    clip_model="openai/clip-vit-base-patch32",
    llm_backend=snn_backend,
    provider="meta"  # Use Meta Ray-Ban provider
)

async def process_multimodal_stream(session_id: str, 
                                   audio_chunk: np.ndarray,
                                   frame_bytes: bytes):
    """Process audio and video from Meta DAT stream."""
    
    # Transcribe audio
    transcript = agent.whisper_processor.transcribe(audio_chunk)
    
    # Analyze frame
    from PIL import Image
    import io
    image = Image.open(io.BytesIO(frame_bytes))
    
    # Run multimodal query
    result = agent.process_multimodal_query(
        text_query=transcript,
        image_input=image
    )
    
    # Extract response and actions
    response_text = result.get("response", "")
    actions = result.get("actions", [])
    
    # Log for debugging
    print(f"Transcript: {transcript}")
    print(f"Response: {response_text}")
    print(f"Actions: {actions}")
    
    return {
        "transcript": transcript,
        "response": response_text,
        "actions": actions
    }
```

### Example 3: Mock Device Development

For development without physical glasses:

**Android Mock Setup:**
```kotlin
import com.meta.wearable.mockdevice.MockDeviceProvider

class DevelopmentActivity : AppCompatActivity() {
    private lateinit var mockProvider: MockDeviceProvider
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize Mock Device
        mockProvider = MockDeviceProvider.Builder()
            .withCameraSimulation(true)
            .withAudioSimulation(true)
            .withFrameRate(30)
            .build()
        
        // Use mock provider for testing
        testWithMockData()
    }
    
    private fun testWithMockData() {
        lifecycleScope.launch {
            // Simulate frames from mock device
            mockProvider.getCameraFrames().collect { frame ->
                processFrame(frame)
            }
        }
    }
}
```

**iOS Mock Setup:**
```swift
import MetaWearablesDAT

class DevelopmentViewController: UIViewController {
    var mockProvider: MockDeviceProvider?
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        // Initialize Mock Device
        mockProvider = MockDeviceProvider.Builder()
            .withCameraSimulation(true)
            .withAudioSimulation(true)
            .withFrameRate(30)
            .build()
        
        testWithMockData()
    }
    
    func testWithMockData() {
        Task {
            // Simulate frames from mock device
            for await frame in mockProvider!.cameraFrames {
                await processFrame(frame)
            }
        }
    }
}
```

---

## Privacy and Compliance

### Meta Wearables Developer Terms

All apps using Meta DAT must comply with:
- **Meta Wearables Developer Terms**: Govern SDK usage
- **Acceptable Use Policy**: Define prohibited use cases
- **Privacy Requirements**: User consent and data handling

### Data Handling Best Practices

1. **Minimize Data Collection**: Only collect what's necessary
2. **User Consent**: Always obtain explicit consent before accessing camera/mic
3. **Transparent Processing**: Inform users how data is processed
4. **Secure Transmission**: Use HTTPS/TLS for all backend communication
5. **Data Retention**: Define clear retention policies
6. **Deletion Rights**: Honor user requests to delete data

### Edge Runtime Privacy Controls

SmartGlass-AI-Agent provides privacy controls:

```bash
# Environment variables for privacy
export STORE_RAW_AUDIO=false     # Don't retain audio
export STORE_RAW_FRAMES=false    # Don't retain frames
export STORE_TRANSCRIPTS=false   # Don't retain transcripts
```

See [PRIVACY.md](../PRIVACY.md) for detailed guidelines.

### Analytics Opt-Out

**Android:**
```xml
<meta-data
    android:name="ANALYTICS_OPT_OUT"
    android:value="true" />
```

**iOS:**
```xml
<key>MWDAT</key>
<dict>
    <key>Analytics</key>
    <dict>
        <key>OptOut</key>
        <true/>
    </dict>
</dict>
```

---

## Troubleshooting

### Common Issues

#### 1. GitHub Maven Authentication

**Problem**: Cannot download Meta DAT dependencies

**Solution**: Generate GitHub Personal Access Token
```bash
# Create token at https://github.com/settings/tokens
# Set environment variable
export GITHUB_TOKEN="ghp_your_token_here"
```

#### 2. Connection Timeout

**Problem**: Glasses won't connect via Meta AI app

**Solutions**:
- Ensure glasses are powered on and charged
- Verify Bluetooth is enabled on phone
- Check Meta AI app is installed and updated
- Try resetting glasses (hold button for 10 seconds)

#### 3. Frame Rate Issues

**Problem**: Frames arriving too slowly or quickly

**Solution**: Adjust frame sampling rate
```kotlin
// Send every Nth frame
if (frameCount % N == 0) {
    sendToBackend(frame)
}
```

#### 4. Backend Connection Failed

**Problem**: Cannot reach SmartGlass backend

**Solutions**:
- Check backend is running: `curl http://backend-ip:8765/health`
- Verify firewall allows connections
- For emulator: use `10.0.2.2` instead of `localhost`
- For physical device: use LAN IP address

#### 5. Mock Device Not Working

**Problem**: Mock Device Kit not providing frames

**Solutions**:
- Verify `mwdat-mockdevice` dependency is included
- Check Mock Device is properly initialized
- Look for initialization errors in logs

---

## Next Steps

1. **Apply for Preview Access**: Submit interest form to Meta
2. **Clone Sample Apps**: Get Android or iOS samples running
3. **Set Up Backend**: Deploy SmartGlass-AI-Agent backend
4. **Integrate AI Hook**: Add backend calls in frame callbacks
5. **Test with Mock Device**: Validate end-to-end flow
6. **Add Features**: Implement actions, TTS, notifications
7. **Hardware Testing**: Test with real Ray-Ban Meta glasses
8. **Privacy Review**: Ensure compliance with all terms
9. **Production Deploy**: Package and distribute your app

## Additional Resources

- [Meta Wearables Developer Center](https://developers.meta.com/wearables)
- [SmartGlass-AI-Agent Documentation](../README.md)
- [Android SDK Guide](../ANDROID_SDK.md)
- [Edge Runtime Documentation](../docs/android_integration.md)
- [Privacy Guidelines](../PRIVACY.md)
- [RaySkillKit Actions](actions_and_skills.md)

---

**Built with ❤️ for AI-powered wearables**

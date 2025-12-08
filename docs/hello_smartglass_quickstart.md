# Hello SmartGlass-AI-Agent: Quickstart Guide

A step-by-step guide to building your first AI-powered smart glasses application using Meta Ray-Ban glasses and the SmartGlass-AI-Agent stack.

## 🎯 What You'll Build

A simple mobile app that:
1. Connects to Ray-Ban Meta glasses
2. Streams camera frames to an AI backend
3. Gets intelligent scene descriptions
4. Displays responses to the user

**Time to complete**: ~30 minutes  
**Difficulty**: Beginner  
**Prerequisites**: Basic Android or iOS development knowledge

---

## 📋 Prerequisites

### Accounts & Access
- [ ] Meta Managed Account (created at developers.meta.com/wearables)
- [ ] Developer Preview access (applied and approved)
- [ ] GitHub account with personal access token

### Development Tools
- [ ] **Android**: Android Studio Arctic Fox or later
- [ ] **iOS**: Xcode 15+ with Swift 5.9+
- [ ] **Backend**: Python 3.9+ installed
- [ ] Git command line tools

### Optional Hardware
- [ ] Ray-Ban Meta glasses (can use Mock Device without)
- [ ] Android phone or iPhone for testing

---

## 🚀 Choose Your Platform

Pick your platform to get started:

- **[Android Path](#android-implementation)** - Kotlin + Jetpack Compose
- **[iOS Path](#ios-implementation)** - Swift + SwiftUI

Both paths follow the same architecture and connect to the same Python backend.

---

## 🏗️ Architecture Overview

```
┌──────────────────┐
│   Ray-Ban Meta   │  Camera + Mic
│     Glasses      │
└────────┬─────────┘
         │ Bluetooth
         │
┌────────▼─────────┐
│   Mobile App     │  Frame sampling
│  (Your code!)    │  JPEG compression
└────────┬─────────┘
         │ HTTP/WebSocket
         │
┌────────▼─────────┐
│  Python Backend  │  Whisper (audio)
│  SmartGlassAgent │  CLIP (vision)
│                  │  SNN/LLM (text)
└──────────────────┘
```

**Data Flow:**
1. Glasses capture video at 30 fps
2. Mobile app samples every 5th frame (~6 fps)
3. Frames sent to backend as JPEG
4. Backend returns AI-generated response
5. Mobile app displays response

---

## 🐍 Step 1: Set Up Python Backend

First, let's get the AI backend running on your development machine.

### Clone Repository

```bash
git clone https://github.com/farmountain/SmartGlass-AI-Agent.git
cd SmartGlass-AI-Agent
```

### Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Start Backend Server

For quick testing, use the dummy agent (no model downloads needed):

```bash
export SDK_PYTHON_DUMMY_AGENT=1
export PROVIDER=meta
python -m sdk_python.server --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Verify Backend

Test the health endpoint:
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

**Note your backend URL**:
- **Local testing**: `http://localhost:8000`
- **Android Emulator**: `http://10.0.2.2:8000`
- **Physical Device**: `http://YOUR_COMPUTER_IP:8000` (e.g., `http://192.168.1.100:8000`)

---

## 📱 Android Implementation

### Step 2: Create New Android Project

1. Open Android Studio
2. New Project → Empty Activity
3. Name: `HelloSmartGlass`
4. Package: `com.example.hellosmartglass`
5. Language: Kotlin
6. Minimum SDK: API 24

### Step 3: Configure Dependencies

**`settings.gradle.kts`:**
```kotlin
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        
        // Meta Wearables DAT
        maven {
            url = uri("https://maven.pkg.github.com/facebook/meta-wearables-dat-android")
            credentials {
                username = ""
                password = System.getenv("GITHUB_TOKEN") ?: ""
            }
        }
        
        // SmartGlass SDK (local path for development)
        maven {
            url = uri("file://${rootProject.projectDir}/../SmartGlass-AI-Agent/sdk-android")
        }
    }
}
```

**`app/build.gradle.kts`:**
```kotlin
dependencies {
    // Android basics
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0")
    
    // Meta Wearables DAT SDK
    implementation("com.meta.wearable:mwdat-core:0.2.1")
    implementation("com.meta.wearable:mwdat-camera:0.2.1")
    implementation("com.meta.wearable:mwdat-mockdevice:0.2.1")
    
    // SmartGlass Android SDK (use the local module)
    implementation(project(":sdk-android"))
    
    // HTTP client
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.0")
}
```

### Step 4: Add Permissions

**`AndroidManifest.xml`:**
```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.BLUETOOTH" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
    
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/Theme.AppCompat.Light.DarkActionBar">
        
        <!-- Opt out of Meta analytics -->
        <meta-data
            android:name="ANALYTICS_OPT_OUT"
            android:value="true" />
        
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

### Step 5: Create Main Activity

**`MainActivity.kt`:**
```kotlin
package com.example.hellosmartglass

import android.graphics.Bitmap
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.smartglass.sdk.SmartGlassEdgeClient
import com.smartglass.sdk.rayban.MetaRayBanManager
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream

class MainActivity : AppCompatActivity() {
    
    private val TAG = "HelloSmartGlass"
    
    // UI Components
    private lateinit var btnConnect: Button
    private lateinit var btnCapture: Button
    private lateinit var imgPreview: ImageView
    private lateinit var tvStatus: TextView
    private lateinit var tvResponse: TextView
    
    // SDK Components
    private lateinit var metaManager: MetaRayBanManager
    private lateinit var aiClient: SmartGlassEdgeClient
    
    private var sessionId: String? = null
    private var isConnected = false
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        initializeUI()
        initializeSDKs()
    }
    
    private fun initializeUI() {
        btnConnect = findViewById(R.id.btnConnect)
        btnCapture = findViewById(R.id.btnCapture)
        imgPreview = findViewById(R.id.imgPreview)
        tvStatus = findViewById(R.id.tvStatus)
        tvResponse = findViewById(R.id.tvResponse)
        
        btnConnect.setOnClickListener {
            lifecycleScope.launch {
                if (isConnected) {
                    disconnect()
                } else {
                    connect()
                }
            }
        }
        
        btnCapture.setOnClickListener {
            lifecycleScope.launch {
                captureAndAnalyze()
            }
        }
        
        // Initially disable capture button
        btnCapture.isEnabled = false
    }
    
    private fun initializeSDKs() {
        // Initialize Meta Ray-Ban Manager (supports Mock Device)
        metaManager = MetaRayBanManager(this)
        
        // Initialize SmartGlass AI Client
        // Change this URL based on your setup:
        // - Emulator: "http://10.0.2.2:8000"
        // - Physical device: "http://YOUR_COMPUTER_IP:8000"
        aiClient = SmartGlassEdgeClient(
            baseUrl = "http://10.0.2.2:8000"  // Adjust as needed
        )
        
        updateStatus("Ready to connect")
    }
    
    private suspend fun connect() {
        try {
            updateStatus("Connecting to glasses...")
            
            // Connect to glasses (or Mock Device)
            val connected = metaManager.connect(
                deviceId = "RAYBAN-MOCK-001",
                transport = "mock"  // Use "ble" for real glasses
            )
            
            if (!connected) {
                throw Exception("Failed to connect to glasses")
            }
            
            // Create AI session
            updateStatus("Creating AI session...")
            sessionId = aiClient.startSession(text = "Hello from HelloSmartGlass!")
            
            isConnected = true
            updateStatus("Connected! Ready to capture.")
            
            runOnUiThread {
                btnConnect.text = "Disconnect"
                btnCapture.isEnabled = true
            }
            
            Toast.makeText(this, "Connected successfully!", Toast.LENGTH_SHORT).show()
            
        } catch (e: Exception) {
            Log.e(TAG, "Connection failed", e)
            updateStatus("Connection failed: ${e.message}")
            Toast.makeText(this, "Connection failed", Toast.LENGTH_LONG).show()
        }
    }
    
    private suspend fun disconnect() {
        try {
            updateStatus("Disconnecting...")
            
            // Close AI session if exists
            sessionId?.let { sid ->
                // Note: Add closeSession to SmartGlassClient if needed
                sessionId = null
            }
            
            isConnected = false
            updateStatus("Disconnected")
            
            runOnUiThread {
                btnConnect.text = "Connect"
                btnCapture.isEnabled = false
                imgPreview.setImageResource(android.R.drawable.ic_menu_camera)
                tvResponse.text = ""
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Disconnect failed", e)
        }
    }
    
    private suspend fun captureAndAnalyze() {
        if (!isConnected || sessionId == null) {
            Toast.makeText(this, "Not connected!", Toast.LENGTH_SHORT).show()
            return
        }
        
        try {
            updateStatus("Capturing photo...")
            
            // Capture photo from glasses
            val photo = metaManager.capturePhoto()
            
            // Display preview
            runOnUiThread {
                imgPreview.setImageBitmap(photo)
            }
            
            updateStatus("Analyzing with AI...")
            
            // Convert to JPEG bytes
            val stream = ByteArrayOutputStream()
            photo.compress(Bitmap.CompressFormat.JPEG, 85, stream)
            val jpegBytes = stream.toByteArray()
            
            // Send to AI backend
            val response = aiClient.answer(
                sessionId = sessionId!!,
                text = "What do you see in this image?",
                imagePath = null  // We're sending bytes directly
                // Note: May need to modify SmartGlassClient to accept bytes
            )
            
            // Display response
            val responseText = response.response ?: "No response"
            updateStatus("Analysis complete")
            
            runOnUiThread {
                tvResponse.text = responseText
            }
            
            Log.d(TAG, "AI Response: $responseText")
            
        } catch (e: Exception) {
            Log.e(TAG, "Capture and analyze failed", e)
            updateStatus("Analysis failed: ${e.message}")
            Toast.makeText(this, "Analysis failed", Toast.LENGTH_LONG).show()
        }
    }
    
    private fun updateStatus(status: String) {
        Log.d(TAG, "Status: $status")
        runOnUiThread {
            tvStatus.text = status
        }
    }
}
```

### Step 6: Create Layout

**`res/layout/activity_main.xml`:**
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">
    
    <TextView
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Hello SmartGlass AI Agent"
        android:textSize="24sp"
        android:textStyle="bold"
        android:gravity="center"
        android:layout_marginBottom="16dp" />
    
    <TextView
        android:id="@+id/tvStatus"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Ready to connect"
        android:textSize="16sp"
        android:gravity="center"
        android:layout_marginBottom="16dp" />
    
    <Button
        android:id="@+id/btnConnect"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Connect"
        android:layout_marginBottom="8dp" />
    
    <Button
        android:id="@+id/btnCapture"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Capture &amp; Analyze"
        android:enabled="false"
        android:layout_marginBottom="16dp" />
    
    <ImageView
        android:id="@+id/imgPreview"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:src="@android:drawable/ic_menu_camera"
        android:scaleType="centerInside"
        android:contentDescription="Camera preview"
        android:layout_marginBottom="16dp" />
    
    <TextView
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="AI Response:"
        android:textStyle="bold"
        android:textSize="14sp"
        android:layout_marginBottom="8dp" />
    
    <ScrollView
        android:layout_width="match_parent"
        android:layout_height="120dp"
        android:background="@android:color/darker_gray"
        android:padding="8dp">
        
        <TextView
            android:id="@+id/tvResponse"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textColor="@android:color/white"
            android:textSize="14sp" />
    </ScrollView>
    
</LinearLayout>
```

### Step 7: Build and Run

1. Set your GitHub token: `export GITHUB_TOKEN="your_token_here"`
2. Sync Gradle dependencies
3. Connect Android device or start emulator
4. Click Run ▶️
5. Test the flow:
   - Click "Connect" → should connect to Mock Device
   - Click "Capture & Analyze" → should show a test image and AI response

---

## 🍎 iOS Implementation

### Step 2: Create New iOS Project

1. Open Xcode
2. File → New → Project
3. iOS → App
4. Product Name: `HelloSmartGlass`
5. Interface: SwiftUI
6. Language: Swift

### Step 3: Add Swift Package Dependencies

1. File → Add Package Dependencies
2. Enter: `https://github.com/facebook/meta-wearables-dat-ios`
3. Select latest version
4. Add to `HelloSmartGlass` target

### Step 4: Configure Info.plist

Add analytics opt-out:
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

### Step 5: Create Main View

**`ContentView.swift`:**
```swift
import SwiftUI
import MetaWearablesDAT

struct ContentView: View {
    @StateObject private var viewModel = SmartGlassViewModel()
    
    var body: some View {
        VStack(spacing: 20) {
            Text("Hello SmartGlass AI Agent")
                .font(.title)
                .bold()
            
            Text(viewModel.statusMessage)
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            HStack {
                Button(action: {
                    Task {
                        if viewModel.isConnected {
                            await viewModel.disconnect()
                        } else {
                            await viewModel.connect()
                        }
                    }
                }) {
                    Text(viewModel.isConnected ? "Disconnect" : "Connect")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                
                Button(action: {
                    Task {
                        await viewModel.captureAndAnalyze()
                    }
                }) {
                    Text("Capture & Analyze")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!viewModel.isConnected)
            }
            .padding(.horizontal)
            
            if let image = viewModel.capturedImage {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
                    .frame(maxHeight: 300)
                    .cornerRadius(8)
            } else {
                Image(systemName: "camera.fill")
                    .resizable()
                    .scaledToFit()
                    .frame(height: 100)
                    .foregroundColor(.gray)
            }
            
            VStack(alignment: .leading, spacing: 8) {
                Text("AI Response:")
                    .font(.headline)
                
                ScrollView {
                    Text(viewModel.aiResponse)
                        .font(.body)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.gray.opacity(0.2))
                        .cornerRadius(8)
                }
                .frame(height: 120)
            }
            .padding(.horizontal)
            
            Spacer()
        }
        .padding()
    }
}
```

### Step 6: Create View Model

**`SmartGlassViewModel.swift`:**
```swift
import Foundation
import UIKit
import MetaWearablesDAT

@MainActor
class SmartGlassViewModel: ObservableObject {
    @Published var statusMessage = "Ready to connect"
    @Published var isConnected = false
    @Published var capturedImage: UIImage?
    @Published var aiResponse = ""
    
    private var metaManager: MetaRayBanManager?
    private var sessionId: String?
    
    // Update this URL based on your setup
    private let backendURL = "http://YOUR_COMPUTER_IP:8000"
    
    func connect() async {
        statusMessage = "Connecting to glasses..."
        
        do {
            // Initialize Meta Ray-Ban Manager
            metaManager = MetaRayBanManager()
            
            // Connect to glasses (or Mock Device)
            try await metaManager?.connect(
                deviceId: "RAYBAN-MOCK-001",
                transport: "mock"  // Use "ble" for real glasses
            )
            
            // Create AI session
            statusMessage = "Creating AI session..."
            sessionId = try await createSession()
            
            isConnected = true
            statusMessage = "Connected! Ready to capture."
            
        } catch {
            statusMessage = "Connection failed: \(error.localizedDescription)"
            print("Connection error: \(error)")
        }
    }
    
    func disconnect() async {
        statusMessage = "Disconnecting..."
        
        // Close session if exists
        if let sid = sessionId {
            // Add close session call if needed
            sessionId = nil
        }
        
        metaManager = nil
        isConnected = false
        capturedImage = nil
        aiResponse = ""
        statusMessage = "Disconnected"
    }
    
    func captureAndAnalyze() async {
        guard isConnected, let manager = metaManager, let sid = sessionId else {
            statusMessage = "Not connected!"
            return
        }
        
        do {
            statusMessage = "Capturing photo..."
            
            // Capture photo from glasses
            let photo = try await manager.capturePhoto()
            capturedImage = photo
            
            statusMessage = "Analyzing with AI..."
            
            // Convert to JPEG data
            guard let jpegData = photo.jpegData(compressionQuality: 0.85) else {
                throw NSError(domain: "HelloSmartGlass", code: -1,
                            userInfo: [NSLocalizedDescriptionKey: "Failed to convert image"])
            }
            
            // Send to AI backend
            let response = try await sendToBackend(
                sessionId: sid,
                imageData: jpegData,
                query: "What do you see in this image?"
            )
            
            aiResponse = response
            statusMessage = "Analysis complete"
            
        } catch {
            statusMessage = "Analysis failed: \(error.localizedDescription)"
            print("Capture error: \(error)")
        }
    }
    
    // MARK: - Network Helpers
    
    private func createSession() async throws -> String {
        guard let url = URL(string: "\(backendURL)/ingest") else {
            throw NSError(domain: "HelloSmartGlass", code: -1)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["text": "Hello from HelloSmartGlass!"]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let sessionId = json["session_id"] as? String else {
            throw NSError(domain: "HelloSmartGlass", code: -1)
        }
        
        return sessionId
    }
    
    private func sendToBackend(sessionId: String, imageData: Data, query: String) async throws -> String {
        guard let url = URL(string: "\(backendURL)/answer") else {
            throw NSError(domain: "HelloSmartGlass", code: -1)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "session_id": sessionId,
            "text": query,
            "image_base64": imageData.base64EncodedString()
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let response = json["response"] as? String else {
            throw NSError(domain: "HelloSmartGlass", code: -1)
        }
        
        return response
    }
}

// Mock Meta Ray-Ban Manager for demonstration
class MetaRayBanManager {
    func connect(deviceId: String, transport: String) async throws {
        // Simulate connection delay
        try await Task.sleep(nanoseconds: 1_000_000_000)
    }
    
    func capturePhoto() async throws -> UIImage {
        // Return a test image
        // In real implementation, this would come from the glasses
        return UIImage(systemName: "photo.fill") ?? UIImage()
    }
}
```

### Step 7: Build and Run

1. Select simulator or connected device
2. Click Run ▶️ (Cmd+R)
3. Test the flow:
   - Tap "Connect" → should simulate connection
   - Tap "Capture & Analyze" → should show test image and AI response

---

## 🧪 Testing Your Implementation

### 1. Backend Health Check

Verify backend is responding:
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### 2. Manual API Test

Test the session and answer flow:
```bash
# Create session
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}'
# Response: {"session_id": "some-uuid"}

# Send query
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "some-uuid",
    "text": "What do you see?"
  }'
# Response: {"response": "AI response text", "actions": []}
```

### 3. Mock Device Testing

Both platforms support Mock Device for testing without hardware:
- **Android**: Set `transport = "mock"` in connect call
- **iOS**: Set `transport = "mock"` in connect call

Mock Device provides:
- Simulated camera frames
- Deterministic image data
- No bluetooth required

### 4. End-to-End Flow

Complete flow should be:
1. ✅ App starts successfully
2. ✅ Connect button works
3. ✅ Backend session created
4. ✅ Capture button enabled
5. ✅ Photo captured (mock or real)
6. ✅ Image sent to backend
7. ✅ AI response received
8. ✅ Response displayed in UI

---

## 🐛 Common Issues & Solutions

### Issue: "Cannot connect to backend"

**Symptoms**: Network errors, timeouts  
**Solutions**:
- Check backend is running: `curl http://backend-ip:8000/health`
- Verify firewall allows connections
- Use correct IP:
  - Emulator: `10.0.2.2`
  - Physical device: Your computer's LAN IP
- Check phone and computer on same network

### Issue: "GitHub authentication failed"

**Symptoms**: Cannot download Meta DAT dependencies  
**Solutions**:
```bash
# Create GitHub Personal Access Token
# Go to: https://github.com/settings/tokens
# Generate new token with 'read:packages' scope
export GITHUB_TOKEN="ghp_your_token_here"
```

### Issue: "Mock Device not working"

**Symptoms**: No frames from Mock Device  
**Solutions**:
- Verify `mwdat-mockdevice` dependency included
- Check initialization code
- Look for errors in Logcat (Android) or Console (iOS)

### Issue: "AI response is slow"

**Symptoms**: Long delays between capture and response  
**Solutions**:
- Backend processing takes time on first run (model loading)
- Subsequent requests should be faster
- Check backend logs for performance info
- Consider using `SDK_PYTHON_DUMMY_AGENT=1` for faster testing

---

## 🎉 Success! What's Next?

You now have a working AI-powered smart glasses app! Here's what to explore next:

### Immediate Next Steps
1. **Real Glasses**: Test with actual Ray-Ban Meta hardware
2. **Streaming**: Implement continuous frame streaming (not just single captures)
3. **Audio**: Add microphone input and speech-to-text
4. **Actions**: Implement navigation, notifications, etc.

### Enhancements
- **Voice Commands**: Add wake-word detection
- **Real-time Processing**: Stream every Nth frame continuously
- **Privacy Controls**: Add data retention settings
- **Offline Mode**: Cache responses for offline use
- **Custom Actions**: Build domain-specific features

### Learning Resources
- [Full Integration Guide](meta_dat_integration.md)
- [Android SDK Documentation](../ANDROID_SDK.md)
- [SmartGlass Agent API](API_REFERENCE.md)
- [Actions & Skills](actions_and_skills.md)
- [Privacy Guidelines](../PRIVACY.md)

### Sample Use Cases
- **Retail**: Price checking, product info
- **Travel**: Sign translation, navigation
- **Healthcare**: Medication reminders, vitals
- **Accessibility**: Scene descriptions, text reading

---

## 📚 Additional Resources

- [Meta Wearables Developer Portal](https://developers.meta.com/wearables)
- [SmartGlass-AI-Agent GitHub](https://github.com/farmountain/SmartGlass-AI-Agent)
- [Meta DAT Android SDK](https://github.com/facebook/meta-wearables-dat-android)
- [Meta DAT iOS SDK](https://github.com/facebook/meta-wearables-dat-ios)

---

**Questions or Issues?**
- Open an issue on GitHub
- Check existing documentation
- Review sample apps in SDK repositories

**Built with ❤️ for AI-powered wearables**

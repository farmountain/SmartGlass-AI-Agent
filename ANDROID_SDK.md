# Android SDK Usage Guide

This guide covers how to consume the SmartGlass Android SDK, configure the edge runtime connection, and invoke the suspend APIs with coroutines.

## Setup and Requirements
- **Android Studio / Gradle**: Android Gradle Plugin with Kotlin support.
- **Android API level**: `minSdk 24`, `targetSdk 34`, `compileSdk 34` (matches `sdk-android/build.gradle.kts`).
- **Runtime dependencies**: The library bundles OkHttp, Moshi, WorkManager, coroutines, and other transitive dependencies; add the SDK module to pull them in automatically.
- **Permissions**: Network access to the edge runtime (e.g., add `android.permission.INTERNET` to your app manifest).

## Adding the dependency
1. Ensure the module is included in `settings.gradle.kts` (already present for this repo):
   ```kotlin
   include(":sdk-android")
   ```
2. Add the module to your app module's dependencies:
   ```kotlin
   dependencies {
       implementation(project(":sdk-android"))
   }
   ```

## Client configuration
- The `SmartGlassEdgeClient` accepts an optional `baseUrl` for the edge runtime and defaults to `http://127.0.0.1:8765`.
- Trim trailing slashes are handled automatically; provide the reachable host/port of your edge deployment, for example:
  ```kotlin
  val client = SmartGlassEdgeClient(baseUrl = "http://192.168.1.50:8765")
  ```

> [!NOTE]
> The edge runtime client above targets the low-latency edge service. The HTTP client described below is separate and talks to
> the Python server exposed in `sdk_python.server`; configure only one client type per use case to avoid mixing endpoints.

## Using the Python HTTP server with `SmartGlassClient`
1. Start the lightweight HTTP server from the repo root (enable the dummy agent to avoid heavyweight model downloads):
   ```bash
   export SDK_PYTHON_DUMMY_AGENT=1
   python -m sdk_python.server --host 0.0.0.0 --port 8000
   ```
   - For emulators, use `http://10.0.2.2:8000` as the reachable host from Android.
   - For physical devices on the same network, substitute your machine's LAN IP, for example `http://192.168.1.50:8000`.

2. Configure the Android client with the server's base URL:
   ```kotlin
   val client = SmartGlassClient(baseUrl = "http://10.0.2.2:8000")
   ```

3. Drive the request flow with `startSession` followed by `answer` calls:
   ```kotlin
   viewModelScope.launch {
       // Create a new session with optional initial text or image path
       val sessionId = client.startSession(text = "Hello from Android")

       // Send follow-up prompts (and optional image paths) against the same session
       val response = client.answer(sessionId, text = "What's next?")

       // Inspect the response and actions as needed
       handleResponse(response)
   }
   ```
   The `/ingest` call creates and returns a `sessionId`; subsequent `/answer` calls reuse that identifier to maintain context.

## Coroutine and threading guidance
- All public APIs on `SmartGlassEdgeClient` are `suspend` functions; call them from a coroutine scope (e.g., `lifecycleScope`, `viewModelScope`).
- Network work is dispatched onto `Dispatchers.IO` internally, but you should avoid blocking the main thread when chaining calls.
- Handle cancellation normally; the client propagates coroutine cancellations while wrapping other failures as `IOException`.

## Sample usage
```kotlin
class DemoViewModel : ViewModel() {
    private val client = SmartGlassEdgeClient(baseUrl = "http://127.0.0.1:8765")

    fun runDemo(prompt: String) {
        viewModelScope.launch {
            // 1) Create a session
            val sessionId = client.createSession()

            // 2) Send audio bytes (16 kHz mono in this example)
            val audio = ByteArray(3200) { (it % 50).toByte() }
            val audioResp = client.sendAudioChunk(sessionId, audio, sampleRate = 16000)

            // 3) Send an image frame (JPEG bytes)
            val frameResp = client.sendFrame(sessionId, jpegBytes = obtainJpeg(), width = 640, height = 480)

            // 4) Run a multimodal query (text, audio, or image)
            val queryResp = client.runQuery(sessionId, textQuery = prompt)

            // 5) Close the session when finished
            val closeResp = client.closeSession(sessionId)

            // Handle responses (transcript/response/status/error fields)
            handleEdgeResponse(audioResp)
            handleEdgeResponse(frameResp)
            handleEdgeResponse(queryResp)
            handleEdgeResponse(closeResp)
        }
    }
}
```

## Runnable example
A full runnable example is available in the [`sample/`](sample/) Android app, which wires the client into an Activity lifecycle and demonstrates the end-to-end workflow.

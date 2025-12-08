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
- Use **`SmartGlassEdgeClient`** when talking to the **edge runtime**. It issues `createSession` / `runQuery` requests to the
  runtime's REST surface (see sample below) and expects endpoints rooted at `/sessions` on port `8765` by default.
- Use **`SmartGlassClient`** when talking to the **Python HTTP server** in `sdk_python.server`. It issues `startSession`
  (`POST /ingest`) followed by `answer` (`POST /answer`) calls and defaults to port `8000`.
- Only configure one of these clients in a given flow; they target different servers and are not interchangeable.
- Both clients trim trailing slashes from the `baseUrl` you pass.

Edge runtime configuration example:

```kotlin
val edgeClient = SmartGlassEdgeClient(baseUrl = "http://192.168.1.50:8765")
```

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

3. **New Streaming API (Recommended)**: Drive the request flow by accumulating audio and frames, then finalizing the turn:
   ```kotlin
   viewModelScope.launch {
       // Create a new session
       val session = client.startSession()

       // Send audio chunks as they become available
       client.sendAudioChunk(session, audioData, System.currentTimeMillis())

       // Send visual frames
       client.sendFrame(session, jpegBytes, System.currentTimeMillis())

       // Finalize the turn and get the agent's response
       val result = client.finalizeTurn(session)
       println("Agent: ${result.response}")

       // Execute any actions returned by the agent
       ActionExecutor.execute(result.actions, context)
   }
   ```

4. **Legacy API (Deprecated)**: Simple request/response pattern:
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
   `startSession` issues `POST /ingest` to receive a `session_id`; each `answer` call issues `POST /answer` with that identifier
   to maintain conversation context.

## Action execution
LLM responses can include actions (for example `NAVIGATE` or `SHOW_TEXT`) that you can trigger on-device. The SDK ships an
`ActionExecutor` helper that processes a list of actions and invokes the right handler for each entry. This helper is part of the
stable v1.0 Android surface:

```kotlin
ActionExecutor.execute(response.actions, context)
```

- **`NAVIGATE`**: Builds a `geo:0,0?q=<destination>` URI from the `destination` payload key and attempts to open it in Google
  Maps, falling back to a generic `ACTION_VIEW` intent if Maps is unavailable.
- **`SHOW_TEXT`**: Reads the `message` payload key, then shows it as both a Toast and a notification for quick user feedback.

To support additional action types or payload shapes, add new `when` branches inside `ActionExecutor` (or wrap the helper with
your own dispatcher) before calling `ActionExecutor.execute`.

## On-device SNN Inference
- **Model placement**: Copy your exported `snn_student.onnx` into `sdk-android/src/main/assets/models/snn_student.onnx` so the
  Gradle build packages it inside the SDK AAR. If your export uses a different filename or subdirectory, override the
  `modelAssetName` argument to `SnnLanguageEngine` (default: `"models/snn_student.onnx"`).
- **Engine initialization**: Create a `SnnLanguageEngine` with an Android `Context`; the constructor and `generateReply` API are
  part of the stable v1.0 surface.
- **Tokenizer/shape caveats**: The current tokenizer splits on whitespace, hashes tokens into a fixed 32K ID space (reserving `0`
  for unknown), and pads/truncates tensors to the requested `maxTokens`. This is a placeholder implementation—the tokenizer and
  ONNX input/output shapes will be aligned with `metadata.json` from the SNN export pipeline in upcoming updates while keeping
  the public API consistent.

Prompt-to-reply usage:

```kotlin
val engine = SnnLanguageEngine(context)
val reply = engine.generateReply("Hello SNN world!", maxTokens = 32)
println("Model replied: $reply")
```

Use this engine when you want fully local inference without the edge or Python servers. Replace the placeholder tokenizer once the production vocabulary and tensor shapes from `metadata.json` are available.

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

## Meta Ray-Ban Integration
The sample app still includes a stubbed `MetaRayBanManager` to keep the UI runnable without the Android SDK, but the Python provider now integrates directly with the `metarayban` package whenever it is installed. That means you can exercise live camera, microphone, audio, overlay, and haptics calls from Python while the Android UI remains mock-friendly.

- **Purpose and behavior**: The manager exposes a `connect` flow, capture trigger, and a streaming loop that emits placeholder audio data. The stub logs progress and invokes callbacks immediately to simulate success while running a coroutine that feeds dummy PCM bytes to listeners.
- **Mapping `device_id` and transport**: The Python provider passes `device_id` along with the preferred transport (BLE vs. Wi-Fi) into the SDK. In the stub, these inputs are threaded into `connect` and logged to illustrate how they would select the underlying transport in the real SDK (e.g., choosing BLE pairing vs. Wi-Fi Direct). Replace the logging/placeholder branch with SDK-specific connect calls keyed by the provided `device_id` and transport.
- **Capture and streaming**: Invoking `capture` on the stub toggles a mock recording session and reuses the coroutine loop to stream fabricated audio chunks. Insert SDK microphone start/stop calls here when wiring actual hardware, and forward microphone frames to the same callbacks that currently receive dummy data.
- **UI touchpoints**: The sample app's **Connect** button invokes `connect` on the manager, while the **Capture** button toggles the stubbed capture/stream path. Swap these callbacks to call the real SDK when available so UI behavior remains unchanged.
- **TODO handoff points**: Replace log lines with SDK APIs for discovery/connection, insert microphone start/stop in the capture handler, and route incoming audio/video frames through the same listener interfaces already consumed by the sample UI and Python provider. The provider will continue to fall back to deterministic mocks if the `metarayban` package is not present or a runtime SDK call fails.

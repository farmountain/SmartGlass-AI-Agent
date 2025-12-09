# LocalSnnEngine - On-Device SNN Inference

## Overview

The `LocalSnnEngine` class provides on-device SNN (Spiking Neural Network) inference using TorchScript or ONNX models. It runs completely offline without any network calls, making it ideal for privacy-sensitive applications on smart glasses.

## Package

```kotlin
com.smartglass.runtime.llm
```

## Architecture

The implementation uses an abstraction layer (`ModelBackend` interface) to support multiple inference engines:

1. **PyTorch Mobile** (preferred): Uses `org.pytorch.Module` for TorchScript models
2. **ONNX Runtime** (fallback): Uses `ai.onnxruntime` for ONNX models
3. **Mock Backend**: Simple fallback for testing when no real backend is available

The engine automatically detects which backend is available at runtime using reflection, allowing the library to compile without hard dependencies on PyTorch or ONNX.

## Usage

### Basic Example

```kotlin
import android.content.Context
import com.smartglass.runtime.llm.LocalSnnEngine
import com.smartglass.runtime.llm.LocalTokenizer
import kotlinx.coroutines.runBlocking

fun createEngine(context: Context): LocalSnnEngine {
    // Create tokenizer (will load metadata from assets if available)
    val tokenizer = LocalTokenizer(context, "snn_student_ts.pt")
    
    // Create engine
    val engine = LocalSnnEngine(
        context = context,
        modelAssetPath = "snn_student_ts.pt",  // Model in assets folder
        tokenizer = tokenizer
    )
    
    return engine
}

// Generate text
runBlocking {
    val engine = createEngine(context)
    val response = engine.generate("What is the weather like?")
    println(response)
}
```

### With Visual Context

```kotlin
suspend fun generateWithVision(
    engine: LocalSnnEngine,
    prompt: String,
    visualInfo: String
): String {
    return engine.generate(
        prompt = prompt,
        visualContext = visualInfo,
        maxTokens = 128
    )
}

// Example usage
val response = generateWithVision(
    engine = engine,
    prompt = "Describe what you see",
    visualInfo = "A red stop sign at an intersection"
)
```

### Custom Token Limits

```kotlin
// Generate short responses
val shortResponse = engine.generate(
    prompt = "Yes or no?",
    maxTokens = 10
)

// Generate longer responses
val longResponse = engine.generate(
    prompt = "Explain quantum computing",
    maxTokens = 256
)
```

## LocalTokenizer

The `LocalTokenizer` class handles text encoding and decoding:

```kotlin
val tokenizer = LocalTokenizer(context, modelAssetPath = "model.pt")

// Encode text to token IDs
val tokens: LongArray = tokenizer.encode("Hello world", maxLength = 64)

// Decode token IDs back to text
val text: String = tokenizer.decode(tokens)

// Pad or truncate tokens
val padded: LongArray = tokenizer.pad(tokens, length = 128)

// Access metadata
val maxLen = tokenizer.maxSequenceLength
val padId = tokenizer.padTokenId
```

### Tokenizer Metadata

The tokenizer can load metadata from JSON files in assets. Place a `metadata.json` file alongside your model:

```
assets/
  ├── snn_student_ts.pt
  └── snn_student_ts.metadata.json
```

Example metadata format:

```json
{
  "tokenizer": {
    "vocab": ["<pad>", "<unk>", "hello", "world", "..."],
    "lowercase": true,
    "pad_token_id": 0,
    "unk_token_id": 1,
    "max_length": 128
  }
}
```

If metadata is not found, the tokenizer falls back to hash-based encoding.

## Error Handling

The engine handles errors gracefully:

```kotlin
val response = engine.generate("Hello")
// On error, returns: "I'm having trouble thinking right now."
```

All exceptions are caught, logged, and result in the fallback message. This ensures the UI never crashes due to inference failures.

## Threading

All heavy computation runs on `Dispatchers.Default` automatically. The `generate()` function is a suspend function, so call it from a coroutine:

```kotlin
// In a ViewModel
viewModelScope.launch {
    val response = engine.generate("Question?")
    updateUI(response)
}

// In an Activity/Fragment
lifecycleScope.launch {
    val response = engine.generate("Question?")
    textView.text = response
}
```

## Dependencies

### Required (already in SDK)
- `kotlinx-coroutines-android`
- `org.json:json`

### Optional (compileOnly)
- `org.pytorch:pytorch_android_lite:1.13.1` - For TorchScript models
- `com.microsoft.onnxruntime:onnxruntime-android:1.18.0` - For ONNX models

To include PyTorch Mobile in your app, add to your app's `build.gradle`:

```gradle
dependencies {
    implementation("org.pytorch:pytorch_android_lite:1.13.1")
    implementation("org.pytorch:pytorch_android_torchvision_lite:1.13.1")
}
```

## Model Formats

### TorchScript (.pt)
```python
# Export PyTorch model to TorchScript
model = YourModel()
scripted = torch.jit.script(model)
scripted.save("snn_student_ts.pt")
```

### ONNX (.onnx)
```python
# Export PyTorch model to ONNX
import torch.onnx
dummy_input = torch.randn(1, 128, dtype=torch.long)
torch.onnx.export(model, dummy_input, "snn_student.onnx")
```

Place the exported model in `app/src/main/assets/` directory.

## Testing

Unit tests are provided for both classes:

```bash
./gradlew :sdk-android:test --tests com.smartglass.runtime.llm.LocalTokenizerTest
./gradlew :sdk-android:test --tests com.smartglass.runtime.llm.LocalSnnEngineTest
```

The tests use mock contexts and don't require actual model files.

## Performance Considerations

1. **Model Size**: Keep models under 50MB for reasonable app size
2. **Inference Time**: Expect 50-500ms depending on model complexity and device
3. **Memory**: SNN models are memory-efficient compared to transformers
4. **Battery**: On-device inference uses more battery than cloud APIs

## Privacy Benefits

- **No Network Calls**: All processing happens on-device
- **No Data Leaks**: User prompts never leave the device
- **Offline Operation**: Works without internet connection
- **Low Latency**: No network round-trip delays

## Limitations

1. Mock backend returns simplified responses when no real backend is available
2. Hash-based tokenization (without metadata) produces non-decodable tokens
3. Model must be compatible with PyTorch Mobile or ONNX Runtime
4. No streaming generation (returns complete response)

## Future Enhancements

- [ ] Streaming token generation
- [ ] Beam search decoding
- [ ] Temperature and top-k sampling
- [ ] Model quantization support
- [ ] Batch inference
- [ ] GPU acceleration (when available)

## Related Classes

- `rayskillkit.core.SnnLanguageEngine` - Alternative implementation using ONNX only
- `com.smartglass.sdk.SmartGlassClient` - Network-based inference client
- `com.smartglass.sdk.SmartGlassEdgeClient` - Edge server client

## See Also

- [ANDROID_SDK.md](../../ANDROID_SDK.md) - Android SDK documentation
- [Training Guide](../../docs/) - Model training documentation

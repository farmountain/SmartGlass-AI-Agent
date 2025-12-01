# API Reference - SmartGlass AI Agent

Complete API documentation for all components.

## Table of Contents
- [SmartGlassAgent](#smartglassagent)
- [WhisperAudioProcessor](#whisperaudioprocessor)
- [CLIPVisionProcessor](#clipvisionprocessor)

---

## SmartGlassAgent

Main agent class integrating all components. The public methods are considered
stable as of v1.0 and are designed around a pluggable language backend and
provider resolver to avoid breaking downstream applications.

### Initialization

```python
from src.llm_snn_backend import SNNLLMBackend
from src.smartglass_agent import SmartGlassAgent

# PROVIDER env var controls device/provider selection when `provider` is omitted
# (default: "mock"). Pass a provider string or instance to override.
agent = SmartGlassAgent(
    whisper_model: str = "base",
    clip_model: str = "openai/clip-vit-base-patch32",
    llm_backend: Optional[BaseLLMBackend] = None,
    device: Optional[str] = None,
    provider: Optional[Union[str, BaseProvider]] = None,
)

# Example: SNN backend + provider resolved from PROVIDER
agent = SmartGlassAgent(
    llm_backend=SNNLLMBackend(model_path="artifacts/snn_student/student.pt"),
)
```

**Parameters:**
- `whisper_model` (str): Whisper model size - 'tiny', 'base', 'small', 'medium', 'large'
- `clip_model` (str): CLIP model name from HuggingFace
- `llm_backend` (BaseLLMBackend, optional): Language backend implementation. Defaults to the ANN/GPT-2 compatibility path when
  omitted; inject `SNNLLMBackend` for on-device generation or any custom backend that implements
  `BaseLLMBackend.generate`.
- `device` (str, optional): Device hint used by the processors/backends - 'cuda', 'cpu', or None for auto-detect
- `provider` (str or BaseProvider, optional): Provider name or instance. When omitted, the `PROVIDER` env var is read (default:
  `"mock"`) and resolved via `drivers.providers.get_provider`.

### Methods

#### process_audio_command()

Process audio command from user.

```python
text = agent.process_audio_command(
    audio_input: Union[str, np.ndarray],
    language: Optional[str] = None
) -> str
```

**Parameters:**
- `audio_input`: Audio file path or audio array (16kHz)
- `language`: Language code (e.g., 'en', 'es') or None for auto-detect

**Returns:** Transcribed text

**Example:**
```python
text = agent.process_audio_command("command.wav")
print(f"User said: {text}")
```

---

#### analyze_scene()

Analyze scene from smart glass camera.

```python
result = agent.analyze_scene(
    image: Union[str, Image.Image, np.ndarray],
    custom_queries: Optional[List[str]] = None
) -> Dict
```

**Parameters:**
- `image`: Image file path, PIL Image, or numpy array
- `custom_queries`: Custom queries for specific analysis

**Returns:** Dictionary with scene analysis results

**Example:**
```python
# Default scene analysis
scene = agent.analyze_scene("photo.jpg")
print(scene['description'])

# Custom queries
result = agent.analyze_scene(
    "photo.jpg",
    custom_queries=['indoor', 'outdoor', 'night scene']
)
print(f"Best match: {result['best_match']}")
```

---

#### identify_object()

Identify object in view.

```python
object_name = agent.identify_object(
    image: Union[str, Image.Image, np.ndarray],
    possible_objects: List[str]
) -> str
```

**Parameters:**
- `image`: Image file path, PIL Image, or numpy array
- `possible_objects`: List of possible object names

**Returns:** Identified object name

**Example:**
```python
items = ['keys', 'phone', 'wallet', 'book']
found = agent.identify_object("view.jpg", items)
print(f"I see your {found}")
```

---

#### generate_response()

Generate natural language response to user query.

```python
response = agent.generate_response(
    user_query: str,
    visual_context: Optional[str] = None
) -> str
```

**Parameters:**
- `user_query`: User's question or command
- `visual_context`: Description of what the agent sees

**Returns:** Generated response text

**Example:**
```python
response = agent.generate_response(
    "What should I do?",
    visual_context="I see a red car in front of a building"
)
print(response)
```

---

#### process_multimodal_query()

Process multimodal query combining audio, vision, and text.

```python
result = agent.process_multimodal_query(
    audio_input: Optional[Union[str, np.ndarray]] = None,
    image_input: Optional[Union[str, Image.Image, np.ndarray]] = None,
    text_query: Optional[str] = None,
    language: Optional[str] = None,
    provider: Optional[Union[str, BaseProvider]] = None,
) -> Dict[str, Any]
```

**Parameters:**
- `audio_input`: Audio command (file path or array)
- `image_input`: Image from smart glasses
- `text_query`: Direct text query (if no audio)
- `language`: Language for audio transcription
- `provider`: Optional override for the active provider (otherwise `SmartGlassAgent` uses the resolver configured at init time).

**Returns:** Dictionary with:
- `response`: Generated assistant message (string)
- `actions`: Optional list of structured action dictionaries
- `raw`: Optional nested payload preserving query, context, and metadata

**Example (multimodal actions with SNN backend):**
```python
from src.llm_snn_backend import SNNLLMBackend
from src.smartglass_agent import SmartGlassAgent

# PROVIDER selects the device bridge; defaults to "mock" if unset
agent = SmartGlassAgent(llm_backend=SNNLLMBackend())

result = agent.process_multimodal_query(
    text_query="What should I do next?",  # optional audio_input instead
    image_input="scene.jpg",
)

print("Response:", result.get("response"))
print("Actions:")
for action in result.get("actions", []):
    print(" -", action.get("type"), action.get("payload"))

print("Raw payload keys:", sorted(result.get("raw", {}).keys()))
```

---

#### help_identify()

Help user identify what they're looking at.

```python
response = agent.help_identify(
    image: Union[str, Image.Image, np.ndarray],
    audio_query: Optional[Union[str, np.ndarray]] = None,
    text_query: Optional[str] = None
) -> str
```

**Parameters:**
- `image`: Image from smart glasses
- `audio_query`: Audio question (optional)
- `text_query`: Text question (optional)

**Returns:** Helpful identification response

**Example:**
```python
response = agent.help_identify(
    "object.jpg",
    text_query="What is this?"
)
print(response)
```

---

#### Other Methods

```python
# Clear conversation history
agent.clear_conversation_history()

# Get conversation history
history = agent.get_conversation_history() -> List[str]

# Get agent information
info = agent.get_agent_info() -> Dict
```

---

## WhisperAudioProcessor

Audio processing using OpenAI Whisper.

### Initialization

```python
from src.whisper_processor import WhisperAudioProcessor

processor = WhisperAudioProcessor(
    model_size: str = "base",
    device: Optional[str] = None
)
```

**Parameters:**
- `model_size`: 'tiny', 'base', 'small', 'medium', 'large'
- `device`: 'cuda', 'cpu', or None for auto-detect

### Methods

#### transcribe_audio()

Transcribe audio file or array to text.

```python
result = processor.transcribe_audio(
    audio_path: Optional[str] = None,
    audio_array: Optional[np.ndarray] = None,
    language: Optional[str] = None,
    task: str = "transcribe"
) -> dict
```

**Parameters:**
- `audio_path`: Path to audio file
- `audio_array`: NumPy array containing audio data (16kHz)
- `language`: Language code or None for auto-detect
- `task`: 'transcribe' or 'translate' (translate to English)

**Returns:** Dictionary with 'text' and transcription details

**Example:**
```python
# From file
result = processor.transcribe_audio(audio_path="audio.wav")
print(result['text'])

# From array
import soundfile as sf
audio, sr = sf.read("audio.wav")
result = processor.transcribe_audio(audio_array=audio, language='en')
print(result['text'])
```

---

#### transcribe_realtime()

Transcribe audio chunk for real-time processing.

```python
text = processor.transcribe_realtime(
    audio_chunk: np.ndarray
) -> str
```

**Parameters:**
- `audio_chunk`: Audio data chunk (16kHz sample rate)

**Returns:** Transcribed text

---

## CLIPVisionProcessor

Vision processing using CLIP.

### Initialization

```python
from src.clip_vision import CLIPVisionProcessor

vision = CLIPVisionProcessor(
    model_name: str = "openai/clip-vit-base-patch32",
    device: Optional[str] = None
)
```

### Methods

#### understand_image()

Understand image content by matching with text queries.

```python
result = vision.understand_image(
    image: Union[str, Image.Image, np.ndarray],
    text_queries: List[str],
    return_scores: bool = True
) -> dict
```

**Parameters:**
- `image`: Image file path, PIL Image, or numpy array
- `text_queries`: List of text descriptions to match
- `return_scores`: Whether to return similarity scores

**Returns:** Dictionary with 'best_match', 'confidence', and optionally 'all_scores'

**Example:**
```python
queries = ['indoor scene', 'outdoor scene', 'night scene']
result = vision.understand_image("photo.jpg", queries)
print(f"Best match: {result['best_match']}")
print(f"Confidence: {result['confidence']:.2%}")
```

---

#### classify_image()

Zero-shot image classification.

```python
category = vision.classify_image(
    image: Union[str, Image.Image, np.ndarray],
    categories: List[str]
) -> str
```

**Parameters:**
- `image`: Image file path, PIL Image, or numpy array
- `categories`: List of possible categories

**Returns:** Best matching category

**Example:**
```python
categories = ['cat', 'dog', 'bird', 'car']
result = vision.classify_image("photo.jpg", categories)
print(f"Image contains: {result}")
```

---

#### get_image_features()

Extract image features (embeddings).

```python
features = vision.get_image_features(
    image: Union[str, Image.Image, np.ndarray]
) -> np.ndarray
```

**Returns:** Image feature vector (numpy array)

---

#### describe_scene()

Generate a description of what's in the scene.

```python
description = vision.describe_scene(
    image: Union[str, Image.Image, np.ndarray]
) -> str
```

**Returns:** Scene description

**Example:**
```python
description = vision.describe_scene("scene.jpg")
print(description)
```

---

## Language Backends (pluggable)

Language generation is provided by implementations of `BaseLLMBackend`. The
SmartGlassAgent API remains stable as of v1.0, allowing backends to be swapped
without changing application code.

### SNNLLMBackend (on-device friendly)

```python
from src.llm_snn_backend import SNNLLMBackend

backend = SNNLLMBackend(
    model_path: str = "artifacts/snn_student/student.pt",  # optional stub fallback
    device: Optional[str] = None,  # e.g., "cpu" or "cuda" hint
)
```

**Key behaviors:**
- Uses the saved spiking student checkpoint when available and falls back to a stub for portability.
- Respects the provided `device` hint but otherwise auto-selects based on environment.
- Implements `generate(prompt: str, max_tokens: int = 64, **kwargs) -> str`, so it can be dropped into `SmartGlassAgent` via
  the `llm_backend` parameter.

### Swapping backends

```python
from src.llm_backend import LLMBackend  # ANN baseline
from src.llm_snn_backend import SNNLLMBackend
from src.smartglass_agent import SmartGlassAgent

# Use PROVIDER to steer device/provider resolution (default: "mock")
agent = SmartGlassAgent(
    llm_backend=SNNLLMBackend(),  # or LLMBackend("student/llama-3.2-3b")
    provider=None,  # omitting uses drivers.providers.get_provider(os.getenv("PROVIDER", "mock"))
)
```

Backends can implement custom kwargs (e.g., temperature or max_tokens) while still exposing the same `generate` interface. This makes it straightforward to migrate between on-device, cloud-hosted, or experimental language models without rewriting the agent or driver wiring. Consult each backend class for supported keyword arguments.

## Error Handling

All methods may raise the following exceptions:

- `ValueError`: Invalid parameters
- `FileNotFoundError`: Missing audio/image files
- `RuntimeError`: Model loading or inference errors
- `MemoryError`: Insufficient memory

**Example:**
```python
try:
    result = agent.process_multimodal_query(
        text_query="Hello",
        image_input="image.jpg"
    )
except FileNotFoundError:
    print("Image file not found")
except ValueError as e:
    print(f"Invalid input: {e}")
```

---

## Best Practices

1. **Memory Management**: Close unused models when switching configurations
2. **Error Handling**: Always wrap API calls in try-except blocks
3. **Performance**: Use appropriate model sizes for your hardware
4. **Context**: Provide visual context for better text generation
5. **Language**: Specify language when known for faster transcription

---

For more examples, see the `examples/` directory and the Colab notebooks.

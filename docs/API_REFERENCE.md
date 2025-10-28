# API Reference - SmartGlass AI Agent

Complete API documentation for all components.

## Table of Contents
- [SmartGlassAgent](#smartglassagent)
- [WhisperAudioProcessor](#whisperaudioprocessor)
- [CLIPVisionProcessor](#clipvisionprocessor)
- [GPT2TextGenerator](#gpt2textgenerator)

---

## SmartGlassAgent

Main agent class integrating all components.

### Initialization

```python
from src.smartglass_agent import SmartGlassAgent

agent = SmartGlassAgent(
    whisper_model: str = "base",
    clip_model: str = "openai/clip-vit-base-patch32",
    gpt2_model: str = "gpt2",
    device: Optional[str] = None
)
```

**Parameters:**
- `whisper_model` (str): Whisper model size - 'tiny', 'base', 'small', 'medium', 'large'
- `clip_model` (str): CLIP model name from HuggingFace
- `gpt2_model` (str): GPT-2 model name - 'gpt2', 'gpt2-medium', 'gpt2-large', 'gpt2-xl'
- `device` (str, optional): Device to run models - 'cuda', 'cpu', or None for auto-detect

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
    language: Optional[str] = None
) -> Dict[str, str]
```

**Parameters:**
- `audio_input`: Audio command (file path or array)
- `image_input`: Image from smart glasses
- `text_query`: Direct text query (if no audio)
- `language`: Language for audio transcription

**Returns:** Dictionary with 'query', 'visual_context', and 'response'

**Example:**
```python
result = agent.process_multimodal_query(
    audio_input="command.wav",
    image_input="scene.jpg"
)
print(f"Query: {result['query']}")
print(f"Context: {result['visual_context']}")
print(f"Response: {result['response']}")
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

## GPT2TextGenerator

Text generation using GPT-2.

### Initialization

```python
from src.gpt2_generator import GPT2TextGenerator

generator = GPT2TextGenerator(
    model_name: str = "gpt2",
    device: Optional[str] = None
)
```

### Methods

#### generate_response()

Generate text response based on prompt.

```python
responses = generator.generate_response(
    prompt: str,
    max_length: int = 100,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 50,
    num_return_sequences: int = 1,
    no_repeat_ngram_size: int = 2
) -> List[str]
```

**Parameters:**
- `prompt`: Input text prompt
- `max_length`: Maximum length of generated text
- `temperature`: Sampling temperature (higher = more random)
- `top_p`: Nucleus sampling parameter
- `top_k`: Top-k sampling parameter
- `num_return_sequences`: Number of responses to generate
- `no_repeat_ngram_size`: Prevent repetition of n-grams

**Returns:** List of generated text responses

**Example:**
```python
responses = generator.generate_response(
    "What is artificial intelligence?",
    max_length=50,
    temperature=0.7
)
print(responses[0])
```

---

#### generate_smart_response()

Generate a smart, context-aware response.

```python
response = generator.generate_smart_response(
    user_query: str,
    context: Optional[str] = None,
    response_type: str = "helpful"
) -> str
```

**Parameters:**
- `user_query`: User's question or command
- `context`: Additional context (e.g., "I see a red car")
- `response_type`: 'helpful', 'informative', or 'conversational'

**Returns:** Generated response text

**Example:**
```python
response = generator.generate_smart_response(
    "What should I do?",
    context="You are at a crosswalk",
    response_type="helpful"
)
print(response)
```

---

#### summarize_text()

Generate a summary of the given text.

```python
summary = generator.summarize_text(
    text: str,
    max_length: int = 50
) -> str
```

**Example:**
```python
long_text = "Very long text here..."
summary = generator.summarize_text(long_text, max_length=30)
print(summary)
```

---

#### continue_conversation()

Continue a conversation based on history.

```python
response = generator.continue_conversation(
    conversation_history: List[str],
    max_history: int = 3
) -> str
```

**Parameters:**
- `conversation_history`: List of previous exchanges
- `max_history`: Maximum number of history items to use

**Returns:** Generated response

---

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

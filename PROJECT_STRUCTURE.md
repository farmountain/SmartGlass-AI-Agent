# SmartGlass AI Agent - Project Structure

## 📁 Directory Structure

```
SmartGlass-AI-Agent/
├── src/                          # Core source code (agent orchestration, backends, policies)
│   ├── smartglass_agent.py      # Stable v1.0 SmartGlassAgent entry point
│   ├── llm_backend_base.py      # Backend protocol for SNN/ANN/cloud text generators
│   ├── llm_snn_backend.py       # On-device spiking student backend (SNN)
│   ├── llm_backend.py           # ANN/text backends, routing, and tokenizer helpers
│   ├── whisper_processor.py     # Whisper audio processing
│   ├── clip_vision.py           # CLIP / DeepSeek-Vision processing
│   ├── agent/                   # Policies, fusion, and action formatting
│   ├── edge_runtime/            # Edge runtime toggles and privacy protections
│   └── skills/                  # Action execution shims and RaySkillKit bindings
│   ├── world_model.py            # World state representation (planned/partial)
│   ├── context_store.py          # Memory store interface (planned/partial)
│   └── planner.py                # Task planning interface (planned/partial)
│
├── drivers/                      # Device drivers and provider abstractions
│   ├── providers/               # Provider resolver (mock, meta, vuzix, xreal, visionos, openxr)
│   └── ...
│
├── rayskillkit/                  # Skill/action execution adapters and payload schemas
├── scripts/                      # Training, evaluation, and tooling scripts (e.g., SNN distillation)
├── examples/                     # Usage examples and CLI demos
├── tests/                        # Unit and integration tests
├── sdk-android/                  # Native Android client and bridge code
├── sdk_python/                   # Python SDK distribution (pip-installable layout)
├── colab_notebooks/              # Weekly notebooks and interactive workshops
├── docs/                         # Documentation, reports, and integration guides
├── requirements.txt              # Python dependencies
├── setup.py                      # Package installation setup
├── README.md                     # Main documentation
├── QUICKSTART.md                 # Quick start guide
├── CONTRIBUTING.md               # Contributing guidelines
├── LICENSE                       # MIT License with NOTICE
└── NOTICE.md                     # Third-party notices for the v1.0 stable release
```

## 🔧 Core Modules

### 1. smartglass_agent.py
- **Purpose**: Main integration layer for multimodal queries
- **Features**:
  - Coordinates speech, vision, and language backends
  - Returns structured responses with `actions` aligned to RaySkillKit
  - Delegates provider selection to `drivers.providers.get_provider`
- **Use Case**: Stable entry point for apps and SDKs (Python/Android)

### 2. llm_backend_base.py & llm_snn_backend.py
- **Purpose**: Pluggable language generation backends
- **Backends**:
  - **SNNLLMBackend**: On-device spiking student for low-power glasses
  - **ANN/Cloud adapters**: GPT-style or hosted models via `llm_backend.py`
- **Features**:
  - Shared interface for `generate`/`chat` semantics
  - Tokenizer/model fallbacks to keep demos runnable without checkpoints
- **Use Case**: Swap between on-device SNN, local ANN, or remote providers without changing agent code

### 3. whisper_processor.py
- **Purpose**: Speech-to-text transcription
- **Model**: OpenAI Whisper (all sizes)
- **Features**:
  - Streaming and chunked audio support
  - Multilingual, with device-friendly configuration for edge runtime
- **Use Case**: Convert voice commands to text across providers

### 4. clip_vision.py
- **Purpose**: Visual understanding
- **Models**: OpenAI CLIP and DeepSeek-Vision
- **Features**:
  - Zero-shot image classification and captioning hooks
  - Scene understanding for action planning
- **Use Case**: Understand what the smart glasses see and feed context to the LLM backend

### 5. drivers.providers
- **Purpose**: Abstract device I/O (camera, mic, haptics) behind a provider interface
- **Providers**: mock, meta (Ray-Ban), vuzix, xreal, openxr, visionos
- **Use Case**: Target multiple devices while preserving a consistent API

### 6. rayskillkit and skills/
- **Purpose**: Map LLM-emitted `actions` to concrete skill implementations
- **Features**:
  - Action schemas for navigation, notifications, and device control
  - Adapters that bind RaySkillKit skills to provider capabilities
- **Use Case**: Execute actions on-device or via paired mobile/edge runtimes

## 📓 Notebooks

### SmartGlass_AI_Agent_Meta_RayBan.ipynb
**Target Audience**: Users and testers
**Content**:
- Setup and installation
- Component testing
- Multimodal integration
- Real-world scenarios for Meta Ray-Ban
- Upload and test with actual smart glass media

### SmartGlass_AI_Agent_Advanced.ipynb
**Target Audience**: Developers and researchers
**Content**:
- Custom configurations
- Performance optimization
- Real-time processing pipelines
- Custom use cases (Shopping, Accessibility)
- Benchmarking tools
- Deployment guidelines

## 📚 Documentation

### README.md
- Project overview
- Quick start guide
- Features and capabilities
- Installation instructions
- Basic usage examples
- Meta Ray-Ban integration tips

### QUICKSTART.md
- 5-minute getting started guide
- Common use cases
- Configuration tips
- Troubleshooting

### CONTRIBUTING.md
- How to contribute
- Code style guidelines
- Development setup
- Testing guidelines
- Feature areas needing help

### docs/API_REFERENCE.md
- Complete API documentation
- All classes and methods
- Parameter descriptions
- Code examples
- Error handling

## 🎯 Example Scripts

### examples/basic_usage.py
- Initialize the agent
- Text-only queries
- Conversation management
- Demonstrates core functionality

### examples/vision_example.py
- Vision processing
- Scene understanding
- Object classification
- Real-world use cases

## 🔄 Data Flow

```
User Input (Audio/Text/Image)
        ↓
┌───────────────────────────────┐
│   SmartGlassAgent             │
│   ┌─────────────────────┐     │
│   │ Audio Processing    │     │
│   │ (Whisper)           │     │
│   └─────────────────────┘     │
│                               │
│   ┌─────────────────────┐     │
│   │ Vision Processing   │     │
│   │ (CLIP)              │     │
│   └─────────────────────┘     │
│                               │
│   ┌─────────────────────┐     │
│   │ Text Generation     │     │
│   │ (GPT-2)             │     │
│   └─────────────────────┘     │
└───────────────────────────────┘
        ↓
Response to User
```

## 🚀 Typical Usage Flow

1. **Initialization**
   ```python
   agent = SmartGlassAgent()
   ```

2. **Capture Input**
   - Audio from Meta Ray-Ban microphone
   - Image from Meta Ray-Ban camera

3. **Process Query**
   ```python
   result = agent.process_multimodal_query(
       audio_input="command.wav",
       image_input="scene.jpg"
   )

    # Extract response with backward compatibility
    response_text = result.get("response", result) if isinstance(result, dict) else result
    actions = result.get("actions", []) if isinstance(result, dict) else []
    raw_payload = result.get("raw", {}) if isinstance(result, dict) else {}
   ```

4. **Get Response**
   - Text response from GPT-2 (see `response_text` above)
   - Optional structured actions/metadata available via `actions` / `raw`
   - (Optional) Convert the text response to speech for audio output

## 🛠️ Configuration Options

### Model Selection
- **Whisper**: tiny, base, small, medium, large
- **CLIP**: vit-base-patch32, vit-large-patch14
- **GPT-2**: gpt2, gpt2-medium, gpt2-large, gpt2-xl

### Device Selection
- Auto-detect (recommended)
- CPU (slower, works everywhere)
- CUDA (faster, requires GPU)

### Performance Tuning
- Model size vs. accuracy tradeoff
- Batch processing
- Frame skipping for real-time
- Context window size

## 📊 File Sizes and Requirements

### Models (Disk Storage Requirements - Downloaded on First Run)
- Whisper tiny: ~39 MB
- Whisper base: ~74 MB
- Whisper small: ~244 MB
- CLIP base: ~350 MB
- GPT-2 base: ~500 MB

*Note: These are disk storage requirements for model files, not runtime memory usage.*

### Disk Space
- Minimum: 1 GB (tiny models)
- Recommended: 2-3 GB (base models)
- Full install: 5+ GB (large models)

### RAM Requirements (System Memory)
- Minimum: 4 GB (for tiny/base models, single image processing)
- Recommended: 8 GB (for base models with multimodal processing)
- Optimal: 16+ GB (for larger models or batch processing)

*Note: These are total system RAM requirements. GPU memory (VRAM) requirements are typically 2-4 GB for base models when using CUDA acceleration. Requirements increase with larger model sizes and concurrent processing.*

## 🔌 Extension Points

The system is designed to be extended:

1. **Add new models**: Replace or add models in respective processors
2. **Add new modalities**: Extend the agent with GPS, IMU, etc.
3. **Custom workflows**: Create custom use-case classes
4. **Platform integration**: Add mobile/embedded platform support

## 📝 Version Information

- **Current Version**: 1.0.0
- **Status**: Stable SDK (SmartGlassAgent and core backends)
- **Python**: 3.9+
- **License**: MIT (see LICENSE and NOTICE for third-party attributions)

## 🔗 Key Dependencies

- torch >= 2.0.0
- transformers >= 4.30.0
- openai-whisper >= 20230314
- Pillow >= 9.5.0
- numpy >= 1.24.0

See `requirements.txt` for complete list.

---

**For detailed API documentation, see [API_REFERENCE.md](docs/API_REFERENCE.md)**

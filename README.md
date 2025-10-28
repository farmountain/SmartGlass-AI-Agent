# SmartGlass AI Agent 👓🤖

A multimodal AI assistant for smart glasses integrating **Whisper** (speech recognition), **CLIP** (vision understanding), and **GPT-2** (language generation). Designed and tested for **Meta Ray-Ban Wayfarer** smart glasses.

## 🌟 Features

- 🎤 **Speech Recognition**: Real-time audio transcription using OpenAI Whisper
- 👁️ **Visual Understanding**: Scene analysis and object recognition using CLIP
- 💬 **Natural Language Generation**: Contextual responses using GPT-2
- 🔄 **Multimodal Integration**: Seamlessly combines audio, vision, and language
- 📓 **Google Colab Ready**: Complete notebook for testing with Meta Ray-Ban

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/farmountain/SmartGlass-AI-Agent.git
cd SmartGlass-AI-Agent

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
from src.smartglass_agent import SmartGlassAgent

# Initialize the agent
agent = SmartGlassAgent(
    whisper_model="base",
    clip_model="openai/clip-vit-base-patch32",
    gpt2_model="gpt2"
)

# Process a multimodal query
result = agent.process_multimodal_query(
    text_query="What am I looking at?",
    image_input="photo.jpg"
)

print(f"Response: {result['response']}")
```

## 📚 Components

### 1. Whisper Audio Processor (`whisper_processor.py`)
- Speech-to-text transcription
- Multilingual support
- Real-time audio processing
- Optimized for smart glasses

### 2. CLIP Vision Processor (`clip_vision.py`)
- Zero-shot image classification
- Scene understanding
- Object identification
- Image-text matching

### 3. GPT-2 Text Generator (`gpt2_generator.py`)
- Natural language responses
- Context-aware generation
- Conversation management
- Text summarization

### 4. SmartGlass Agent (`smartglass_agent.py`)
- Main integration class
- Multimodal query processing
- Conversation history
- Unified interface

## 📓 Google Colab Notebook

The repository includes a comprehensive Google Colab notebook (`SmartGlass_AI_Agent_Meta_RayBan.ipynb`) for testing with Meta Ray-Ban smart glasses:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/farmountain/SmartGlass-AI-Agent/blob/main/SmartGlass_AI_Agent_Meta_RayBan.ipynb)

### Notebook Features:
- ✅ Complete setup and installation
- ✅ Individual component testing
- ✅ Full multimodal integration
- ✅ Real-world use case examples
- ✅ Meta Ray-Ban specific scenarios

## 💡 Use Cases

### 1. Visual Question Answering
```python
# Ask about what you're seeing
response = agent.help_identify(
    image="scene.jpg",
    text_query="What do you see?"
)
```

### 2. Object Recognition
```python
# Identify objects in your view
objects = ['keys', 'phone', 'wallet', 'book']
item = agent.identify_object(image="view.jpg", possible_objects=objects)
print(f"I see your {item}")
```

### 3. Navigation Assistant
```python
# Understand your environment
scene = agent.analyze_scene(image="surroundings.jpg")
print(scene['description'])
```

### 4. Voice Commands with Vision
```python
# Combine voice and vision
result = agent.process_multimodal_query(
    audio_input="command.wav",
    image_input="scene.jpg"
)
```

## 🎯 Examples

The `examples/` directory contains sample scripts:

- `basic_usage.py` - Basic agent functionality
- `vision_example.py` - CLIP vision processing examples

Run examples:
```bash
cd examples
python basic_usage.py
python vision_example.py
```

## 🔧 Configuration

### Model Selection

**Whisper Models** (Speed ↔ Accuracy):
- `tiny` - Fastest, basic accuracy
- `base` - **Recommended** - Good balance
- `small` - Better accuracy, slower
- `medium` - High accuracy, much slower
- `large` - Best accuracy, very slow

**CLIP Models**:
- `openai/clip-vit-base-patch32` - **Recommended**
- `openai/clip-vit-large-patch14` - Higher accuracy

**GPT-2 Models**:
- `gpt2` - **Recommended** - Fast and efficient
- `gpt2-medium` - Better generation
- `gpt2-large` - High quality, slower
- `gpt2-xl` - Best quality, very slow

### Device Selection

```python
# Auto-detect (uses GPU if available)
agent = SmartGlassAgent(device=None)

# Force CPU
agent = SmartGlassAgent(device="cpu")

# Force GPU
agent = SmartGlassAgent(device="cuda")
```

## 🏗️ Project Structure

```
SmartGlass-AI-Agent/
├── src/
│   ├── __init__.py
│   ├── whisper_processor.py      # Whisper audio processing
│   ├── clip_vision.py             # CLIP vision processing
│   ├── gpt2_generator.py          # GPT-2 text generation
│   └── smartglass_agent.py        # Main agent class
├── examples/
│   ├── basic_usage.py             # Basic examples
│   └── vision_example.py          # Vision examples
├── SmartGlass_AI_Agent_Meta_RayBan.ipynb  # Colab notebook
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── LICENSE                        # MIT License
```

## 📋 Requirements

- Python 3.8+
- PyTorch 2.0+
- Transformers 4.30+
- OpenAI Whisper
- Pillow, NumPy, SoundFile

See `requirements.txt` for complete list.

## 🔍 Testing with Meta Ray-Ban

### Capturing Media
1. Use Meta Ray-Ban app to capture photos/videos
2. Transfer media to your device
3. Load into the agent for processing

### Best Practices
- ✅ Ensure good lighting for images
- ✅ Record audio in quiet environments
- ✅ Use base models for better battery life
- ✅ Respect privacy in public spaces

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [OpenAI CLIP](https://github.com/openai/CLIP) - Vision-language model
- [Hugging Face Transformers](https://huggingface.co/transformers/) - GPT-2 and CLIP
- [Meta Ray-Ban](https://www.ray-ban.com/usa/discover-ray-ban-stories) - Smart glasses

## 📞 Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Built with ❤️ for the future of smart glasses**
# 🕶️ SmartGlass-AI-Agent

Build a **multimodal AI assistant for smart glasses** using **Whisper**, **vision-language models (VLMs)**, and **LLMs**—powered by **Google Colab** with modular session-based workshops.

This project is designed for rapid prototyping and deployment on devices like **Meta Ray-Ban Wayfarer smart glasses**, and includes real-world industry applications in **healthcare, retail, security, travel**, and more.

---

## 🚀 Features

- 🎙️ **Voice Trigger** with Whisper: wake words like “Hey Athena” with command detection
- 🖼️ **Visual Understanding** via CLIP, DeepSeek-Vision, or GPT-4V
- 🧠 **LLM Reasoning Chain**: Convert multimodal input into smart assistant responses
- 🔧 **Modular Pipeline** for smart glasses or mobile deployment
- 🧪 **Google Colab Notebooks** for step-by-step hands-on learning

---

## 🧭 Learning Journey (18 Weeks)

| Week | Module |
|------|--------|
| 1    | [Multimodal Basics: Whisper + Vision + LLM](colab_notebooks/Session1_Multimodal_Basics.ipynb) |
| 2    | [Voice Trigger with Whisper Wake Words](colab_notebooks/Session2_Whisper_WakeWord.ipynb) |
| 3    | Smart Vision: Scene Description with DeepSeek-Vision |
| 4    | Command to Action Mapping with LLMs |
| ...  | *(Ongoing — see roadmap.md)* |

---

## 📂 Project Structure

```

SmartGlass-AI-Agent/
│
├── colab_notebooks/        # Step-by-step learning notebooks
│   ├── Session1_Multimodal_Basics.ipynb
│   └── Session2_Whisper_WakeWord.ipynb
│
├── audio_samples/          # Sample .wav inputs (wake words, commands)
├── images/                 # Diagrams and architecture illustrations
├── src/                    # Modular pipeline: vision, voice, agent
├── examples/               # Domain-specific demos: travel, healthcare, etc.
├── roadmap.md              # 18-week curriculum and feature roadmap
├── requirements.txt        # Python dependencies
└── README.md

````

---

## 🛠️ Setup Instructions

```bash
# Clone the repository
git clone https://github.com/farmountain/SmartGlass-AI-Agent.git
cd SmartGlass-AI-Agent

# (Optional) Install Python dependencies
pip install -r requirements.txt
````

> 💡 Recommended: Run the notebooks in [Google Colab](https://colab.research.google.com) for instant GPU access and voice/vision support.

---

## 🧪 Example Use Case: "Athena, what's around me?"

1. Smart glasses capture image → analyzed by VLM
2. Wake word "Hey Athena" → Whisper activates command
3. LLM combines vision + voice → generates reply
4. Audio output or AR display provides user feedback

---

## 🧠 Target Industries & Scenarios

* 🏪 Retail: “Hey Athena, price check”
* 🧳 Travel: “Athena, translate this sign”
* 🏥 Healthcare: “Show patient vitals”
* 👮 Security: “Athena, start alert mode”
* 🎓 Education: “Explain this object”

---

## 📅 Roadmap

See [`roadmap.md`](roadmap.md) for:

* Future sessions
* Planned model integrations (DeepSeek-Vision, GPT-4V, Whisper Tiny)
* Edge deployment options (on-device/offload)
* Meta SDK compatibility

---

## 📄 Apache 2.0, Commercial Use & Licensing

This open-source version is free to use under the Apache 2.0 License.

For commercial deployment, OEM integration (e.g. smart glasses manufacturers), or enterprise features (e.g. RAG modules, EHR integration, multilingual OCR), please contact:

📩 farmountain@gmail.com

Commercial licenses include priority support, closed-source modules, and custom deployment options.


---

## 👨‍💻 Author

**Liew Keong Han** (farmountain)
Senior Data & AI Architect
🌐 [GitHub](https://github.com/farmountain)


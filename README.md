# 👓🤖 SmartGlass AI Agent

A multimodal AI assistant for smart glasses, integrating:

- **🎙️ Whisper** (speech-to-text)
- **👁️ CLIP / DeepSeek-Vision** (vision-language understanding)
- **🧠 GPT-2 / LLMs** (natural language generation)

Built for the **Meta Ray-Ban Wayfarer** and similar wearable devices.  
Includes an **18-week learning program** with step-by-step **Google Colab workshops**, and a fully functional modular Python agent (`SmartGlassAgent`) for real-world deployment.

---

## 🌟 Features

- 🎤 **Speech Recognition**: Real-time transcription with OpenAI Whisper
- 👁️ **Visual Understanding**: Scene and object analysis using CLIP or DeepSeek-Vision
- 💬 **Language Generation**: Responses via GPT-2 (or LLM of your choice)
- 🔄 **Multimodal Integration**: Voice + Vision → LLM-powered interaction
- 🧪 **Google Colab Ready**: Modular 18-week training + live testing
- 🔧 **Modular Agent SDK**: `SmartGlassAgent` class with clean APIs

---

## 🚀 Quick Start

### 🔧 Clone and Install

```bash
git clone https://github.com/farmountain/SmartGlass-AI-Agent.git
cd SmartGlass-AI-Agent
pip install -r requirements.txt
````

---

### 🔨 Use the Agent in Python

```python
from src.smartglass_agent import SmartGlassAgent

agent = SmartGlassAgent(
    whisper_model="base",
    clip_model="openai/clip-vit-base-patch32",
    gpt2_model="gpt2"
)

result = agent.process_multimodal_query(
    text_query="What am I looking at?",
    image_input="scene.jpg"
)

print("Response:", result["response"])
```

---

## 🧭 18-Week Learning Journey (Google Colab Curriculum)

| Week | Module                                                                                        |
| ---- | -------------------------------------------------------------------------------------------   |
| 1    | [Multimodal Basics: Whisper + CLIP + GPT](colab_notebooks/Session1_Multimodal_Basics.ipynb)   |
| 2    | [Wake Words with Whisper](colab_notebooks/Session2_WakeWord_Detector_WhisperOnly.ipynb)       |
| 3    | [Scene Description with Vision-Language Models](colab_notebooks/Session3_Scene_Description_CLIP.ipynb)                                                |
| 4    | [Intent Detection + Prompt Engineering](colab_notebooks/Session4_Intent_Detection_Prompt_Engineering.ipynb)                                                        |
| 5    | [Meta Ray-Ban SDK Simulation](colab_notebooks/Session5_Meta_RayBan_SDK_Simulation.ipynb)                                                                  |
| 6    | [Real-Time Audio Streaming](colab_notebooks/Session6_RealTime_Audio_Streaming.ipynb)                                                                   |
| 7    | [Visual OCR and Translation](ccolab_notebooks/Session7_Visual_OCR_and_Translation.ipynb)                                                                   |
| 8    | [Domain-Specific Voice Commands](colab_notebooks/Session8_Domain_Specific_Voice_Commands.ipynb)                                                              |
| 9    | [On-Device Tiny Models (CPU)](colab_notebooks/Session9_On_Device_Tiny_Models_CPU.ipynb)                                                                 |
| 10   | [Caching & Optimization](colab_notebooks/Session10_Caching_Optimization.ipynb)                                                                      |
| 11   | [Mobile UI/UX Considerations](colab_notebooks/Session11_Mobile_UI_UX.ipynb)                                                                 |
| 12   | [Meta Ray-Ban Deployment Flow](colab_notebooks/Session12_Meta_RayBan_Deployment.ipynb)                                                                |
| 13   | [Use Case: Healthcare](colab_notebooks/Session2_WakeWord_Detector_WhisperOnly.ipynb)                                                                        |
| 14   | [Use Case: Retail](colab_notebooks/Session2_WakeWord_Detector_WhisperOnly.ipynb)                                                                            |
| 15   | [Use Case: Travel Assistant](colab_notebooks/Session2_WakeWord_Detector_WhisperOnly.ipynb)                                                                  |
| 16   | [Use Case: Security Agent](to be continued)                                                                    |
| 17   | [Assemble End-to-End Glass Agent](to be continued)                                                             |
| 18   | [Pitch Deck + Commercial Demo](For private use only)                                                                |

See [`roadmap.md`](roadmap.md) for full breakdown.

---

## 🧠 Use Case Highlights

* 🏪 **Retail**: "Hey Athena, price check"
* 🧳 **Travel**: "Translate this sign"
* 🏥 **Healthcare**: "Show patient vitals"
* 👮 **Security**: "Alert mode on"
* 🎓 **Education**: "Explain this object"

---

## 📓 Try It on Colab (Week 1 Session)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/farmountain/SmartGlass-AI-Agent/blob/main/colab_notebooks/Session1_Multimodal_Basics.ipynb)

---

## 🧱 Project Structure

```plaintext
SmartGlass-AI-Agent/
├── colab_notebooks/         # 18-week training notebooks
├── src/
│   ├── whisper_processor.py
│   ├── clip_vision.py
│   ├── gpt2_generator.py
│   └── smartglass_agent.py
├── examples/                # Domain-specific demos
├── audio_samples/           # Wake word and command audio
├── images/                  # Architecture diagrams
├── requirements.txt
├── roadmap.md
├── LICENSE
├── NOTICE
└── README.md
```

---

## 📋 Requirements

* Python 3.8+
* PyTorch 2.0+
* `transformers`, `torchaudio`, `whisper`, `soundfile`, `Pillow`, `numpy`
* GPU Recommended for Colab (for Whisper + CLIP)

---

## 🧪 Testing on Meta Ray-Ban

1. Use Ray-Ban app to capture photo/audio
2. Transfer to your device or notebook
3. Load into the SmartGlassAgent
4. Use vision + audio inputs to trigger LLM responses

---

## 🏢 Commercial Licensing

This project is available under the **Apache 2.0 License** for open learning and research use.

For **commercial deployment**, OEM integration, or enterprise modules:

📩 [farmountain@gmail.com](mailto:farmountain@gmail.com)

Commercial license includes:

* Priority support
* Proprietary components (e.g. RAG, EHR, NLU)
* Integration with Meta SDK or smartglasses hardware

See [`NOTICE`](NOTICE) for details.

---

## 👨‍💻 Author

**Liew Keong Han** (`@farmountain`)
Senior Data & AI Architect, Capgemini | AI Wearables Researcher
🔗 [GitHub](https://github.com/farmountain)

---

## 📄 License

Licensed under the **Apache License 2.0**.
See [`LICENSE`](LICENSE) for terms.

---

**Built with ❤️ for the future of wearable AI**

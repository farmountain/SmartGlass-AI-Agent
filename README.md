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

## 📄 License

Licensed under the **Apache 2.0 License**.
Feel free to fork, adapt, and contribute.

---

## 👨‍💻 Author

**Liew Keong Han** (farmountain)
Senior Data & AI Architect
🌐 [GitHub](https://github.com/farmountain)


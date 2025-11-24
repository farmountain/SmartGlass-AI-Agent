# 👓🤖 SmartGlass AI Agent

A multimodal AI assistant for smart glasses, integrating:

- **🎙️ Whisper** (speech-to-text)
- **👁️ CLIP / DeepSeek-Vision** (vision-language understanding)
- **🧠 student: Llama-3.2-3B / Qwen-2.5-3B (Week 10/11 plan)** for natural language generation (legacy GPT-2 path deprecated)

Built for the **Meta Ray-Ban Wayfarer** and similar wearable devices.
Includes an **18-week learning program** with step-by-step **Google Colab workshops**, and a fully functional modular Python agent (`SmartGlassAgent`) for real-world deployment.

📄 Latest weekly doc: [Week 4 Report](docs/WEEK_04.md).

---

## 🌟 Features

- 🎤 **Speech Recognition**: Real-time transcription with OpenAI Whisper
- 👁️ **Visual Understanding**: Scene and object analysis using CLIP or DeepSeek-Vision
- 💬 **Language Generation**: Responses via the student Llama-3.2-3B / Qwen-2.5-3B interim models (GPT-2 deprecated)
- 🔄 **Multimodal Integration**: Voice + Vision → LLM-powered interaction
- 🧪 **Google Colab Ready**: Modular 18-week training + live testing
- 🔧 **Modular Agent SDK**: `SmartGlassAgent` class with clean APIs

---

## 🚀 Quick Start

### 🌐 Contribute Through Pull Requests

1. **Propose your change on the web.** Navigate to the file you want to update in GitHub and choose **Edit this file**. GitHub will automatically fork the repository if needed and open the web editor.
2. **Describe your intent.** After editing, provide a concise summary of the change, add any relevant testing notes, and click **Propose changes** to start a new pull request.
3. **Open the pull request.** Review the diff, confirm the base branch, and submit the PR. No local cloning is required.
4. **Let CI validate the update.** Wait for the automated checks to finish. Inspect the linked logs and artifacts to verify linting, tests, and documentation previews.
5. **Address feedback.** Use the web editor to push follow-up commits, respond to reviewer comments, and request re-runs of any failed checks.

---

### 📦 Legacy Local Installation (Optional)

If you still need to run the project locally, you can follow the classic setup:

```bash
git clone https://github.com/farmountain/SmartGlass-AI-Agent.git
cd SmartGlass-AI-Agent
pip install -r requirements.txt
````

#### Microphone + TTS prerequisites

The Meta provider streams audio via either **sounddevice** (default) or **PyAudio**, and uses **pyttsx3** for offline text-to-speech. Both capture backends depend on [PortAudio](http://www.portaudio.com/):

- **Linux (Debian/Ubuntu):** `sudo apt-get install portaudio19-dev` then `pip install sounddevice` (or `pip install pyaudio`).
- **macOS (Homebrew):** `brew install portaudio` then `pip install sounddevice` (or `pip install pyaudio`).
- **Windows:** install the matching [PortAudio binary](https://www.portaudio.com/download.html) or use `pip install pipwin && pipwin install pyaudio`. If `sounddevice` installation fails, prefer the `pyaudio` fallback.

If you only need playback, `pyttsx3` has no external audio driver requirement, but microphone capture will need at least one of the PortAudio-backed libraries above.

### 📊 Render documentation KPIs

Generate a Markdown-formatted table from the latest KPI CSVs under `docs/artifacts`:

```bash
python scripts/doc_kpi_table.py --artifacts docs/artifacts > /tmp/doc_kpis.md
```

The CI summary step automatically runs this helper and posts the newest table alongside the other benchmark outputs.

---

## 🧑‍🏫➡️🧠 Teacher–Student SNN Pipeline (Concise)

- **Pipeline:** `scripts/train_snn_student.py` distills a transformer teacher into a spiking-friendly student with temperature-scaled KD and gradient accumulation so it can run in constrained Colab-style environments.【F:scripts/train_snn_student.py†L1-L208】
- **Artifacts:** Training writes `student.pt` and `metadata.json` under `artifacts/snn_student` by default (override with `--output-dir`).【F:scripts/train_snn_student.py†L224-L236】【F:scripts/train_snn_student.py†L242-L275】
- **Launch training:**

  ```bash
  python scripts/train_snn_student.py \
    --teacher-model sshleifer/tiny-gpt2 \
    --num-steps 50 \
    --batch-size 4 \
    --output-dir artifacts/snn_student_demo
  ```

- **SNN inference demo:** Load the saved student (or fall back to the stubbed path) via the `SNNLLMBackend` demo module and generate a quick response:

  ```bash
  python - <<'PY'
  from src.llm_snn_backend import SNNLLMBackend

  backend = SNNLLMBackend(model_path="artifacts/snn_student/student.pt")
  print(backend.generate("Hello from the glasses", max_tokens=24))
  PY
  ```

  The backend will automatically reuse the saved artifact when available and degrade gracefully to a stubbed tokenizer/model when the files are missing, keeping the demo runnable on any machine.【F:src/llm_snn_backend.py†L21-L104】【F:src/llm_snn_backend.py†L143-L181】

---

### 🔨 Use the Agent in Python

```python
from src.smartglass_agent import SmartGlassAgent
from src import SNNLLMBackend

# Default: ANN language backend powered by the legacy GPT-2 generator
agent = SmartGlassAgent(
    whisper_model="base",
    clip_model="openai/clip-vit-base-patch32",
    gpt2_model="gpt2",
)

result = agent.process_multimodal_query(
    text_query="What am I looking at?",
    image_input="scene.jpg",
)

print("Response:", result["response"])

# Optional: swap in the experimental SNN student backend
snn_agent = SmartGlassAgent(
    whisper_model="base",
    clip_model="openai/clip-vit-base-patch32",
    gpt2_model="gpt2",
    llm_backend=SNNLLMBackend(),
)
```

#### Provider selection

The data access layer defaults to the offline `mock` provider so examples and CI run without hardware:

```bash
export PROVIDER=mock  # default, optional
```

Switching to the `meta` preview stub keeps the same API surface while the real SDK is under development:

```bash
export PROVIDER=meta
```

The `meta` provider (via the `MetaRayBanProvider`) currently returns placeholder telemetry, frames, and audio envelopes that mirror the expected Ray-Ban SDK schema.

Deterministic vendor-specific mocks are also available so you can stub integrations for different runtimes:

```bash
export PROVIDER=vuzix    # 640x480 RGB frames + waveguide overlay metadata
export PROVIDER=xreal    # 1080p Beam-style captures + Nebula overlay stubs
export PROVIDER=openxr   # Square eye-buffers with host-delegated overlays
export PROVIDER=visionos # 1440x1440 persona frames + shared-space overlays
```

Each of these providers exposes deterministic camera/mic fixtures tuned to the vendor's expected resolutions, vendor-tagged audio/permission responses, and a `has_display()` helper that the SDK uses to reflect true overlay availability.

---

## 🧩 RaySkillKit Skill Catalogue

RaySkillKit now ships with a compact catalogue of twelve skills that blend legacy validation fixtures with the travel and retail packs produced by the `raycli` workflow:

- `skill_001` – Spatial Navigation Assistant (navigation/routing baseline)
- `skill_002` – Vision Detection Baseline (vision detection baseline)
- `skill_003` – Speech Transcription Baseline (audio speech baseline)
- `travel_fastlane` – Airport FastLane Wait Estimator (travel operations regression)
- `travel_safebubble` – Air Travel SafeBubble Risk Assessor (travel safety regression)
- `travel_bargaincoach` – BargainCoach Fare Forecaster (travel commerce forecasting)
- `retail_wtp_radar` – Retail WTP Radar (retail pricing regression)
- `retail_capsule_gaps` – Capsule Gap Forecaster (retail supply forecasting)
- `retail_minute_meal` – Minute Meal Throughput (retail operations regression)
- `rt_wtp_radar` – Runtime Retail WTP Radar (retail pricing regression)
- `rt_capsule_gaps` – Runtime Capsule Gap Forecaster (retail supply forecasting)
- `rt_minute_meal` – Runtime Minute Meal Throughput (retail operations regression)

Model and stats artifacts generated by `raycli train_travel_pack` are published under `rayskillkit/skills/{models,stats}/travel`, so downstream tooling and release scripts can resolve the new paths without additional configuration. The travel model binaries are produced on demand by CI and distributed with release bundles rather than being committed directly to the repository. Running `raycli train_retail_pack --output-root rayskillkit/skills --manifest-path rayskillkit/skills.json` will train the retail fixtures and emit quantized INT8 ONNX exports alongside stats under `rayskillkit/skills/{models,stats}/retail`; these artifacts are version-controlled to keep the SDK regression suite deterministic.

### 📦 Pilot drop packaging

RaySkillKit binaries and stats are distributed as self-contained **pilot drops**. Each drop includes:

1. `skills_bundle.zip` – a compressed copy of `rayskillkit/skills/{models,stats}`.
2. `release_manifest.json` – a manifest produced by `cicd.make_manifest` describing every file and its SHA256 digest.
3. `release_manifest.sig` – an Ed25519 signature of the manifest emitted by `cicd.sign_manifest`.

Use `cicd/package_release.py` to assemble these artifacts locally. Provide an Ed25519 seed through either `--key` (path to raw bytes) or `--key-env` (name of an environment variable containing the seed in hex/base64) so the manifest can be signed:

```bash
export PILOT_SIGNING_KEY=$(openssl rand -hex 32)  # replace with your long-term key material
python cicd/package_release.py \
  --staging-dir dist/local_pilot_drop \
  --bundle-name skills_bundle.zip \
  --key-env PILOT_SIGNING_KEY

ls dist/local_pilot_drop
# skills/  skills_bundle.zip  release_manifest.json  release_manifest.sig
```

Tagged pushes (e.g., `v1.2.3`) automatically run the same script via the **Release Packaging** GitHub Actions workflow. The workflow expects a `MANIFEST_SIGNING_KEY` repository secret containing the Ed25519 seed; it uploads the bundle, manifest, and signature as workflow artifacts and attaches them to a draft GitHub Release so the files are ready for distribution without manual steps.

---

## 📈 Benchmarks

### Audio latency bench

Run the synthetic audio benchmark to profile `EnergyVAD` frame counts and `ASRStream` stability without relying on any
external recordings:

```bash
python bench/audio_bench.py --out artifacts/audio_latency.csv
```

The script procedurally generates deterministic tone, silence, and speech-like signals, replays scripted `MockASR`
partials, and writes latency/frame/reversal metrics to both `artifacts/audio_latency.csv` and the telemetry metrics
artifacts for CI consumption.

### Image keyframe + OCR bench

Profile the `select_keyframes` and `VQEncoder` pipeline alongside the synthetic OCR mock:

```bash
python bench/image_bench.py
```

The script renders deterministic clips (static, gradient, motion), records selection/encoding timings into
`artifacts/image_latency.csv`, and evaluates `MockOCR` precision on fabricated panels with results stored in
`artifacts/ocr_results.csv`. See the [Week 3 Report](docs/WEEK_03.md) for design notes, invariances, and interpretation tips.

## 🔍 CI Audio Validation

Automated checks exercise both the VAD and ASR stacks entirely with synthetic fixtures so contributors can run the
suite without credentials or cloud audio services. Unit tests such as `tests/test_vad_thresholds.py` and
`tests/test_vad_framing.py` validate the energy math in `EnergyVAD`, while `tests/test_asr_interface_contract.py` and
`tests/test_asr_delta_gate.py` assert that δ-gated streaming transcripts remain stable under injected noise. The
`bench/audio_bench.py` workflow (added in [PR #25](https://github.com/farmountain/SmartGlass-AI-Agent/pull/25)) is wired
into CI to publish the `audio_latency.csv` artifact summarising reversal counts and latency distributions. By default
`ASRStream` instantiates the deterministic `MockASR` unless `SMARTGLASS_USE_WHISPER=1`, keeping the end-to-end validation
loop entirely offline-friendly.

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
| 13   | [Use Case: Healthcare](colab_notebooks/Session13_Healthcare_UseCase.ipynb)                                                                        |
| 14   | [Use Case: Retail](to be continued)                                                                            |
| 15   | [Use Case: Travel Assistant](To be continued)                                                                  |
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
AI Architect | AI Researcher
🔗 [GitHub](https://github.com/farmountain)

---

## 📄 License

Licensed under the **Apache License 2.0**.
See [`LICENSE`](LICENSE) for terms.

---

**Built with ❤️ for the future of wearable AI**

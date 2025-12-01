# 👓🤖 SmartGlass AI Agent

A multimodal AI assistant for smart glasses, integrating:

- **🎙️ Whisper** (speech-to-text)
- **👁️ CLIP / DeepSeek-Vision** (vision-language understanding)
- **🧠 student: Llama-3.2-3B / Qwen-2.5-3B (Week 10/11 plan)** for natural language generation (legacy GPT-2 path deprecated)

Built for the **Meta Ray-Ban Wayfarer** and similar wearable devices.
Includes an **18-week learning program** with step-by-step **Google Colab workshops**, and a fully functional modular Python agent (`SmartGlassAgent`) for real-world deployment. The **SmartGlassAgent** and primary SDK classes are considered **stable as of v1.0**, so downstream apps can rely on their public methods without churn.

📄 Latest weekly doc: [Week 4 Report](docs/WEEK_04.md).

---

## 🌟 Features

- 🎤 **Speech Recognition**: Real-time transcription with OpenAI Whisper
- 👁️ **Visual Understanding**: Scene and object analysis using CLIP or DeepSeek-Vision
- 💬 **Language Generation**: Responses via the student Llama-3.2-3B / Qwen-2.5-3B interim models (GPT-2 deprecated)
- 🔄 **Multimodal Integration**: Voice + Vision → LLM-powered interaction
- 🧪 **Google Colab Ready**: Modular 18-week training + live testing
- 🔧 **Modular Agent SDK**: `SmartGlassAgent` class with clean APIs and stable SDK entry points as of v1.0

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

### 📱 Android HTTP integration

Building a mobile client? Follow the step-by-step endpoint guide in
[`docs/android_integration.md`](docs/android_integration.md) for payloads,
session handling, and a local server quickstart.

---

### 🔒 Edge runtime privacy controls

The edge runtime defaults to **not** retaining raw audio, frames, or transcripts in memory to reduce the risk of accidental data
leakage. Opt-in persistence is available through environment variables when you need debugging traces:

| Environment variable | Default | Effect |
| --- | --- | --- |
| `STORE_RAW_AUDIO` | `false` | Keep per-session audio buffers in memory for replay and policy enforcement. |
| `STORE_RAW_FRAMES` | `false` | Preserve recent video frames so subsequent queries can reuse the latest view. |
| `STORE_TRANSCRIPTS` | `false` | Retain transcripts generated from audio ingestion and text queries. |

See [PRIVACY.md](PRIVACY.md) for detailed threat-modeling notes and guidance on when to enable each option.

---

## 🧑‍🏫➡️🧠 Teacher–Student SNN Pipeline (Concise)

- **Pipeline:** `scripts/train_snn_student.py` distills a transformer teacher into a spiking-friendly student with temperature-scaled KD and gradient accumulation so it can run in constrained Colab-style environments.【F:scripts/train_snn_student.py†L1-L208】
- **Artifacts:** Training writes `student.pt` and `metadata.json` under `artifacts/snn_student` by default (override with `--output-dir`).【F:scripts/train_snn_student.py†L224-L236】【F:scripts/train_snn_student.py†L242-L275】
- **Detailed walkthrough:** See [`docs/snn_pipeline.md`](docs/snn_pipeline.md) for a step-by-step runbook, artifact layout, and how `SNNLLMBackend` consumes the saved files.【F:docs/snn_pipeline.md†L1-L77】
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

The agent now consumes any backend implementing `src.llm_backend_base.BaseLLMBackend` so you can swap language generators without touching the agent logic. The built-in `SNNLLMBackend` exposes the same interface for on-device, spiking-friendly generation, while the ANN/GPT-2 adapter remains available for comparison.

**Action-aware multimodal query with the SNN backend (on-device capable):**

```python
import os

from src.llm_snn_backend import SNNLLMBackend
from src.smartglass_agent import SmartGlassAgent

# Runs fully on-device when the spiking student checkpoint is present
snn_backend = SNNLLMBackend(model_path="artifacts/snn_student/student.pt")

agent = SmartGlassAgent(
    whisper_model="base",
    clip_model="openai/clip-vit-base-patch32",
    llm_backend=snn_backend,
    provider=os.getenv("PROVIDER", "mock"),  # honors PROVIDER env var
)

result = agent.process_multimodal_query(
    text_query="Describe the scene and propose next steps",
    image_input="A person standing next to a bicycle",
)

print("response:", result["response"])
print("actions:")
for action in result["actions"]:
    print(" -", action.get("type"), action.get("payload"))
```

See [Action schema and RaySkillKit mapping](docs/actions_and_skills.md) for the structured envelope, sample payloads, and how to bind each `action` entry to a concrete skill implementation. The same `process_multimodal_query` shape applies to any `BaseLLMBackend`, so swapping in cloud backends or the ANN GPT-2 adapter continues to return action-aware responses while `SNNLLMBackend` keeps generation entirely on-device when the checkpoint is available.

#### CLI demo

To try the same pipeline from the terminal, run the `examples/cli_smartglass.py` demo from the repository root. It loads an image, walks through the agent pipeline, and streams the generated response (optionally using the SNN backend):

```bash
python -m examples.cli_smartglass --image images/scene.jpg --backend snn
```

Omit `--backend snn` to use the default backend.

#### Provider selection

`drivers.providers.get_provider` constructs the driver layer for you. When you omit the ``name`` argument, it reads the ``PROVIDER`` environment variable (default: ``"mock"``) so scripts and tests can share a single default selection. Supported provider names are ``mock``, ``meta``, ``vuzix``, ``xreal``, ``openxr``, and ``visionos``; unknown values fall back to the deterministic mock provider. `SmartGlassAgent` mirrors this behavior—if you skip the ``provider`` argument, it calls ``get_provider()`` under the hood to honor the environment variable:

```bash
export PROVIDER=mock  # default, optional
```

Passing a string uses the same resolver explicitly:

```python
from src.smartglass_agent import SmartGlassAgent

agent = SmartGlassAgent(provider="meta")
```

You can also create the provider yourself and pass it into the agent for explicit control:

```python
from drivers.providers import get_provider
from src.smartglass_agent import SmartGlassAgent

provider = get_provider("meta", api_key="YOUR_META_APP_KEY")
agent = SmartGlassAgent(provider=provider)
```

`PROVIDER=meta` now selects a **Meta Ray-Ban SDK wrapper** that automatically falls back to deterministic mocks whenever the `metarayban` SDK package is not installed. The wrapper accepts three key configuration fields when you construct it directly in Python:

- `api_key` – optional API token to pass through to SDK calls that require auth.
- `device_id` – Ray-Ban device identifier to stamp on camera/mic/audio/haptics payloads (defaults to `RAYBAN-MOCK-DEVICE`).
- `transport` – SDK transport hint such as `ble` or `wifi` (defaults to `mock`).

Example: 

```python
from drivers.providers.meta import MetaRayBanProvider

provider = MetaRayBanProvider(
    api_key="YOUR_META_APP_KEY",
    device_id="RAYBAN-1234",
    transport="ble",
    prefer_sdk=True,  # only flips on if the metarayban SDK is importable
)
```

When `prefer_sdk=True` **and** the `metarayban` dependency is importable, the provider will route camera and microphone calls into the real SDK hooks (to be implemented) instead of the deterministic fixtures. CI and default local runs keep using the mock data because `prefer_sdk` defaults to `False` and the SDK is not present in the test environment.

When a vendor SDK package is missing, the provider automatically falls back to deterministic mock fixtures so you can still exercise the camera, microphone, and overlay flows without hardware.

Deterministic vendor-specific mocks are also available so you can stub integrations for different runtimes:

```bash
export PROVIDER=vuzix    # 640x480 RGB frames + waveguide overlay metadata
export PROVIDER=xreal    # 1080p Beam-style captures + Nebula overlay stubs
export PROVIDER=openxr   # Square eye-buffers with host-delegated overlays
export PROVIDER=visionos # 1440x1440 persona frames + shared-space overlays
```

Each of these providers exposes deterministic camera/mic fixtures tuned to the vendor's expected resolutions, vendor-tagged audio/permission responses, and a `has_display()` helper that the SDK uses to reflect true overlay availability.

##### Contributing Meta SDK bindings

The mock-first Meta Ray-Ban wrapper lives in `drivers/providers/meta.py`. To land real SDK calls:

- Replace the `_sdk_frames` stubs inside `MetaRayBanCameraIn` and `MetaRayBanMicIn` with calls into the `metarayban` APIs once the official bindings are available.
- Swap the `_sdk_audio`/`_sdk_speak` placeholder in `drivers/providers/meta.py` for real metarayban TTS and earcon hooks when those bindings land, keeping the current mocks as the fallback path.
- Keep the deterministic mock generators as the fallback path for CI and local dev (they should still run when `prefer_sdk` is `False` or the SDK is missing).
- Add regression tests under `tests/test_provider_conformance.py` that exercise both the mock and SDK-backed paths so we can keep provider swaps safe.

### 🕶️ Meta Ray-Ban Integration (Stub)

The Android sample ships with a **`MetaRayBanManager`** façade that mirrors the expected Meta Ray-Ban SDK shape while SDK bindings are still pending. The manager exposes connect, capture, and streaming-style methods that currently emit deterministic placeholder behavior:

- `connect(deviceId, transport)` logs a connection attempt and waits briefly to simulate setup while noting that the provided `device_id` plus `BLE`/`Wi-Fi` transport should map directly onto the future SDK discovery/connection calls.【F:sdk-android/src/main/kotlin/com/smartglass/sdk/rayban/MetaRayBanManager.kt†L14-L38】
- `capturePhoto()` returns a packaged placeholder bitmap until the SDK camera stream is available, and `startAudioStreaming()` emits a short flow of labeled fake audio chunks to exercise downstream consumers.【F:sdk-android/src/main/kotlin/com/smartglass/sdk/rayban/MetaRayBanManager.kt†L40-L73】
- Both stub entry points include TODOs marking where real SDK calls and resource teardown will land once Meta publishes the official interfaces.【F:sdk-android/src/main/kotlin/com/smartglass/sdk/rayban/MetaRayBanManager.kt†L20-L52】【F:sdk-android/src/main/kotlin/com/smartglass/sdk/rayban/MetaRayBanManager.kt†L69-L76】

The **demo app buttons** exercise these stubbed hooks end-to-end: **Connect** invokes `MetaRayBanManager.connect` with a placeholder device ID and BLE transport, **Capture** calls `capturePhoto` then posts the saved JPEG through `SmartGlassClient.answer`, and **Send** submits text-only prompts. Each path includes inline TODOs noting where real SDK wiring, image capture, and streaming should be substituted once the bindings are available.【F:sample/src/main/java/com/smartglass/sample/SampleActivity.kt†L28-L104】

When you upgrade to real SDK access, swap the stubbed connect/capture/streaming logic inside `MetaRayBanManager` for the official calls and plumb the **`device_id`/transport** mapping through to the SDK’s discovery options. The demo activity can then forward actual camera frames and microphone streams via `SmartGlassClient` without changing the button UX, keeping the mock path available for CI by leaving the placeholder flows as the fallback.

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

## 📊 Runtime metrics

The edge runtime emits per-stage latency histograms for the **VAD**, **ASR**, **Vision**, **LLM**, and **Skill** phases. Each
stage wraps its critical section in a `record_latency(<stage>)` context manager so the `/metrics` endpoint aggregates counts,
totals, averages, and min/max timings for individual stages plus an `all` roll-up across them. Alongside latencies, the
endpoint surfaces lifecycle counters (`sessions.created`, `sessions.active`) and total query volume so operators can track
load and concurrency without inspecting logs. The response also reports a boolean `display_available` flag inferred from the
active session agents (via `SmartGlassAgent.has_display`/`display`/`overlay` attributes) and, if no sessions exist, from the
configured provider hint (`display|glass|hud`) to indicate whether the deployment can render overlays.

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

| Week | Module                                                                                                    |
| ---- | --------------------------------------------------------------------------------------------------------- |
| 1    | [Multimodal Basics: Whisper + CLIP + GPT](colab_notebooks/Session1_Multimodal_Basics.ipynb)               |
| 2    | [Wake Words with Whisper](colab_notebooks/Session2_WakeWord_Detector_WhisperOnly.ipynb)                   |
| 3    | [Scene Description with Vision-Language Models](colab_notebooks/Session3_Scene_Description_CLIP.ipynb)    |
| 4    | [Intent Detection + Prompt Engineering](colab_notebooks/Session4_Intent_Detection_Prompt_Engineering.ipynb)|
| 5    | [Meta Ray-Ban SDK Simulation](colab_notebooks/Session5_Meta_RayBan_SDK_Simulation.ipynb)                  |
| 6    | [Real-Time Audio Streaming](colab_notebooks/Session6_RealTime_Audio_Streaming.ipynb)                      |
| 7    | [Visual OCR and Translation](colab_notebooks/Session7_Visual_OCR_and_Translation.ipynb)                   |
| 8    | [Domain-Specific Voice Commands](colab_notebooks/Session8_Domain_Specific_Voice_Commands.ipynb)           |
| 9    | [On-Device Tiny Models (CPU)](colab_notebooks/Session9_On_Device_Tiny_Models_CPU.ipynb)                   |
| 10   | [Caching & Optimization](colab_notebooks/Session10_Caching_Optimization.ipynb)                            |
| 11   | [Mobile UI/UX Considerations](colab_notebooks/Session11_Mobile_UI_UX.ipynb)                               |
| 12   | [Meta Ray-Ban Deployment Flow](colab_notebooks/Session12_Meta_RayBan_Deployment.ipynb)                    |
| 13   | [Use Case: Healthcare](colab_notebooks/Session13_Healthcare_UseCase.ipynb)                                |
| 14   | [SNN Student Distillation & Edge Eval](ANN_Llm2SNN.ipynb)                                                  |
| 15   | [Android Integration & Client Walkthrough](SmartGlass_AI_Agent_Meta_RayBan.ipynb)                          |
| 16   | [Advanced SmartGlass Agent Orchestration](SmartGlass_AI_Agent_Advanced.ipynb)                             |
| 17   | [Action Mapping with RaySkillKit](docs/actions_and_skills.md)                                              |
| 18   | [Pitch Deck + Commercial Demo](roadmap.md)                                                                 |

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
├── colab_notebooks/    # 18-week training notebooks and end-to-end labs
├── docs/               # Architecture notes, integration guides, privacy docs
├── drivers/            # Provider implementations (see drivers/providers)
├── examples/           # Domain-specific demos and CLIs
├── rayskillkit/        # Skill registry and artifacts
├── scripts/            # Training, packaging, and utility scripts
├── sdk-android/        # Kotlin/Android SDK (stable APIs as of v1.0)
├── sdk_python/         # Python SDK facade (mirrors src/ agent APIs)
├── src/                # Core SmartGlassAgent implementation and backends
├── tests/              # Automated regression suite
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

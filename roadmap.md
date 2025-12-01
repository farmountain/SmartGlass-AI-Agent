# 🧭 SmartGlass AI Agent – 18 Week Learning Roadmap

This roadmap outlines each week's theme, goal, and hands-on workshop notebook.

| Week | Module Title                                                    | Outcome Goal |
|------|----------------------------------------------------------------|--------------|
| 1    | Foundations: SmartGlassAgent Quickstart                        | Run the core Python SDK with the mock provider (Colab: `colab_notebooks/week01_foundations.ipynb`). |
| 2    | Providers and Device Abstraction                               | Swap between mock, Meta, and Vuzix providers via `drivers.providers.get_provider`. |
| 3    | Vision + Whisper Fusion                                        | Fuse CLIP/DeepSeek-Vision with Whisper for captioned transcripts (Colab Week 3 notebook). |
| 4    | Actions and RaySkillKit Mapping                                | Emit structured `actions` and bind them to RaySkillKit skills (notification, navigation). |
| 5    | On-Device SNN Distillation (Teacher → Student)                 | Train the spiking student using the ANN→SNN Colab (`colab_notebooks/week05_snn_distillation.ipynb`). |
| 6    | SNN Inference on Glasses/Edge                                  | Deploy `SNNLLMBackend` artifacts on-device; measure latency/energy vs ANN. |
| 7    | Android Bridge and SDK Integration                             | Use `sdk-android` + `sdk_python` to stream frames/audio and invoke actions from Android. |
| 8    | Real-Time Audio Streaming and Wake Words                       | Implement chunked Whisper ingestion with wake-word gating for on-device loops. |
| 9    | OCR, Translation, and Scene Graphs                             | Extend vision to OCR + translation with actionable scene graphs. |
| 10   | Latency Reduction and Caching                                  | Apply context caches, embeddings, and prompt templates for faster responses. |
| 11   | Edge Privacy, Policies, and Safety                             | Configure `edge_runtime` privacy flags and policy modules for safe actions. |
| 12   | Provider-Specific Device Features                              | Integrate haptics/camera controls for Meta/Vuzix/XReal via provider capabilities. |
| 13   | Healthcare Assistant Scenario                                  | Build vitals/medication helper with SNN text generation and action outputs. |
| 14   | Retail Assistant Scenario                                      | Shelf/barcode assistant with offline SNN + provider-triggered notifications. |
| 15   | Travel Companion Scenario                                      | Multimodal travel Q&A with offline fallback and cached actions. |
| 16   | Security and Monitoring Scenario                               | Scene change detection with action alerts to paired devices. |
| 17   | Final Assembly: Cross-Platform SmartGlass Agent                | Package a deployable agent bundle for Python + Android with provider toggles. |
| 18   | Launch Plan, KPIs, and Monetization                            | Prepare launch docs, benchmarks, and monetization strategy for the v1.0 agent. |

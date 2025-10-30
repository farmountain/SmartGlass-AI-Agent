# TECH_DEBT (auto-generated)

- Replace GPT-2 references with student Llama-3.2-3B / Qwen-2.5-3B configs (Week 10/11 plan).
- Migrate critical notebooks to scripted workflows or ensure they are optional for CI.
- Confirm CLIP usage aligns with current vision stack; document migration path if deprecated.
- Validate Whisper models meet latency targets and document batching strategies.
- Audit DeepSeek dependencies for maintenance status and compliance risks.

## mentions_gpt2 (12)
- `PROJECT_STRUCTURE.md`
- `README.md`
- `colab_notebooks/Session10_Caching_Optimization.ipynb`
- `colab_notebooks/Session1_Multimodal_Basics.ipynb`
- `colab_notebooks/Session4_Intent_Detection_Prompt_Engineering.ipynb`
- `colab_notebooks/Session5_Meta_RayBan_SDK_Simulation.ipynb`
- `colab_notebooks/SmartGlass_AI_Agent_Advanced.ipynb`
- `colab_notebooks/SmartGlass_AI_Agent_Meta_RayBan.ipynb`
- `docs/API_REFERENCE.md`
- `docs/INVENTORY.md`
- `docs/README_MODEL_CHOICES.md`
- `docs/TECH_DEBT.md`

## is_ipynb (15)
- `colab_notebooks/Session10_Caching_Optimization.ipynb`
- `colab_notebooks/Session11_Mobile_UI_UX.ipynb`
- `colab_notebooks/Session12_Meta_RayBan_Deployment.ipynb`
- `colab_notebooks/Session13_Healthcare_UseCase.ipynb`
- `colab_notebooks/Session1_Multimodal_Basics.ipynb`
- `colab_notebooks/Session2_WakeWord_Detector_WhisperOnly.ipynb`
- `colab_notebooks/Session3_Scene_Description_CLIP.ipynb`
- `colab_notebooks/Session4_Intent_Detection_Prompt_Engineering.ipynb`
- `colab_notebooks/Session5_Meta_RayBan_SDK_Simulation.ipynb`
- `colab_notebooks/Session6_RealTime_Audio_Streaming.ipynb`
- `colab_notebooks/Session7_Visual_OCR_and_Translation.ipynb`
- `colab_notebooks/Session8_Domain_Specific_Voice_Commands.ipynb`
- `colab_notebooks/Session9_On_Device_Tiny_Models_CPU.ipynb`
- `colab_notebooks/SmartGlass_AI_Agent_Advanced.ipynb`
- `colab_notebooks/SmartGlass_AI_Agent_Meta_RayBan.ipynb`

## mentions_clip (26)
- `PROJECT_STRUCTURE.md`
- `README.md`
- `calibration/clip_calibrate.py`
- `colab_notebooks/Session10_Caching_Optimization.ipynb`
- `colab_notebooks/Session12_Meta_RayBan_Deployment.ipynb`
- `colab_notebooks/Session1_Multimodal_Basics.ipynb`
- `colab_notebooks/Session3_Scene_Description_CLIP.ipynb`
- `colab_notebooks/Session5_Meta_RayBan_SDK_Simulation.ipynb`
- `colab_notebooks/Session9_On_Device_Tiny_Models_CPU.ipynb`
- `colab_notebooks/SmartGlass_AI_Agent_Advanced.ipynb`
- `colab_notebooks/SmartGlass_AI_Agent_Meta_RayBan.ipynb`
- `config/calibration.yaml`
- `config/routes/explain_this.yaml`
- `docs/API_REFERENCE.md`
- `docs/INVENTORY.md`
- `docs/TECH_DEBT.md`
- `examples/basic_usage.py`
- `examples/vision_example.py`
- `roadmap.md`
- `scripts/inventory_repo.py`
- `setup.py`
- `src/__init__.py`
- `src/clip_vision.py`
- `src/smartglass_agent.py`
- `tests/test_ece_threshold.py`
- `tests/test_redaction.py`

## mentions_whisper (28)
- `PROJECT_STRUCTURE.md`
- `QUICKSTART.md`
- `README.md`
- `colab_notebooks/Session10_Caching_Optimization.ipynb`
- `colab_notebooks/Session12_Meta_RayBan_Deployment.ipynb`
- `colab_notebooks/Session13_Healthcare_UseCase.ipynb`
- `colab_notebooks/Session1_Multimodal_Basics.ipynb`
- `colab_notebooks/Session2_WakeWord_Detector_WhisperOnly.ipynb`
- `colab_notebooks/Session4_Intent_Detection_Prompt_Engineering.ipynb`
- `colab_notebooks/Session5_Meta_RayBan_SDK_Simulation.ipynb`
- `colab_notebooks/Session6_RealTime_Audio_Streaming.ipynb`
- `colab_notebooks/Session8_Domain_Specific_Voice_Commands.ipynb`
- `colab_notebooks/Session9_On_Device_Tiny_Models_CPU.ipynb`
- `colab_notebooks/SmartGlass_AI_Agent_Advanced.ipynb`
- `colab_notebooks/SmartGlass_AI_Agent_Meta_RayBan.ipynb`
- `docs/API_REFERENCE.md`
- `docs/INVENTORY.md`
- `docs/TECH_DEBT.md`
- `examples/basic_usage.py`
- `requirements.txt`
- `roadmap.md`
- `scripts/inventory_repo.py`
- `setup.py`
- `src/__init__.py`
- `src/audio/whisper_utils.py`
- `src/smartglass_agent.py`
- `src/whisper_processor.py`
- `tests/test_redaction.py`

## mentions_deepseek (6)
- `README.md`
- `colab_notebooks/Session1_Multimodal_Basics.ipynb`
- `docs/INVENTORY.md`
- `docs/TECH_DEBT.md`
- `roadmap.md`
- `scripts/inventory_repo.py`

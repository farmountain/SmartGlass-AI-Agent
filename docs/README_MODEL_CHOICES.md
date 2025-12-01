# Interim Language Model Choices (Week 10/11)

To align with the student deployment plan, GPT-2 based language generation
has been deprecated across the SmartGlass agent. Teams should migrate to the
pluggable backend interface and select a backend based on deployment needs:

- **Primary option (ANN):** `LLMBackend("student/llama-3.2-3b")`
- **Fallback option (ANN):** `LLMBackend("student/qwen-2.5-3b")`
- **On-device option (SNN):** `SNNLLMBackend(model_path="artifacts/snn_student/student.pt")`

## Migration guidance

1. Update any pipeline configuration that previously referenced `gpt2` or its
   larger checkpoints to pass an `llm_backend` instance into `SmartGlassAgent`.
2. Choose your backend by deployment target: SNN for edge/on-device, ANN for
   cloud or workstation inference. Provide a `device` hint if you need to pin
   execution (e.g., `cpu` on dev boards or `cuda` on desktops).
3. Let the agent resolve providers from the `PROVIDER` environment variable when
   running the same code across devices; override with `provider="meta"` or a
   concrete provider instance when necessary.
4. Remove direct imports of `src.gpt2_generator.GPT2TextGenerator`; attempts to
   instantiate it now raise a `NotImplementedError` to prevent accidental use of
   the deprecated path.

Refer back to this document for Week 10/11 updates or reach out to the platform
team if you need temporary support for legacy GPT-2 checkpoints.

# Interim Language Model Choices (Week 10/11)

To align with the student deployment plan, GPT-2 based language generation
has been deprecated across the SmartGlass agent. Teams should migrate to the
following interim configuration while we finalize the permanent upgrade:

- **Primary option:** `student/llama-3.2-3b`
- **Fallback option:** `student/qwen-2.5-3b`

## Migration guidance

1. Update any pipeline configuration that previously referenced the legacy
   GPT-2 checkpoints to use the student model identifiers above.
2. Ensure inference endpoints or local runtimes are provisioned with the
   corresponding weights and compatible tokenizers.
3. Remove direct imports of the legacy generator (`src.gpt2_generator`); attempts
   to instantiate it now raise a `NotImplementedError` to prevent accidental use
   of the deprecated path.

Refer back to this document for Week 10/11 updates or reach out to the platform
team if you need temporary support for legacy GPT-2 checkpoints.

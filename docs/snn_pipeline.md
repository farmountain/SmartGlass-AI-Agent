# Teacher–Student SNN training guide

This guide walks through running `scripts/train_snn_student.py` with a tiny transformer teacher, the artifacts it produces, and how `SNNLLMBackend` consumes them.

## Prerequisites
- Python environment with `torch` plus `transformers` for the teacher model. `datasets` is only needed for non-synthetic datasets.
- GPU is optional; the script autodetects CUDA and otherwise runs on CPU.

## Quickstart: distill a tiny GPT-2 teacher
Run a short training loop using a small, fast teacher (`sshleifer/tiny-gpt2`) and the synthetic prompt set:

```bash
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 50 \
  --batch-size 4 \
  --grad-accum-steps 2 \
  --output-dir artifacts/snn_student_demo
```

Key knobs:
- `--teacher-model`: Any Hugging Face causal LM ID or local path. Required.
- `--dataset`: `synthetic` (built-in prompts) or any `datasets`-compatible ID such as `wikitext-2`.
- `--dataset-path`: Plain-text prompts file (one prompt per line) if you prefer local data.
- `--output-dir`: Where to write artifacts (default: `artifacts/snn_student`).
- `--num-steps`, `--batch-size`, `--grad-accum-steps`, `--max-length`: Training loop controls sized for Colab-friendly runs.

During training, the teacher is kept in eval mode and only the student updates. Loss logs appear every `--log-interval` steps (default `5`).【F:scripts/train_snn_student.py†L63-L145】

## Artifact layout
After finishing the requested steps, the script writes two files under `--output-dir` (created if missing):

- `student.pt`: The student weights. Saved with `torch.save`; it may be a state dict or full `nn.Module` depending on how you load it later.【F:scripts/train_snn_student.py†L216-L236】
- `metadata.json`: A JSON blob with:
  - `model_type`: Student class name.
  - `vocab_size`: Teacher tokenizer vocabulary size.
  - `student_params`: Parameter count for the student.
  - `training_config`: Lightweight summary of key hyperparameters (steps, batch size, teacher, LR, temperature, dataset).
  - `config`: Full CLI arguments after parsing.
  - `steps` and `avg_loss`: Observed training steps and mean loss.【F:scripts/train_snn_student.py†L216-L236】

Example tree (with a custom output directory):

```
artifacts/snn_student_demo/
├── metadata.json
└── student.pt
```

## Consuming artifacts with `SNNLLMBackend`
`src/llm_snn_backend.py` provides a backend that loads the student artifacts and exposes the same interface as other LLM backends.

### Loading behavior
- Paths: It looks for `student.pt` and `metadata.json` at construction time (defaults: `artifacts/snn_student/student.pt` and `artifacts/snn_student/metadata.json`). You can point it to your run with `SNNLLMBackend(model_path="artifacts/snn_student_demo/student.pt")` and optionally `metadata_path` if you saved elsewhere.【F:src/llm_snn_backend.py†L16-L61】
- Metadata: The backend parses `metadata.json` to recover the stored `config` and tokenizer hints. If the file is missing or malformed, it proceeds with empty defaults while logging a warning.【F:src/llm_snn_backend.py†L25-L52】
- Tokenizer: It prefers the tokenizer named in metadata (`config["tokenizer_name"]`) or a user override; falls back to GPT-2. If transformers are unavailable, it falls back to a whitespace tokenizer stub.【F:src/llm_snn_backend.py†L53-L89】
- Model loading: Tries TorchScript via `torch.jit.load`; if that fails, it attempts `torch.load` to retrieve a state dict or module. Missing or un-loadable artifacts trigger a stubbed path that still returns deterministic text so demos keep running.【F:src/llm_snn_backend.py†L90-L146】

### Minimal generation example
Once your artifacts exist, instantiate the backend and generate:

```python
from src.llm_snn_backend import SNNLLMBackend

backend = SNNLLMBackend(
    model_path="artifacts/snn_student_demo/student.pt",
    metadata_path="artifacts/snn_student_demo/metadata.json",
)
print(backend.generate("Hello from the glasses", max_tokens=24))
```

If the artifacts or PyTorch are unavailable, the backend emits warnings and uses a stubbed tokenizer/model so the call still succeeds—useful for quick demos or CI environments.【F:src/llm_snn_backend.py†L90-L181】

## Exporting to ONNX
You can produce an ONNX artifact alongside the PyTorch checkpoint for deployment to lightweight runtimes:

- Add `--export-onnx` to the training command to automatically call the exporter and write `student.onnx` next to `student.pt` and `metadata.json`. The flag wraps `scripts/export_snn_to_onnx.py`, which rebuilds the `SpikingStudentLM`, loads `student.pt`, and exports with dynamic sequence length for `input_ids`/`logits`.【F:scripts/train_snn_student.py†L205-L236】【F:scripts/export_snn_to_onnx.py†L9-L48】
- Or run the exporter manually if you trained earlier:

  ```bash
  python scripts/export_snn_to_onnx.py \
    --model-path artifacts/snn_student_demo/student.pt \
    --metadata-path artifacts/snn_student_demo/metadata.json \
    --output-path artifacts/snn_student_demo/student.onnx
  ```

## Consuming ONNX on mobile
- Package `student.onnx` with your mobile client (e.g., copy into Android assets or an iOS bundle) and load it with ONNX Runtime Mobile or another ONNX-compatible runtime that supports opset 17. The exported graph expects `input_ids` shaped `[batch, seq_len]` and produces `logits` with a matching dynamic `seq_len` dimension.【F:scripts/export_snn_to_onnx.py†L9-L48】
- Reuse the tokenizer configuration from `metadata.json` to ensure the mobile client tokenizes text identically to training. The same vocab size is embedded in the ONNX export, so tokenizer/token-to-id parity is required for correct logits.【F:scripts/export_snn_to_onnx.py†L25-L39】

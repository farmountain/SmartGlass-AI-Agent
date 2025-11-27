# Android SDK model assets

The Android SDK bundles ONNX models from this directory into the library/AAR via the default Gradle asset packaging.

Because GitHub PRs discourage committing large binary artifacts, the `snn_student.onnx` model is **not** checked in. To package the model:

1. Export the student model to ONNX using the existing training pipeline (e.g. `python scripts/train_snn_student.py --export-onnx --output-dir artifacts/snn_student_demo`).
2. Copy the resulting `student.onnx` to `sdk-android/src/main/assets/models/snn_student.onnx`.
3. Build the Android SDK as usual; Gradle will include the ONNX file from `src/main/assets` automatically.

If you generate additional models for the SDK, place them in this folder so they are picked up by the asset packaging.

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import nacl.signing


def test_manifest_signature_roundtrip(tmp_path: Path, monkeypatch):
    manifest = {
        "models": [
            {"path": "model.bin", "sha256": "aa" * 32, "size": 42},
        ],
        "stats": [
            {"path": "metrics.json", "sha256": "bb" * 32, "size": 128},
        ],
    }
    manifest_path = tmp_path / "release_manifest.json"
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    manifest_path.write_bytes(manifest_bytes)

    seed = hashlib.sha256(b"manifest signature test key").digest()
    monkeypatch.setenv("TEST_SIGNING_KEY", seed.hex())

    signature_path = tmp_path / "release_manifest.sig"
    subprocess.run(
        [
            sys.executable,
            str(Path("cicd") / "sign_manifest.py"),
            "--in",
            str(manifest_path),
            "--out",
            str(signature_path),
            "--key-env",
            "TEST_SIGNING_KEY",
        ],
        check=True,
        cwd=Path.cwd(),
    )

    signature = signature_path.read_bytes()
    assert len(signature) == 64

    verify_key = nacl.signing.SigningKey(seed).verify_key
    verify_key.verify(manifest_bytes, signature)

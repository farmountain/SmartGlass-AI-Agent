"""Sign release manifests with an Ed25519 key.

The script consumes a release manifest (``release_manifest.json``) produced by
``cicd.make_manifest`` and emits a detached Ed25519 signature that is compatible
with libsodium tooling.  The manifest is treated as an opaque UTF-8 encoded JSON
document of the form::

    {
      "models": [
        {"path": "<relative path>", "sha256": "<hex digest>", "size": <int>},
        ...
      ],
      "stats": [
        {"path": "<relative path>", "sha256": "<hex digest>", "size": <int>},
        ...
      ]
    }

The signature written to ``--out`` is exactly 64 bytes of binary data containing
the detached Ed25519 signature of the manifest bytes.  The signature verifies
with the 32-byte Ed25519 public key associated with the supplied secret key
using libsodium-compatible tooling.

One of ``--key`` or ``--key-env`` must be provided. ``--key`` expects a file
containing either a 32-byte Ed25519 seed or a 64-byte libsodium secret key
(seed + public key). ``--key-env`` accepts the name of an environment variable
whose value is either a hex or base64 encoding of the same secret key bytes.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import os
from pathlib import Path
from typing import Iterable

from nacl import signing


def _decode_secret_key(value: str) -> bytes:
    """Return secret key bytes from a hex or base64 encoded string."""

    normalized = "".join(value.split())
    if not normalized:
        raise ValueError("Secret key value is empty")

    if len(normalized) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in normalized):
        try:
            return bytes.fromhex(normalized)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("Failed to decode hex secret key") from exc

    try:
        return base64.b64decode(normalized, validate=True)
    except binascii.Error as exc:
        raise ValueError("Secret key must be hex or base64 encoded") from exc


def _load_secret_key_bytes(key_path: Path | None, key_env: str | None) -> bytes:
    if bool(key_path) == bool(key_env):
        raise ValueError("Provide exactly one of --key or --key-env")

    if key_path is not None:
        return key_path.read_bytes()

    env_value = os.environ.get(key_env or "")
    if env_value is None:
        raise ValueError(f"Environment variable {key_env!r} is not set")
    return _decode_secret_key(env_value)


def _signing_key_from_secret(secret_key: bytes) -> signing.SigningKey:
    if len(secret_key) == 32:
        seed = secret_key
    elif len(secret_key) == 64:
        seed = secret_key[:32]
    else:
        raise ValueError(
            "Unsupported secret key length. Expected 32-byte seed or 64-byte libsodium secret key."
        )
    return signing.SigningKey(seed)


def sign_manifest_bytes(manifest_bytes: bytes, key: signing.SigningKey) -> bytes:
    return key.sign(manifest_bytes).signature


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="manifest", type=Path, required=True, help="Path to release manifest JSON")
    parser.add_argument("--out", dest="signature", type=Path, required=True, help="Path to write detached signature")
    parser.add_argument("--key", dest="key_path", type=Path, help="Path to Ed25519 secret key bytes")
    parser.add_argument(
        "--key-env",
        dest="key_env",
        help="Environment variable containing a hex or base64 encoded Ed25519 secret key",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    secret_key = _load_secret_key_bytes(args.key_path, args.key_env)
    signing_key = _signing_key_from_secret(secret_key)

    manifest_bytes = args.manifest.read_bytes()
    signature = sign_manifest_bytes(manifest_bytes, signing_key)

    args.signature.parent.mkdir(parents=True, exist_ok=True)
    args.signature.write_bytes(signature)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

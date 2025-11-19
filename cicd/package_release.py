"""Package RaySkillKit skills into a distributable pilot drop bundle.

The script performs the following steps:

* copies the skills model/stat directories into a staging area,
* builds a ``release_manifest.json`` using :mod:`cicd.make_manifest`,
* signs the manifest with the helpers from :mod:`cicd.sign_manifest`, and
* creates a compressed ``skills_bundle.zip`` ready for distribution.

The staging directory is safe to delete once the bundle has been published.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from cicd import make_manifest, sign_manifest


def _copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Source directory does not exist: {src}")

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _write_manifest(staged_models: Path, staged_stats: Path, output_path: Path) -> Path:
    manifest = make_manifest.build_manifest(staged_models, staged_stats)
    make_manifest.write_manifest(manifest, output_path)
    return output_path


def _sign_manifest(manifest_path: Path, signature_path: Path, key_path: Path | None, key_env: str | None) -> Path:
    secret_key = sign_manifest._load_secret_key_bytes(key_path, key_env)  # type: ignore[attr-defined]
    signing_key = sign_manifest._signing_key_from_secret(secret_key)  # type: ignore[attr-defined]
    signature = sign_manifest.sign_manifest_bytes(manifest_path.read_bytes(), signing_key)
    signature_path.write_bytes(signature)
    return signature_path


def _zip_skills(skills_root: Path, bundle_path: Path) -> Path:
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    archive_base = bundle_path.with_suffix("")
    created = shutil.make_archive(str(archive_base), "zip", root_dir=skills_root)
    return Path(created)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    default_models = repo_root / "rayskillkit" / "skills" / "models"
    default_stats = repo_root / "rayskillkit" / "skills" / "stats"
    default_staging = repo_root / "dist" / "pilot_drop"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-dir", type=Path, default=default_models, help=f"Source models directory (default: {default_models})")
    parser.add_argument("--stats-dir", type=Path, default=default_stats, help=f"Source stats directory (default: {default_stats})")
    parser.add_argument("--staging-dir", type=Path, default=default_staging, help=f"Directory to write staged artifacts (default: {default_staging})")
    parser.add_argument("--bundle-name", default="skills_bundle.zip", help="Name of the zipped skills bundle (default: skills_bundle.zip)")
    parser.add_argument("--key", dest="key_path", type=Path, help="Path to Ed25519 secret key bytes")
    parser.add_argument("--key-env", dest="key_env", help="Environment variable containing hex/base64 encoded Ed25519 key")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    staging_dir = args.staging_dir
    skills_root = staging_dir / "skills"
    staged_models = skills_root / "models"
    staged_stats = skills_root / "stats"

    skills_root.mkdir(parents=True, exist_ok=True)
    _copy_tree(args.models_dir, staged_models)
    _copy_tree(args.stats_dir, staged_stats)

    manifest_path = staging_dir / "release_manifest.json"
    signature_path = staging_dir / "release_manifest.sig"
    bundle_path = staging_dir / args.bundle_name

    _write_manifest(staged_models, staged_stats, manifest_path)
    _sign_manifest(manifest_path, signature_path, args.key_path, args.key_env)
    _zip_skills(skills_root, bundle_path)

    print(f"Skills bundle written to {bundle_path}")
    print(f"Manifest written to {manifest_path}")
    print(f"Signature written to {signature_path}")


if __name__ == "__main__":
    main()

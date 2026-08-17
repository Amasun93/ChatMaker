"""Sign one canonical ChatMaker Core release manifest in a controlled environment."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _load_verifier():
    path = Path(__file__).with_name("core_release_signature.py")
    spec = importlib.util.spec_from_file_location("chatmaker_core_release_signature_for_signing", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("release_verifier_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_VERIFIER = _load_verifier()
DOMAIN_SEPARATOR = _VERIFIER.DOMAIN_SEPARATOR
OFFICIAL_KEY_ID = _VERIFIER.OFFICIAL_KEY_ID
OFFICIAL_PUBLIC_KEY = _VERIFIER.OFFICIAL_PUBLIC_KEY
OFFICIAL_PUBLIC_KEY_FINGERPRINT = _VERIFIER.OFFICIAL_PUBLIC_KEY_FINGERPRINT


class SigningError(RuntimeError):
    """A safe release-signing contract failure."""


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sign_manifest(manifest_path: Path, private_key_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    """Sign *manifest_path* only when the private key matches the embedded anchor."""
    manifest_path = Path(manifest_path)
    private_key_path = Path(private_key_path)
    try:
        manifest_bytes = manifest_path.read_bytes()
        _VERIFIER._canonical_json_document(manifest_bytes)
        private_key = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
    except Exception as exc:
        raise SigningError("release_signing_input_invalid") from exc
    if not isinstance(private_key, Ed25519PrivateKey):
        raise SigningError("release_signing_key_invalid")
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    fingerprint = hashlib.sha256(public_key).hexdigest()
    if public_key != OFFICIAL_PUBLIC_KEY or fingerprint != OFFICIAL_PUBLIC_KEY_FINGERPRINT:
        raise SigningError("release_signing_key_mismatch")
    signature = private_key.sign(DOMAIN_SEPARATOR + manifest_bytes)
    detached = _canonical_json({
        "algorithm": "ed25519",
        "key_id": OFFICIAL_KEY_ID,
        "signature": base64.b64encode(signature).decode("ascii"),
    })
    destination = Path(output_path) if output_path is not None else manifest_path.with_suffix(manifest_path.suffix + ".sig.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(detached)
    return {
        "success": True,
        "manifest": str(manifest_path),
        "signature_file": str(destination),
        "key_id": OFFICIAL_KEY_ID,
        "public_key_fingerprint_sha256": fingerprint,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sign a canonical ChatMaker Core release manifest.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = sign_manifest(args.manifest, args.private_key, args.output)
    except Exception as exc:
        result = {"success": False, "error": type(exc).__name__, "detail": str(exc)}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]


class SigningError(Exception):
    pass


def _load_trust_store(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SigningError("trust store unavailable or invalid") from exc
    if not isinstance(value, dict) or not isinstance(value.get("keys"), list):
        raise SigningError("trust store unavailable or invalid")
    return value


def sign_registry(
    registry_path: Path,
    private_key_path: Path,
    trust_store_path: Path,
    key_id: str,
    output_path: Path,
) -> None:
    try:
        resolved_output = os.path.normcase(str(output_path.resolve()))
        resolved_inputs = {
            os.path.normcase(str(path.resolve()))
            for path in (registry_path, private_key_path, trust_store_path)
        }
    except OSError as exc:
        raise SigningError("input or output path could not be resolved") from exc
    if resolved_output in resolved_inputs:
        raise SigningError("output path must differ from every input path")
    if not private_key_path.is_file():
        raise SigningError("private key path does not exist")
    if ROOT == private_key_path.resolve() or ROOT in private_key_path.resolve().parents:
        raise SigningError("private key must remain outside the repository")
    try:
        key_value = serialization.load_pem_private_key(
            private_key_path.read_bytes(), password=None
        )
    except (OSError, ValueError, TypeError) as exc:
        raise SigningError("private key could not be loaded") from exc
    if not isinstance(key_value, Ed25519PrivateKey):
        raise SigningError("private key is not Ed25519")
    store = _load_trust_store(trust_store_path)
    anchors = [
        item
        for item in store["keys"]
        if isinstance(item, dict) and item.get("key_id") == key_id
    ]
    if len(anchors) != 1 or anchors[0].get("algorithm") != "ed25519":
        raise SigningError("key ID is not pinned")
    public_bytes = key_value.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    expected_public = anchors[0].get("public_key_base64")
    expected_fingerprint = anchors[0].get("fingerprint_sha256")
    if (
        base64.b64encode(public_bytes).decode("ascii") != expected_public
        or hashlib.sha256(public_bytes).hexdigest() != expected_fingerprint
    ):
        raise SigningError("private key does not match the checked-in anchor")
    try:
        registry_bytes = registry_path.read_bytes()
    except OSError as exc:
        raise SigningError("registry bytes could not be read") from exc
    detached = {
        "key_id": key_id,
        "algorithm": "ed25519",
        "signature": base64.b64encode(key_value.sign(registry_bytes)).decode("ascii"),
    }
    encoded = (
        json.dumps(detached, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(encoded)
    except OSError as exc:
        raise SigningError("detached signature could not be written") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sign exact registry bytes with a pinned key.")
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--trust-store", type=Path, required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        sign_registry(
            args.registry,
            args.private_key,
            args.trust_store,
            args.key_id,
            args.output,
        )
    except SigningError as exc:
        print(f"sign_registry_failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_TRUST_STORE_PATH = (
    ROOT / "runtime" / "chatmaker" / "trust" / "official_registry_keys.json"
)


class SigningError(Exception):
    pass


def _same_file(first: Path, second: Path) -> bool:
    try:
        return os.path.samefile(first, second)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise SigningError("file identity could not be verified") from exc


def _reject_output_input_collision(output_path: Path, inputs: tuple[Path, ...]) -> None:
    try:
        resolved_output = os.path.normcase(str(output_path.resolve()))
        resolved_inputs = {os.path.normcase(str(path.resolve())) for path in inputs}
    except OSError as exc:
        raise SigningError("input or output path could not be resolved") from exc
    if resolved_output in resolved_inputs:
        raise SigningError("output path must differ from every input path")
    if output_path.exists() and any(_same_file(output_path, path) for path in inputs):
        raise SigningError("output file aliases an input file")


def _atomic_write_output(output_path: Path, encoded: bytes, inputs: tuple[Path, ...]) -> None:
    temp_name: str | None = None
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        _reject_output_input_collision(output_path, inputs)
        os.replace(temp_name, output_path)
        temp_name = None
    except SigningError:
        raise
    except OSError as exc:
        raise SigningError("detached signature could not be written") from exc
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass


def _load_trust_store(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SigningError("trust store unavailable or invalid") from exc
    if not isinstance(value, dict) or not isinstance(value.get("keys"), list):
        raise SigningError("trust store unavailable or invalid")
    return value


def _registered_repository_paths(root: Path) -> set[Path]:
    try:
        worktrees = subprocess.run(
            ["git", "-C", str(root), "worktree", "list", "--porcelain"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout
        common_value = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SigningError("registered repository paths could not be verified") from exc
    paths = {root.resolve()}
    for line in worktrees.splitlines():
        if line.startswith("worktree "):
            paths.add(Path(line.removeprefix("worktree ")).resolve())
    common = Path(common_value)
    if not common.is_absolute():
        common = root / common
    paths.add(common.resolve())
    return paths


def _reject_private_key_in_repository(private_key_path: Path) -> None:
    try:
        candidate = private_key_path.resolve()
    except OSError as exc:
        raise SigningError("private key path could not be resolved") from exc
    for boundary in _registered_repository_paths(ROOT):
        if candidate == boundary or boundary in candidate.parents:
            raise SigningError(
                "private key must remain outside every registered worktree and common repository"
            )


def sign_registry(
    registry_path: Path,
    private_key_path: Path,
    trust_store_path: Path,
    key_id: str,
    output_path: Path,
) -> None:
    inputs = (registry_path, private_key_path, trust_store_path)
    _reject_output_input_collision(output_path, inputs)
    if not private_key_path.is_file():
        raise SigningError("private key path does not exist")
    _reject_private_key_in_repository(private_key_path)
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
    _atomic_write_output(output_path, encoded, inputs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sign exact registry bytes with a pinned key.")
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        sign_registry(
            args.registry,
            args.private_key,
            OFFICIAL_TRUST_STORE_PATH,
            args.key_id,
            args.output,
        )
    except SigningError as exc:
        print(f"sign_registry_failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

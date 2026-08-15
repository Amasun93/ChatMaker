"""Fail-closed verification for ChatMaker's signed knowledge-pack registry."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import stat
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

import jsonschema
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .file_lock import (
    FileLockFailure,
    UnsafeLockPath,
    exclusive_file_lock,
    is_reparse,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRUST_STORE_PATH = (
    Path(__file__).resolve().parents[1] / "trust" / "official_registry_keys.json"
)
DEFAULT_STATE_PATH = Path.home() / ".chatmaker" / "state" / "registry-sequences.json"
_REGISTRY_SCHEMA_PATH = _REPO_ROOT / "packs" / "schemas" / "registry.schema.json"
_SIGNATURE_PATTERN = re.compile(r"^[A-Za-z0-9+/]{85}[AQgw]==$")
_PACK_URL_PATTERN = re.compile(
    r"^https://raw\.githubusercontent\.com/Amasun93/ChatMaker/"
    r"[0-9a-f]{40}/distribution/packs/"
    r"chatmaker-board-(?:arduino-nano-classic|arduino-uno-r3|esp32-devkit-v1)"
    r"-wiki-[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?\.cmpack$"
)
_ALLOWED_PACK_IDS = {
    "chatmaker-board-arduino-nano-classic-wiki",
    "chatmaker-board-arduino-uno-r3-wiki",
    "chatmaker-board-esp32-devkit-v1-wiki",
}
MAX_REGISTRY_VALIDITY = timedelta(days=31)

VERIFICATION_PHASES = {
    "registry_bytes_fetched": "registry.bytes_fetched",
    "signature_verified": "registry.signature_verified",
    "archive_downloaded": "pack.after_part_write",
    "archive_hash_verified": "pack.after_archive_verify",
    "staging_extracted": "pack.after_staging_extract",
    "staging_validated": "pack.after_staging_validate",
}


class RegistryError(Exception):
    """Stable distribution error that is safe to forward to later API layers."""

    def __init__(
        self,
        code: str,
        *,
        reason: str,
        message: str | None = None,
        retryable: bool = False,
    ) -> None:
        self.code = code
        self.reason = reason
        self.retryable = retryable
        super().__init__(message or f"{code}: {reason}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "retryable": self.retryable,
            "reason": self.reason,
        }


def _parse_time(value: Any, *, field: str, code: str) -> datetime:
    if not isinstance(value, str):
        raise RegistryError(code, reason=f"invalid_{field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RegistryError(code, reason=f"invalid_{field}") from exc
    if parsed.tzinfo is None:
        raise RegistryError(code, reason=f"invalid_{field}")
    return parsed.astimezone(timezone.utc)


def _read_json_object(raw: bytes, *, code: str, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryError(code, reason=reason) from exc
    if not isinstance(value, dict):
        raise RegistryError(code, reason=reason)
    return value


def load_trust_store(path: Path | str = DEFAULT_TRUST_STORE_PATH) -> dict[str, Any]:
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise RegistryError("registry_fetch_failed", reason="trust_store_unavailable") from exc
    store = _read_json_object(
        raw,
        code="registry_fetch_failed",
        reason="trust_store_invalid",
    )
    if (
        set(store) != {"schema_version", "registry_url", "signature_url", "keys"}
        or store.get("schema_version") != "1.0"
        or not isinstance(store.get("registry_url"), str)
        or not isinstance(store.get("signature_url"), str)
        or not isinstance(store.get("keys"), list)
    ):
        raise RegistryError("registry_fetch_failed", reason="trust_store_invalid")
    return store


def _canonical_signature(signature: Any) -> bytes:
    if not isinstance(signature, str) or _SIGNATURE_PATTERN.fullmatch(signature) is None:
        raise RegistryError("registry_signature_invalid", reason="signature_encoding_invalid")
    try:
        decoded = base64.b64decode(signature, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RegistryError(
            "registry_signature_invalid", reason="signature_encoding_invalid"
        ) from exc
    if len(decoded) != 64 or base64.b64encode(decoded).decode("ascii") != signature:
        raise RegistryError("registry_signature_invalid", reason="signature_encoding_invalid")
    return decoded


def _find_key(store: Mapping[str, Any], key_id: str) -> Mapping[str, Any]:
    matches = [item for item in store["keys"] if isinstance(item, dict) and item.get("key_id") == key_id]
    if len(matches) != 1:
        raise RegistryError("registry_key_unknown", reason="key_id_not_pinned")
    return matches[0]


def _public_key(anchor: Mapping[str, Any]) -> Ed25519PublicKey:
    if anchor.get("algorithm") != "ed25519":
        raise RegistryError("registry_signature_invalid", reason="anchor_algorithm_invalid")
    try:
        public_bytes = base64.b64decode(anchor.get("public_key_base64", ""), validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise RegistryError("registry_signature_invalid", reason="anchor_invalid") from exc
    fingerprint = hashlib.sha256(public_bytes).hexdigest()
    if len(public_bytes) != 32 or fingerprint != anchor.get("fingerprint_sha256"):
        raise RegistryError("registry_signature_invalid", reason="anchor_invalid")
    try:
        return Ed25519PublicKey.from_public_bytes(public_bytes)
    except ValueError as exc:
        raise RegistryError("registry_signature_invalid", reason="anchor_invalid") from exc


def _validate_key_window(anchor: Mapping[str, Any], now: datetime) -> None:
    if anchor.get("status") != "active":
        raise RegistryError("registry_key_retired", reason="key_not_active")
    not_before = _parse_time(
        anchor.get("not_before"), field="not_before", code="registry_signature_invalid"
    )
    if now < not_before:
        raise RegistryError("registry_key_not_yet_valid", reason="key_window")
    not_after_value = anchor.get("not_after")
    if not_after_value is not None:
        not_after = _parse_time(
            not_after_value,
            field="not_after",
            code="registry_signature_invalid",
        )
        if now > not_after:
            raise RegistryError("registry_key_expired", reason="key_window")


def validate_pack_url(url: Any) -> str:
    if not isinstance(url, str) or _PACK_URL_PATTERN.fullmatch(url) is None:
        raise RegistryError("pack_content_invalid", reason="pack_url_not_commit_pinned")
    return url


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port


def validate_redirect_origin(requested_url: str, final_url: str) -> None:
    if _origin(requested_url) != _origin(final_url):
        raise RegistryError(
            "pack_redirect_origin_changed",
            reason="redirect_origin_changed",
        )


def _validate_transport_url(
    *, expected_url: Any, requested_url: Any, final_url: str | None
) -> None:
    if not isinstance(expected_url, str) or requested_url != expected_url:
        raise RegistryError("registry_fetch_failed", reason="registry_url_not_allowlisted")
    if final_url is not None and _origin(requested_url) != _origin(final_url):
        raise RegistryError("registry_fetch_failed", reason="redirect_origin_changed")


def verify_pack_download(
    pack: Mapping[str, Any],
    archive_bytes: bytes,
    *,
    final_url: str | None = None,
) -> bytes:
    try:
        requested_url = validate_pack_url(pack.get("url"))
        if final_url is not None:
            validate_redirect_origin(requested_url, final_url)
        expected_length = pack.get("length")
        expected_hash = pack.get("sha256")
        if not isinstance(archive_bytes, bytes):
            raise RegistryError("pack_download_failed", reason="archive_bytes_invalid")
        if not isinstance(expected_length, int) or len(archive_bytes) != expected_length:
            raise RegistryError("pack_size_mismatch", reason="archive_length_mismatch")
        if (
            not isinstance(expected_hash, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
            or hashlib.sha256(archive_bytes).hexdigest() != expected_hash
        ):
            raise RegistryError("pack_hash_mismatch", reason="archive_hash_mismatch")
        return archive_bytes
    except RegistryError:
        raise
    except Exception as exc:
        raise RegistryError("pack_download_failed", reason="download_validation_failed") from exc


def _load_sequence_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": "1.0", "sequences": []}
    if (
        path.is_symlink()
        or is_reparse(path)
        or not stat.S_ISREG(path.lstat().st_mode)
        or path.lstat().st_nlink != 1
    ):
        raise RegistryError("registry_fetch_failed", reason="sequence_state_unsafe")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryError("registry_fetch_failed", reason="sequence_state_invalid") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != "1.0"
        or not isinstance(value.get("sequences"), list)
    ):
        raise RegistryError("registry_fetch_failed", reason="sequence_state_invalid")
    for item in value["sequences"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"registry_url", "key_id", "highest_sequence"}
            or not isinstance(item["registry_url"], str)
            or not isinstance(item["key_id"], str)
            or not isinstance(item["highest_sequence"], int)
            or item["highest_sequence"] < 1
        ):
            raise RegistryError("registry_fetch_failed", reason="sequence_state_invalid")
    return value


def _highest_sequence(state: Mapping[str, Any], registry_url: str, key_id: str) -> int:
    matches = [
        item["highest_sequence"]
        for item in state["sequences"]
        if item["registry_url"] == registry_url and item["key_id"] == key_id
    ]
    if len(matches) > 1:
        raise RegistryError("registry_fetch_failed", reason="sequence_state_invalid")
    return matches[0] if matches else 0


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        handle = kernel32.CreateFileW(
            str(path),
            0x40000000,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,
            0x02000000,
            None,
        )
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not kernel32.FlushFileBuffers(handle):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel32.CloseHandle(handle)
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_state(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        parent_stat = path.parent.lstat()
        if (
            path.parent.is_symlink()
            or is_reparse(path.parent)
            or not stat.S_ISDIR(parent_stat.st_mode)
        ):
            raise RegistryError(
                "registry_fetch_failed", reason="sequence_state_path_unsafe"
            )
        if os.path.lexists(path):
            value = path.lstat()
            if (
                path.is_symlink()
                or is_reparse(path)
                or not stat.S_ISREG(value.st_mode)
                or value.st_nlink != 1
            ):
                raise RegistryError(
                    "registry_fetch_failed", reason="sequence_state_path_unsafe"
                )
    except RegistryError:
        raise
    except OSError as exc:
        raise RegistryError(
            "registry_fetch_failed", reason="sequence_state_path_unsafe"
        ) from exc
    encoded = (
        json.dumps(state, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
        _fsync_directory(path.parent)
    except OSError as exc:
        raise RegistryError("registry_fetch_failed", reason="sequence_state_write_failed") from exc
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass


@contextmanager
def _sequence_state_lock(state_path: Path):
    lock_path = state_path.with_name(f".{state_path.name}.lock")
    try:
        with exclusive_file_lock(lock_path):
            yield
    except UnsafeLockPath as exc:
        raise RegistryError(
            "registry_fetch_failed", reason="sequence_state_lock_unsafe"
        ) from exc
    except FileLockFailure as exc:
        raise RegistryError("registry_fetch_failed", reason="sequence_state_lock_failed") from exc


def _replace_sequence(
    state: dict[str, Any], registry_url: str, key_id: str, sequence: int
) -> dict[str, Any]:
    retained = [
        item
        for item in state["sequences"]
        if not (item["registry_url"] == registry_url and item["key_id"] == key_id)
    ]
    retained.append(
        {
            "registry_url": registry_url,
            "key_id": key_id,
            "highest_sequence": sequence,
        }
    )
    retained.sort(key=lambda item: (item["registry_url"], item["key_id"]))
    return {"schema_version": "1.0", "sequences": retained}


def _inject(
    failure_injector: Callable[[str], None] | None,
    point: str,
    *,
    code: str,
) -> None:
    if failure_injector is None:
        return
    try:
        failure_injector(point)
    except Exception as exc:
        raise RegistryError(code, reason="failure_injected") from exc


def verify_registry(
    registry_bytes: bytes,
    signature_bytes: bytes,
    *,
    registry_url: str,
    final_registry_url: str | None = None,
    signature_url: str | None = None,
    final_signature_url: str | None = None,
    trust_store: Mapping[str, Any] | None = None,
    trust_store_path: Path | str = DEFAULT_TRUST_STORE_PATH,
    state_path: Path | str = DEFAULT_STATE_PATH,
    now: datetime | None = None,
    phase_callback: Callable[[str], None] | None = None,
    failure_injector: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Verify exact bytes, validate policy, then atomically advance sequence state."""

    try:
        if not isinstance(registry_bytes, bytes) or not isinstance(signature_bytes, bytes):
            raise RegistryError("registry_fetch_failed", reason="registry_bytes_invalid")
        store = dict(trust_store) if trust_store is not None else load_trust_store(trust_store_path)
        _validate_transport_url(
            expected_url=store.get("registry_url"),
            requested_url=registry_url,
            final_url=final_registry_url,
        )
        requested_signature_url = signature_url or store.get("signature_url")
        _validate_transport_url(
            expected_url=store.get("signature_url"),
            requested_url=requested_signature_url,
            final_url=final_signature_url,
        )
        if phase_callback is not None:
            phase_callback(VERIFICATION_PHASES["registry_bytes_fetched"])

        detached = _read_json_object(
            signature_bytes,
            code="registry_signature_invalid",
            reason="detached_signature_invalid",
        )
        if set(detached) != {"key_id", "algorithm", "signature"}:
            raise RegistryError("registry_signature_invalid", reason="detached_signature_invalid")
        if detached.get("algorithm") != "ed25519" or not isinstance(detached.get("key_id"), str):
            raise RegistryError("registry_signature_invalid", reason="detached_signature_invalid")
        signature = _canonical_signature(detached.get("signature"))
        anchor = _find_key(store, detached["key_id"])
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise RegistryError("registry_fetch_failed", reason="clock_must_be_timezone_aware")
        current_time = current_time.astimezone(timezone.utc)
        _validate_key_window(anchor, current_time)
        try:
            _public_key(anchor).verify(signature, registry_bytes)
        except InvalidSignature as exc:
            raise RegistryError("registry_signature_invalid", reason="bad_signature") from exc
        if phase_callback is not None:
            phase_callback(VERIFICATION_PHASES["signature_verified"])

        value = _read_json_object(
            registry_bytes,
            code="registry_fetch_failed",
            reason="registry_json_invalid",
        )
        packs = value.get("packs")
        if isinstance(packs, list):
            for pack in packs:
                if isinstance(pack, dict) and pack.get("pack_id") not in _ALLOWED_PACK_IDS:
                    raise RegistryError("pack_not_allowlisted", reason="pack_id_not_allowlisted")
        try:
            schema = json.loads(_REGISTRY_SCHEMA_PATH.read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(
                schema, format_checker=jsonschema.FormatChecker()
            ).validate(value)
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError("registry_fetch_failed", reason="registry_schema_unavailable") from exc
        except jsonschema.ValidationError as exc:
            pack_url_error = any(
                isinstance(item, dict)
                and isinstance(item.get("url"), str)
                and _PACK_URL_PATTERN.fullmatch(item["url"]) is None
                for item in value.get("packs", [])
                if isinstance(value.get("packs"), list)
            )
            if pack_url_error:
                raise RegistryError(
                    "pack_content_invalid", reason="pack_url_not_commit_pinned"
                ) from exc
            raise RegistryError("registry_fetch_failed", reason="registry_schema_invalid") from exc

        generated_at = _parse_time(
            value["generated_at"], field="generated_at", code="registry_expired"
        )
        expires_at = _parse_time(
            value["expires_at"], field="expires_at", code="registry_expired"
        )
        if generated_at > current_time:
            raise RegistryError("registry_expired", reason="generated_at_in_future")
        if expires_at - generated_at > MAX_REGISTRY_VALIDITY:
            raise RegistryError(
                "registry_expired", reason="validity_window_too_long"
            )
        if expires_at <= current_time or expires_at <= generated_at:
            raise RegistryError("registry_expired", reason="expired")
        for pack in value["packs"]:
            validate_pack_url(pack["url"])

        state_file = Path(state_path)
        sequence = value["sequence"]
        with _sequence_state_lock(state_file):
            state = _load_sequence_state(state_file)
            if sequence <= _highest_sequence(state, registry_url, detached["key_id"]):
                raise RegistryError("registry_replay_detected", reason="sequence_not_increasing")
            new_state = _replace_sequence(state, registry_url, detached["key_id"], sequence)
            _inject(
                failure_injector,
                "registry.before_sequence_replace",
                code="registry_fetch_failed",
            )
            _atomic_write_state(state_file, new_state)
            _inject(
                failure_injector,
                "registry.after_sequence_replace",
                code="registry_fetch_failed",
            )
        return {
            "registry": value,
            "registry_url": registry_url,
            "key_id": detached["key_id"],
            "sequence": sequence,
        }
    except RegistryError:
        raise
    except Exception as exc:
        raise RegistryError("registry_fetch_failed", reason="verification_failed") from exc


__all__ = [
    "DEFAULT_STATE_PATH",
    "DEFAULT_TRUST_STORE_PATH",
    "MAX_REGISTRY_VALIDITY",
    "RegistryError",
    "VERIFICATION_PHASES",
    "load_trust_store",
    "validate_pack_url",
    "validate_redirect_origin",
    "verify_pack_download",
    "verify_registry",
]

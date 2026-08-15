"""Atomic, user-owned management for signed passive ChatMaker packs."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from .pack_artifact import (
    PackArtifactError,
    extract_validated_pack,
    validate_pack_archive,
    validate_staging,
)
from .registry import (
    DEFAULT_TRUST_STORE_PATH,
    RegistryError,
    load_trust_store,
    verify_pack_download,
    verify_registry,
)


DEFAULT_USER_ROOT = Path.home() / ".chatmaker"
DEFAULT_CORE_VERSION = "0.1.0"
ALLOWED_PACKS = {
    "chatmaker-board-arduino-nano-classic-wiki": "arduino-nano-classic",
    "chatmaker-board-arduino-uno-r3-wiki": "arduino-uno-r3",
    "chatmaker-board-esp32-devkit-v1-wiki": "esp32-devkit-v1",
}
_VERSION_PATTERN = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)(?:-(?P<pre>[0-9A-Za-z.-]+))?$"
)
_SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()
_WINDOWS_REPARSE_POINT = 0x400


@dataclass(frozen=True)
class FetchResponse:
    data: bytes
    final_url: str


class Transport(Protocol):
    def fetch(self, url: str) -> FetchResponse: ...


class UrlTransport:
    """Small production transport; policy validation remains in Task 3."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def fetch(self, url: str) -> FetchResponse:
        request = Request(url, headers={"User-Agent": "ChatMaker-pack/1"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return FetchResponse(data=response.read(), final_url=response.geturl())
        except (OSError, URLError) as exc:
            raise OSError("transport_failed") from exc


class PackManagerError(Exception):
    """Stable manager error suitable for CLI and later LLMWiki envelopes."""

    def __init__(
        self,
        code: str,
        *,
        reason: str,
        message: str | None = None,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.reason = reason
        self.retryable = retryable
        self.details = dict(details or {})
        super().__init__(message or f"{code}: {reason}")

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "message": str(self),
            "retryable": self.retryable,
            "reason": self.reason,
        }
        if self.details:
            value["details"] = dict(self.details)
        return value


@dataclass(frozen=True)
class PackPaths:
    root: Path
    overrides: Path
    cache: Path
    store: Path
    state: Path
    locks: Path
    quarantine: Path
    staging: Path
    active: Path
    registry_state: Path
    verified_registry: Path
    pending_registry: Path
    installed_metadata: Path
    manager_lock: Path

    @classmethod
    def from_root(cls, root: Path | str) -> "PackPaths":
        value = Path(root).expanduser()
        state = value / "state"
        locks = value / "locks"
        return cls(
            root=value,
            overrides=value / "overrides",
            cache=value / "cache",
            store=value / "store",
            state=state,
            locks=locks,
            quarantine=value / "quarantine",
            staging=value / "staging",
            active=state / "active.json",
            registry_state=state / "registry-sequences.json",
            verified_registry=state / "verified-registry.json",
            pending_registry=state / "pending-registry.json",
            installed_metadata=state / "installed-packs.json",
            manager_lock=locks / "pack-manager.lock",
        )


def _thread_lock(path: Path) -> threading.RLock:
    key = os.path.normcase(str(path.resolve(strict=False)))
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


@contextmanager
def _interprocess_lock(path: Path):
    local = _thread_lock(path)
    with local:
        handle = None
        locked = False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if os.path.lexists(path) and (path.is_symlink() or _is_reparse(path)):
                raise PackManagerError(
                    "pack_activation_failed", reason="manager_lock_unsafe"
                )
            flags = os.O_CREAT | os.O_RDWR
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(path, flags, 0o600)
            lock_stat = os.fstat(descriptor)
            if not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_nlink != 1:
                os.close(descriptor)
                raise PackManagerError(
                    "pack_activation_failed", reason="manager_lock_unsafe"
                )
            handle = os.fdopen(descriptor, "a+b")
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
            yield
        except PackManagerError:
            raise
        except OSError as exc:
            raise PackManagerError(
                "pack_activation_failed", reason="manager_lock_failed"
            ) from exc
        finally:
            if handle is not None:
                if locked:
                    try:
                        handle.seek(0)
                        if os.name == "nt":
                            import msvcrt

                            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            import fcntl

                            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass
                handle.close()


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


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
            0x40000000,  # GENERIC_WRITE
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,  # OPEN_EXISTING
            0x02000000,  # FILE_FLAG_BACKUP_SEMANTICS
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


def _fsync_tree(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    directories = sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for path in files:
        with path.open("r+b") as handle:
            os.fsync(handle.fileno())
    for path in (*directories, root, root.parent):
        _fsync_directory(path)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
        _fsync_directory(path.parent)
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass


def _version_key(value: str) -> tuple[Any, ...]:
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        raise PackManagerError("pack_content_invalid", reason="version_invalid")
    main = tuple(int(match.group(name)) for name in ("major", "minor", "patch"))
    raw_pre = match.group("pre")
    if raw_pre is None:
        return (*main, 1, ())
    identifiers: list[tuple[int, Any]] = []
    for item in raw_pre.split("."):
        identifiers.append((0, int(item)) if item.isdigit() else (1, item))
    return (*main, 0, tuple(identifiers))


def _is_reparse(path: Path) -> bool:
    try:
        return bool(getattr(path.lstat(), "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT)
    except FileNotFoundError:
        return False


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


class PackManager:
    """Compose Task 3 validators into one locked activation transaction."""

    def __init__(
        self,
        *,
        user_root: Path | str = DEFAULT_USER_ROOT,
        transport: Transport | None = None,
        trust_store: Mapping[str, Any] | None = None,
        trust_store_path: Path | str = DEFAULT_TRUST_STORE_PATH,
        registry_url: str | None = None,
        signature_url: str | None = None,
        core_version: str = DEFAULT_CORE_VERSION,
        now: datetime | Callable[[], datetime] | None = None,
        failure_injector: Callable[[str], None] | None = None,
        phase_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.paths = PackPaths.from_root(user_root)
        self.transport = transport or UrlTransport()
        try:
            self.trust_store = (
                dict(trust_store)
                if trust_store is not None
                else load_trust_store(trust_store_path)
            )
        except RegistryError as exc:
            raise PackManagerError(
                exc.code,
                reason=exc.reason,
                message=str(exc),
                retryable=exc.retryable,
            ) from exc
        self.registry_url = registry_url or self.trust_store["registry_url"]
        self.signature_url = signature_url or self.trust_store["signature_url"]
        self.core_version = core_version
        self.now = now
        self.failure_injector = failure_injector
        self.phase_callback = phase_callback

    @staticmethod
    def _unsafe_existing_path(path: Path, *, directory: bool) -> bool:
        if not _lexists(path):
            return False
        if path.is_symlink() or _is_reparse(path):
            return True
        try:
            value = path.lstat()
        except OSError:
            return True
        if value.st_nlink != 1 and not directory:
            return True
        return not (path.is_dir() if directory else path.is_file())

    def _assert_managed_layout(self) -> None:
        if self._unsafe_existing_path(self.paths.root, directory=True):
            raise PackManagerError(
                "pack_activation_failed", reason="managed_path_unsafe"
            )
        for path in (
            self.paths.cache,
            self.paths.store,
            self.paths.state,
            self.paths.locks,
            self.paths.quarantine,
            self.paths.staging,
        ):
            if self._unsafe_existing_path(path, directory=True):
                raise PackManagerError(
                    "pack_activation_failed", reason="managed_path_unsafe"
                )
        for path in (
            self.paths.active,
            self.paths.registry_state,
            self.paths.verified_registry,
            self.paths.pending_registry,
            self.paths.installed_metadata,
        ):
            if self._unsafe_existing_path(path, directory=False):
                raise PackManagerError(
                    "pack_activation_failed", reason="managed_path_unsafe"
                )
        if self._unsafe_existing_path(self.paths.manager_lock, directory=False):
            raise PackManagerError(
                "pack_activation_failed", reason="manager_lock_unsafe"
            )

    def _current_time(self) -> datetime:
        value = self.now() if callable(self.now) else self.now
        value = value or datetime.now(timezone.utc)
        if value.tzinfo is None:
            raise PackManagerError(
                "registry_fetch_failed", reason="clock_must_be_timezone_aware"
            )
        return value.astimezone(timezone.utc)

    @staticmethod
    def _translate(exc: BaseException) -> PackManagerError:
        if isinstance(exc, PackManagerError):
            return exc
        if isinstance(exc, RegistryError):
            return PackManagerError(
                exc.code,
                reason=exc.reason,
                message=str(exc),
                retryable=exc.retryable,
            )
        if isinstance(exc, PackArtifactError):
            details = {"path": exc.path} if exc.path is not None else None
            return PackManagerError(
                exc.code,
                reason=exc.reason,
                message=str(exc),
                details=details,
            )
        if isinstance(exc, OSError):
            return PackManagerError(
                "pack_activation_failed", reason="filesystem_operation_failed"
            )
        return PackManagerError(
            "pack_activation_failed", reason="unexpected_manager_failure"
        )

    def _inject(self, point: str) -> None:
        try:
            if self.phase_callback is not None:
                self.phase_callback(point)
            if self.failure_injector is not None:
                self.failure_injector(point)
        except Exception as exc:
            raise PackManagerError(
                "pack_activation_failed", reason="failure_injected"
            ) from exc

    @staticmethod
    def _validate_pack_id(pack_id: str) -> None:
        if pack_id not in ALLOWED_PACKS:
            raise PackManagerError(
                "pack_not_allowlisted", reason="pack_id_not_allowlisted"
            )

    def _load_active(self) -> tuple[dict[str, Any], bytes | None]:
        if not self.paths.active.exists():
            return {"schema_version": "1.0", "generation": 0, "packs": {}}, None
        try:
            raw = self.paths.active.read_bytes()
            value = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackManagerError(
                "pack_activation_failed", reason="active_state_invalid"
            ) from exc
        if (
            not isinstance(value, dict)
            or set(value) != {"schema_version", "generation", "packs"}
            or value.get("schema_version") != "1.0"
            or not isinstance(value.get("generation"), int)
            or value["generation"] < 0
            or not isinstance(value.get("packs"), dict)
        ):
            raise PackManagerError("pack_activation_failed", reason="active_state_invalid")
        for pack_id, item in value["packs"].items():
            if (
                pack_id not in ALLOWED_PACKS
                or not isinstance(item, dict)
                or set(item) != {"version", "archive_sha256"}
                or not isinstance(item.get("version"), str)
                or _VERSION_PATTERN.fullmatch(item["version"]) is None
                or not isinstance(item.get("archive_sha256"), str)
                or _SHA_PATTERN.fullmatch(item["archive_sha256"]) is None
            ):
                raise PackManagerError(
                    "pack_activation_failed", reason="active_state_invalid"
                )
        return value, raw

    def _load_installed_metadata(self) -> dict[str, Any]:
        if not self.paths.installed_metadata.exists():
            return {"schema_version": "1.0", "packs": {}}
        try:
            value = json.loads(self.paths.installed_metadata.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackManagerError(
                "pack_activation_failed", reason="installed_metadata_invalid"
            ) from exc
        if (
            not isinstance(value, dict)
            or set(value) != {"schema_version", "packs"}
            or value.get("schema_version") != "1.0"
            or not isinstance(value.get("packs"), dict)
        ):
            raise PackManagerError(
                "pack_activation_failed", reason="installed_metadata_invalid"
            )
        for pack_id, versions in value["packs"].items():
            if pack_id not in ALLOWED_PACKS or not isinstance(versions, dict):
                raise PackManagerError(
                    "pack_activation_failed", reason="installed_metadata_invalid"
                )
            for version, item in versions.items():
                if (
                    _VERSION_PATTERN.fullmatch(version) is None
                    or not isinstance(item, dict)
                    or set(item)
                    != {"archive_sha256", "manifest_sha256", "registry_receipt"}
                    or not isinstance(item["archive_sha256"], str)
                    or _SHA_PATTERN.fullmatch(item["archive_sha256"]) is None
                    or not isinstance(item["manifest_sha256"], str)
                    or _SHA_PATTERN.fullmatch(item["manifest_sha256"]) is None
                    or not isinstance(item["registry_receipt"], dict)
                ):
                    raise PackManagerError(
                        "pack_activation_failed", reason="installed_metadata_invalid"
                    )
        return value

    def _record_installed(
        self,
        pack_id: str,
        version: str,
        archive_sha256: str,
        manifest: Mapping[str, Any],
        receipt: Mapping[str, Any],
    ) -> None:
        metadata = self._load_installed_metadata()
        packs = {identity: dict(versions) for identity, versions in metadata["packs"].items()}
        versions = packs.setdefault(pack_id, {})
        manifest_sha256 = hashlib.sha256(_canonical_json(manifest)).hexdigest()
        existing = versions.get(version)
        expected = {
            "archive_sha256": archive_sha256,
            "manifest_sha256": manifest_sha256,
            "registry_receipt": dict(receipt),
        }
        if existing is not None and (
            existing.get("archive_sha256") != archive_sha256
            or existing.get("manifest_sha256") != manifest_sha256
        ):
            raise PackManagerError(
                "pack_drift_detected", reason="installed_archive_identity_changed"
            )
        versions[version] = expected
        _atomic_write(
            self.paths.installed_metadata,
            _canonical_json({"schema_version": "1.0", "packs": packs}),
        )

    def generation_token(self) -> str:
        try:
            self._assert_managed_layout()
            state, raw = self._load_active()
            payload = raw or b""
            return f"{state['generation']}:{hashlib.sha256(payload).hexdigest()}"
        except Exception as exc:
            raise self._translate(exc) from exc

    def _verify_store(
        self,
        pack_id: str,
        version: str,
        *,
        require_metadata: bool = True,
    ) -> tuple[Path, dict[str, Any]]:
        target = self.paths.store / pack_id / version
        try:
            if target.is_symlink() or _is_reparse(target):
                raise PackManagerError(
                    "pack_drift_detected", reason="immutable_store_link_or_reparse"
                )
            raw = (target / "pack-manifest.json").read_bytes()
            manifest = json.loads(raw.decode("utf-8"))
            validate_staging(target, manifest)
            if (
                manifest.get("pack_id") != pack_id
                or manifest.get("pack_version") != version
                or manifest.get("board_id") != ALLOWED_PACKS[pack_id]
                or manifest.get("pack_type") != "knowledge"
            ):
                raise PackManagerError(
                    "pack_drift_detected", reason="immutable_store_identity_mismatch"
                )
            if require_metadata:
                metadata = self._load_installed_metadata()
                installed = metadata["packs"].get(pack_id, {}).get(version)
                manifest_sha256 = hashlib.sha256(raw).hexdigest()
                if (
                    installed is None
                    or installed.get("manifest_sha256") != manifest_sha256
                ):
                    raise PackManagerError(
                        "pack_drift_detected",
                        reason="immutable_store_manifest_identity_changed",
                    )
                self._durable_installed_entry(pack_id, version, installed=installed)
            return target, manifest
        except PackManagerError:
            raise
        except (PackArtifactError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackManagerError(
                "pack_drift_detected", reason="immutable_store_drift"
            ) from exc

    def active_resource_root(self, pack_id: str) -> tuple[Path, str] | None:
        return self.resource_snapshot(pack_id)[0]

    def resource_snapshot(
        self, pack_id: str
    ) -> tuple[tuple[Path, str] | None, str]:
        try:
            self._assert_managed_layout()
            self._validate_pack_id(pack_id)
            with _interprocess_lock(self.paths.manager_lock):
                state, raw = self._load_active()
                token = (
                    f"{state['generation']}:"
                    f"{hashlib.sha256(raw or b'').hexdigest()}"
                )
                item = state["packs"].get(pack_id)
                if item is None:
                    return None, token
                root, _ = self._verify_store(pack_id, item["version"])
                evidence = self._durable_installed_entry(pack_id, item["version"])
                if item["archive_sha256"] != evidence["sha256"]:
                    raise PackManagerError(
                        "pack_drift_detected",
                        reason="active_archive_identity_changed",
                    )
                return (root, item["version"]), token
        except Exception as exc:
            raise self._translate(exc) from exc

    def _installed_versions(self, pack_id: str) -> list[str]:
        root = self.paths.store / pack_id
        try:
            versions = [
                item.name
                for item in root.iterdir()
                if item.is_dir() and _VERSION_PATTERN.fullmatch(item.name)
            ] if root.is_dir() else []
        except OSError as exc:
            raise PackManagerError(
                "pack_activation_failed", reason="store_inspection_failed"
            ) from exc
        return sorted(versions, key=_version_key)

    def _cached_manifest(self, path: Path) -> dict[str, Any]:
        return validate_pack_archive(path, core_version=self.core_version)

    def _cached_versions(self, pack_id: str) -> list[str]:
        versions: set[str] = set()
        if not self.paths.cache.is_dir():
            return []
        for path in self.paths.cache.glob("*.cmpack"):
            try:
                manifest = self._cached_manifest(path)
            except PackArtifactError:
                self._quarantine_cache(path)
                continue
            if manifest.get("pack_id") == pack_id:
                versions.add(manifest["pack_version"])
        return sorted(versions, key=_version_key)

    def status(self, pack_id: str | None = None) -> dict[str, Any]:
        try:
            self._assert_managed_layout()
            if pack_id is not None:
                self._validate_pack_id(pack_id)
            state, _ = self._load_active()
            identities = [pack_id] if pack_id is not None else sorted(ALLOWED_PACKS)
            packs: list[dict[str, Any]] = []
            for identity in identities:
                item = state["packs"].get(identity)
                if item is None:
                    continue
                record: dict[str, Any] = {
                    "pack_id": identity,
                    "version": item["version"],
                    "archive_sha256": item["archive_sha256"],
                    "verified": False,
                    "override_effective": (self.paths.overrides / identity).exists(),
                }
                try:
                    self._verify_store(identity, item["version"])
                    evidence = self._durable_installed_entry(identity, item["version"])
                    if item["archive_sha256"] != evidence["sha256"]:
                        raise PackManagerError(
                            "pack_drift_detected",
                            reason="active_archive_identity_changed",
                        )
                    record["verified"] = True
                except PackManagerError as exc:
                    record["error"] = exc.to_dict()
                packs.append(record)
            return {
                "success": True,
                "action": "status",
                "generation": state["generation"],
                "generation_token": self.generation_token(),
                "packs": packs,
            }
        except Exception as exc:
            raise self._translate(exc) from exc

    def list(self) -> dict[str, Any]:
        try:
            self._assert_managed_layout()
            installed = [
                {
                    "pack_id": pack_id,
                    "versions": self._installed_versions(pack_id),
                }
                for pack_id in sorted(ALLOWED_PACKS)
            ]
            return {
                "success": True,
                "action": "list",
                "packs": installed,
            }
        except Exception as exc:
            raise self._translate(exc) from exc

    list_packs = list

    def inspect_cache(self) -> dict[str, Any]:
        try:
            self._assert_managed_layout()
            objects: list[dict[str, Any]] = []
            if self.paths.cache.is_dir():
                for path in sorted(self.paths.cache.glob("*.cmpack")):
                    item: dict[str, Any] = {
                        "sha256": path.stem,
                        "length": path.stat().st_size,
                        "valid": False,
                    }
                    try:
                        manifest = self._cached_manifest(path)
                        item.update(
                            {
                                "valid": True,
                                "pack_id": manifest["pack_id"],
                                "version": manifest["pack_version"],
                                "receipt": path.with_suffix(".receipt.json").is_file(),
                            }
                        )
                    except PackArtifactError as exc:
                        item["error"] = exc.to_dict()
                    objects.append(item)
            partials = (
                sorted(path.name for path in self.paths.cache.glob("*.part"))
                if self.paths.cache.is_dir()
                else []
            )
            return {
                "success": True,
                "action": "cache",
                "objects": objects,
                "partials": partials,
            }
        except Exception as exc:
            raise self._translate(exc) from exc

    cache = inspect_cache

    def _fetch(self, url: str, *, code: str) -> FetchResponse:
        try:
            response = self.transport.fetch(url)
        except PackManagerError:
            raise
        except Exception as exc:
            raise PackManagerError(code, reason="transport_failed", retryable=True) from exc
        if (
            not isinstance(response, FetchResponse)
            or not isinstance(response.data, bytes)
            or not isinstance(response.final_url, str)
        ):
            raise PackManagerError(code, reason="transport_response_invalid")
        return response

    def _receipt(
        self,
        *,
        registry_bytes: bytes,
        signature_bytes: bytes,
        final_registry_url: str,
        final_signature_url: str,
        verified: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "registry_url": self.registry_url,
            "signature_url": self.signature_url,
            "final_registry_url": final_registry_url,
            "final_signature_url": final_signature_url,
            "registry_bytes_base64": base64.b64encode(registry_bytes).decode("ascii"),
            "signature_bytes_base64": base64.b64encode(signature_bytes).decode("ascii"),
            "key_id": verified["key_id"],
            "sequence": verified["sequence"],
        }

    def _candidate_receipt(
        self,
        *,
        registry_bytes: bytes,
        signature_bytes: bytes,
        final_registry_url: str,
        final_signature_url: str,
    ) -> dict[str, Any] | None:
        try:
            registry_value = json.loads(registry_bytes.decode("utf-8"))
            signature_value = json.loads(signature_bytes.decode("utf-8"))
            sequence = registry_value["sequence"]
            key_id = signature_value["key_id"]
        except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(sequence, int) or not isinstance(key_id, str):
            return None
        return {
            "schema_version": "1.0",
            "registry_url": self.registry_url,
            "signature_url": self.signature_url,
            "final_registry_url": final_registry_url,
            "final_signature_url": final_signature_url,
            "registry_bytes_base64": base64.b64encode(registry_bytes).decode("ascii"),
            "signature_bytes_base64": base64.b64encode(signature_bytes).decode("ascii"),
            "key_id": key_id,
            "sequence": sequence,
        }

    def _promote_registry_receipt(self, receipt: Mapping[str, Any]) -> None:
        _atomic_write(self.paths.verified_registry, _canonical_json(receipt))
        self.paths.pending_registry.unlink(missing_ok=True)
        _fsync_directory(self.paths.state)

    def _fetch_registry(self) -> tuple[dict[str, Any], dict[str, Any]]:
        registry_response = self._fetch(self.registry_url, code="registry_fetch_failed")
        signature_response = self._fetch(self.signature_url, code="registry_fetch_failed")
        candidate = self._candidate_receipt(
            registry_bytes=registry_response.data,
            signature_bytes=signature_response.data,
            final_registry_url=registry_response.final_url,
            final_signature_url=signature_response.final_url,
        )
        candidate_raw = _canonical_json(candidate) if candidate is not None else None
        pending_before = (
            self.paths.pending_registry.read_bytes()
            if self.paths.pending_registry.is_file()
            else None
        )
        verified_before = (
            self.paths.verified_registry.read_bytes()
            if self.paths.verified_registry.is_file()
            else None
        )
        recoverable = (
            candidate_raw is not None
            and pending_before == candidate_raw
            and verified_before != candidate_raw
        )
        verification_time = self._current_time()
        if candidate is not None and candidate_raw is not None:
            self._verify_receipt_value(
                candidate,
                verification_time=verification_time,
                require_highest=False,
            )
            if pending_before != candidate_raw:
                _atomic_write(self.paths.pending_registry, candidate_raw)
        try:
            verified = verify_registry(
                registry_response.data,
                signature_response.data,
                registry_url=self.registry_url,
                final_registry_url=registry_response.final_url,
                signature_url=self.signature_url,
                final_signature_url=signature_response.final_url,
                trust_store=self.trust_store,
                state_path=self.paths.registry_state,
                now=verification_time,
                failure_injector=self.failure_injector,
            )
        except RegistryError as exc:
            if exc.code == "registry_replay_detected" and recoverable:
                registry, receipt = self._verify_receipt(self.paths.pending_registry)
                self._promote_registry_receipt(receipt)
                return registry, receipt
            if exc.code == "registry_replay_detected" and candidate_raw is not None:
                try:
                    if self.paths.pending_registry.read_bytes() == candidate_raw:
                        if pending_before is not None and pending_before != candidate_raw:
                            _atomic_write(self.paths.pending_registry, pending_before)
                        else:
                            self.paths.pending_registry.unlink(missing_ok=True)
                            _fsync_directory(self.paths.state)
                except OSError:
                    pass
            raise
        receipt = self._receipt(
            registry_bytes=registry_response.data,
            signature_bytes=signature_response.data,
            final_registry_url=registry_response.final_url,
            final_signature_url=signature_response.final_url,
            verified=verified,
        )
        self._promote_registry_receipt(receipt)
        return verified["registry"], receipt

    @staticmethod
    def _validate_receipt_value(value: Any) -> dict[str, Any]:
        required = {
            "schema_version",
            "registry_url",
            "signature_url",
            "final_registry_url",
            "final_signature_url",
            "registry_bytes_base64",
            "signature_bytes_base64",
            "key_id",
            "sequence",
        }
        if not isinstance(value, dict) or set(value) != required or value.get("schema_version") != "1.0":
            raise PackManagerError(
                "registry_fetch_failed", reason="verified_registry_state_invalid"
            )
        return dict(value)

    @classmethod
    def _read_receipt(cls, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackManagerError(
                "registry_fetch_failed", reason="verified_registry_state_invalid"
            ) from exc
        return cls._validate_receipt_value(value)

    def _highest_sequence(self, registry_url: str, key_id: str) -> int:
        try:
            value = json.loads(self.paths.registry_state.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackManagerError(
                "registry_fetch_failed", reason="sequence_state_invalid"
            ) from exc
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != "1.0"
            or not isinstance(value.get("sequences"), list)
        ):
            raise PackManagerError("registry_fetch_failed", reason="sequence_state_invalid")
        matches = [
            item.get("highest_sequence")
            for item in value["sequences"]
            if isinstance(item, dict)
            and item.get("registry_url") == registry_url
            and item.get("key_id") == key_id
        ]
        if len(matches) != 1 or not isinstance(matches[0], int):
            raise PackManagerError("registry_fetch_failed", reason="sequence_state_invalid")
        return matches[0]

    def _verify_receipt_value(
        self,
        receipt_value: Mapping[str, Any],
        *,
        verification_time: datetime,
        require_highest: bool,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        receipt = self._validate_receipt_value(dict(receipt_value))
        try:
            registry_bytes = base64.b64decode(
                receipt["registry_bytes_base64"], validate=True
            )
            signature_bytes = base64.b64decode(
                receipt["signature_bytes_base64"], validate=True
            )
        except (ValueError, TypeError) as exc:
            raise PackManagerError(
                "registry_fetch_failed", reason="verified_registry_state_invalid"
            ) from exc
        with tempfile.TemporaryDirectory() as temp:
            verified = verify_registry(
                registry_bytes,
                signature_bytes,
                registry_url=receipt["registry_url"],
                final_registry_url=receipt["final_registry_url"],
                signature_url=receipt["signature_url"],
                final_signature_url=receipt["final_signature_url"],
                trust_store=self.trust_store,
                state_path=Path(temp) / "sequence.json",
                now=verification_time,
            )
        if (
            verified["key_id"] != receipt["key_id"]
            or verified["sequence"] != receipt["sequence"]
        ):
            raise PackManagerError(
                "registry_fetch_failed", reason="verified_registry_state_invalid"
            )
        if require_highest:
            highest = self._highest_sequence(receipt["registry_url"], receipt["key_id"])
            if highest != receipt["sequence"]:
                raise PackManagerError(
                    "registry_replay_detected", reason="verified_metadata_stale"
                )
        return verified["registry"], receipt

    def _verify_receipt(self, path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._verify_receipt_value(
            self._read_receipt(path),
            verification_time=self._current_time(),
            require_highest=True,
        )

    @staticmethod
    def _select_entry(
        registry: Mapping[str, Any], pack_id: str, version: str | None
    ) -> dict[str, Any]:
        matches = [
            item
            for item in registry["packs"]
            if item.get("pack_id") == pack_id
            and (version is None or item.get("version") == version)
        ]
        if len(matches) != 1:
            raise PackManagerError(
                "pack_not_allowlisted", reason="pack_version_not_in_registry"
            )
        return dict(matches[0])

    def _durable_installed_entry(
        self,
        pack_id: str,
        version: str,
        *,
        installed: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            if installed is None:
                metadata = self._load_installed_metadata()
                installed = metadata["packs"].get(pack_id, {}).get(version)
            if not isinstance(installed, Mapping):
                raise PackManagerError(
                    "pack_drift_detected", reason="installed_receipt_missing"
                )
            receipt = self._validate_receipt_value(installed.get("registry_receipt"))
            registry_bytes = base64.b64decode(
                receipt["registry_bytes_base64"], validate=True
            )
            registry_value = json.loads(registry_bytes.decode("utf-8"))
            generated_at = registry_value.get("generated_at")
            if not isinstance(generated_at, str):
                raise ValueError("generated_at missing")
            verification_time = datetime.fromisoformat(
                generated_at.replace("Z", "+00:00")
            )
            if verification_time.tzinfo is None:
                raise ValueError("generated_at must be timezone aware")
            try:
                registry, _ = self._verify_receipt_value(
                    receipt,
                    verification_time=self._current_time(),
                    require_highest=False,
                )
            except RegistryError as exc:
                if exc.code != "registry_expired" or exc.reason != "expired":
                    raise
                registry, _ = self._verify_receipt_value(
                    receipt,
                    verification_time=verification_time.astimezone(timezone.utc),
                    require_highest=False,
                )
            entry = self._select_entry(registry, pack_id, version)
            if entry["sha256"] != installed.get("archive_sha256"):
                raise PackManagerError(
                    "pack_drift_detected",
                    reason="installed_archive_identity_changed",
                )
            return entry
        except PackManagerError as exc:
            if exc.code == "pack_drift_detected":
                raise
            raise PackManagerError(
                "pack_drift_detected", reason="installed_receipt_invalid"
            ) from exc
        except (RegistryError, ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackManagerError(
                "pack_drift_detected", reason="installed_receipt_invalid"
            ) from exc

    def _resume_entry(
        self, pack_id: str, version: str | None
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        if not self.paths.verified_registry.is_file():
            return None
        try:
            registry, receipt = self._verify_receipt(self.paths.verified_registry)
            return self._select_entry(registry, pack_id, version), receipt
        except (PackManagerError, RegistryError):
            return None

    def _validate_entry_compatibility(self, entry: Mapping[str, Any]) -> None:
        compatibility = entry["compatibility"]
        core = _version_key(self.core_version)
        minimum = _version_key(compatibility["core"]["minimum"])
        maximum = _version_key(compatibility["core"]["maximum_exclusive"])
        if not minimum <= core < maximum:
            raise PackManagerError("pack_incompatible", reason="core_version_out_of_range")
        if "1.0" not in compatibility["pack_manifest_schema"]:
            raise PackManagerError("pack_incompatible", reason="manifest_schema_unsupported")
        if "1.0" not in compatibility["llmwiki_index_schema"]:
            raise PackManagerError("pack_incompatible", reason="llmwiki_schema_unsupported")

    @staticmethod
    def _match_manifest(entry: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
        if (
            manifest.get("pack_id") != entry.get("pack_id")
            or manifest.get("pack_version") != entry.get("version")
            or manifest.get("pack_type") != entry.get("pack_type")
            or manifest.get("board_id") != entry.get("board_id")
            or manifest.get("compatibility", {}).get("core")
            != entry.get("compatibility", {}).get("core")
            or manifest.get("compatibility", {}).get("llmwiki_index_schema")
            != entry.get("compatibility", {}).get("llmwiki_index_schema")
        ):
            raise PackManagerError(
                "pack_content_invalid", reason="registry_manifest_mismatch"
            )

    def _cache_receipt_path(self, sha256: str) -> Path:
        return self.paths.cache / f"{sha256}.receipt.json"

    def _refresh_cache_receipt(
        self, entry: Mapping[str, Any], receipt: Mapping[str, Any]
    ) -> None:
        cache_path = self.paths.cache / f"{entry['sha256']}.cmpack"
        if not cache_path.is_file():
            return
        data = cache_path.read_bytes()
        verify_pack_download(entry, data)
        manifest = validate_pack_archive(data, core_version=self.core_version)
        self._match_manifest(entry, manifest)
        _atomic_write(
            self._cache_receipt_path(entry["sha256"]),
            _canonical_json(receipt),
        )

    def _archive_for_entry(
        self,
        entry: Mapping[str, Any],
        receipt: Mapping[str, Any],
        *,
        offline: bool,
    ) -> tuple[bytes, str]:
        digest = entry["sha256"]
        cache_path = self.paths.cache / f"{digest}.cmpack"
        receipt_path = self._cache_receipt_path(digest)
        if cache_path.is_file():
            data = cache_path.read_bytes()
            verify_pack_download(entry, data)
            manifest = validate_pack_archive(data, core_version=self.core_version)
            self._match_manifest(entry, manifest)
            _atomic_write(receipt_path, _canonical_json(receipt))
            return data, "cache"
        if offline:
            raise PackManagerError(
                "offline_pack_unavailable", reason="exact_cache_object_missing"
            )

        response = self._fetch(entry["url"], code="pack_download_failed")
        self.paths.cache.mkdir(parents=True, exist_ok=True)
        part_path = self.paths.cache / f"{digest}.cmpack.part"
        try:
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(part_path, flags, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(response.data)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise PackManagerError(
                "pack_download_failed", reason="part_write_failed", retryable=True
            ) from exc
        self._inject("pack.after_part_write")
        try:
            part_bytes = part_path.read_bytes()
        except OSError as exc:
            raise PackManagerError(
                "pack_download_failed", reason="part_read_failed", retryable=True
            ) from exc
        data = verify_pack_download(entry, part_bytes, final_url=response.final_url)
        manifest = validate_pack_archive(data, core_version=self.core_version)
        self._match_manifest(entry, manifest)
        self._inject("pack.after_archive_verify")
        os.replace(part_path, cache_path)
        _fsync_directory(self.paths.cache)
        _atomic_write(receipt_path, _canonical_json(receipt))
        return data, "download"

    def _quarantine(self, pack_id: str, version: str) -> None:
        target = self.paths.store / pack_id / version
        if not _lexists(target):
            return
        destination_root = self.paths.quarantine / pack_id
        destination_root.mkdir(parents=True, exist_ok=True)
        destination = destination_root / f"{version}-{uuid.uuid4().hex}"
        try:
            os.replace(target, destination)
            _fsync_directory(destination_root)
        except OSError as exc:
            raise PackManagerError(
                "pack_drift_detected", reason="quarantine_failed"
            ) from exc

    def _quarantine_cache(self, archive: Path) -> None:
        if not _lexists(archive):
            return
        destination_root = self.paths.quarantine / "cache"
        destination_root.mkdir(parents=True, exist_ok=True)
        suffix = uuid.uuid4().hex
        destination = destination_root / f"{archive.name}-{suffix}"
        receipt = archive.with_suffix(".receipt.json")
        try:
            os.replace(archive, destination)
            if _lexists(receipt):
                os.replace(
                    receipt,
                    destination_root / f"{receipt.name}-{suffix}",
                )
            _fsync_directory(destination_root)
        except OSError as exc:
            raise PackManagerError(
                "pack_activation_failed", reason="cache_quarantine_failed"
            ) from exc

    def _restore_active(self, old_raw: bytes | None) -> None:
        if old_raw is None:
            try:
                self.paths.active.unlink(missing_ok=True)
                if self.paths.active.parent.exists():
                    _fsync_directory(self.paths.active.parent)
            except OSError as exc:
                raise PackManagerError(
                    "pack_activation_failed", reason="active_compensation_failed"
                ) from exc
            return
        try:
            _atomic_write(self.paths.active, old_raw)
        except OSError as exc:
            raise PackManagerError(
                "pack_activation_failed", reason="active_compensation_failed"
            ) from exc

    def _activate(self, pack_id: str, version: str, archive_sha256: str) -> None:
        _fsync_tree(self.paths.store / pack_id / version)
        _fsync_directory(self.paths.store)
        _fsync_directory(self.paths.root)
        state, old_raw = self._load_active()
        new_state = {
            "schema_version": "1.0",
            "generation": state["generation"] + 1,
            "packs": dict(state["packs"]),
        }
        new_state["packs"][pack_id] = {
            "version": version,
            "archive_sha256": archive_sha256,
        }
        new_raw = _canonical_json(new_state)
        self._inject("pack.before_active_replace")
        try:
            _atomic_write(self.paths.active, new_raw)
            self._inject("pack.after_active_replace")
        except PackManagerError:
            self._restore_active(old_raw)
            raise
        except OSError as exc:
            self._restore_active(old_raw)
            raise PackManagerError(
                "pack_activation_failed", reason="active_state_write_failed"
            ) from exc

    def _install_entry(
        self,
        entry: Mapping[str, Any],
        receipt: Mapping[str, Any],
        *,
        offline: bool,
    ) -> dict[str, Any]:
        self._validate_entry_compatibility(entry)
        pack_id = entry["pack_id"]
        version = entry["version"]
        target = self.paths.store / pack_id / version
        if _lexists(target):
            try:
                _, installed_manifest = self._verify_store(pack_id, version)
                self._record_installed(
                    pack_id,
                    version,
                    entry["sha256"],
                    installed_manifest,
                    receipt,
                )
                self._activate(pack_id, version, entry["sha256"])
                return {
                    "success": True,
                    "action": "ensure",
                    "pack_id": pack_id,
                    "version": version,
                    "changed": True,
                    "source": "store",
                }
            except PackManagerError as exc:
                if exc.code != "pack_drift_detected":
                    raise
                self._quarantine(pack_id, version)

        archive_bytes, source = self._archive_for_entry(entry, receipt, offline=offline)
        self.paths.staging.mkdir(parents=True, exist_ok=True)
        staging = self.paths.staging / f"{pack_id}-{version}-{uuid.uuid4().hex}"
        manifest = extract_validated_pack(
            archive_bytes,
            staging,
            core_version=self.core_version,
        )
        self._match_manifest(entry, manifest)
        self._inject("pack.after_staging_extract")
        validate_staging(staging, manifest)
        self._inject("pack.after_staging_validate")
        target.parent.mkdir(parents=True, exist_ok=True)
        if _lexists(target):
            try:
                self._verify_store(pack_id, version)
                shutil.rmtree(staging)
            except PackManagerError as exc:
                if exc.code != "pack_drift_detected":
                    raise
                self._quarantine(pack_id, version)
                os.replace(staging, target)
        else:
            os.replace(staging, target)
        _fsync_directory(target.parent)
        self._inject("pack.after_store_move")
        _, installed_manifest = self._verify_store(
            pack_id, version, require_metadata=False
        )
        self._match_manifest(entry, installed_manifest)
        self._record_installed(
            pack_id,
            version,
            entry["sha256"],
            installed_manifest,
            receipt,
        )
        self._verify_store(pack_id, version)
        self._activate(pack_id, version, entry["sha256"])
        return {
            "success": True,
            "action": "ensure",
            "pack_id": pack_id,
            "version": version,
            "changed": True,
            "source": source,
        }

    def _remove_inactive(self, path: Path) -> None:
        if path.is_symlink() or _is_reparse(path):
            try:
                path.unlink()
            except IsADirectoryError:
                os.rmdir(path)
            return
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)

    def _recover(self) -> None:
        if self.paths.cache.is_dir():
            for path in self.paths.cache.glob("*.part"):
                self._remove_inactive(path)
        if self.paths.staging.is_dir():
            for path in self.paths.staging.iterdir():
                self._remove_inactive(path)

    def _installed_exact(self, pack_id: str, version: str) -> bool:
        target = self.paths.store / pack_id / version
        if not _lexists(target):
            return False
        try:
            self._verify_store(pack_id, version)
            return True
        except PackManagerError as exc:
            if exc.code != "pack_drift_detected":
                raise
            self._quarantine(pack_id, version)
            return False

    def _cache_entry(
        self, pack_id: str, version: str
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        first_error: PackManagerError | RegistryError | None = None
        if not self.paths.cache.is_dir():
            return None
        for archive in self.paths.cache.glob("*.cmpack"):
            try:
                manifest = self._cached_manifest(archive)
            except PackArtifactError:
                self._quarantine_cache(archive)
                continue
            try:
                if (
                    manifest.get("pack_id") != pack_id
                    or manifest.get("pack_version") != version
                ):
                    continue
                receipt_path = archive.with_suffix(".receipt.json")
                registry, receipt = self._verify_receipt(receipt_path)
                entry = self._select_entry(registry, pack_id, version)
                if entry["sha256"] != archive.stem:
                    raise PackManagerError(
                        "pack_hash_mismatch", reason="cache_identity_mismatch"
                    )
                verify_pack_download(entry, archive.read_bytes())
                self._match_manifest(entry, manifest)
                return entry, receipt
            except (PackManagerError, RegistryError) as exc:
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error
        return None

    def _offline_missing(self, pack_id: str) -> PackManagerError:
        return PackManagerError(
            "offline_pack_unavailable",
            reason="exact_pack_unavailable_offline",
            retryable=False,
            details={
                "cached_versions": self._cached_versions(pack_id),
                "installed_versions": self._installed_versions(pack_id),
            },
        )

    def _ensure_locked(
        self, pack_id: str, *, version: str | None, offline: bool
    ) -> dict[str, Any]:
        state, _ = self._load_active()
        active = state["packs"].get(pack_id)
        floor_version = active["version"] if active is not None else None
        if (
            active is not None
            and version is not None
            and _version_key(version) < _version_key(active["version"])
        ):
            raise PackManagerError(
                "pack_activation_failed", reason="ensure_would_downgrade"
            )
        if active is not None and (version is None or active["version"] == version):
            try:
                self._verify_store(pack_id, active["version"])
                return {
                    "success": True,
                    "action": "ensure",
                    "pack_id": pack_id,
                    "version": active["version"],
                    "changed": False,
                    "source": "active",
                }
            except PackManagerError as exc:
                if exc.code != "pack_drift_detected":
                    raise
                self._quarantine(pack_id, active["version"])

        self._recover()
        if version is not None and self._installed_exact(pack_id, version):
            digest = self._archive_sha_for_version(pack_id, version)
            self._activate(pack_id, version, digest)
            return {
                "success": True,
                "action": "ensure",
                "pack_id": pack_id,
                "version": version,
                "changed": True,
                "source": "store",
            }

        if offline:
            target_version = version
            if target_version is None:
                installed = self._installed_versions(pack_id)
                if installed:
                    target_version = installed[-1]
                else:
                    cached = self._cached_versions(pack_id)
                    target_version = cached[-1] if cached else None
            if target_version is None:
                raise self._offline_missing(pack_id)
            if (
                floor_version is not None
                and _version_key(target_version) < _version_key(floor_version)
            ):
                raise PackManagerError(
                    "pack_activation_failed", reason="ensure_would_downgrade"
                )
            cached_entry = self._cache_entry(pack_id, target_version)
            if cached_entry is None:
                raise self._offline_missing(pack_id)
            entry, receipt = cached_entry
            return self._install_entry(entry, receipt, offline=True)

        resumed = self._resume_entry(pack_id, version)
        if resumed is None:
            registry, receipt = self._fetch_registry()
            entry = self._select_entry(registry, pack_id, version)
        else:
            entry, receipt = resumed
        if (
            floor_version is not None
            and _version_key(entry["version"]) < _version_key(floor_version)
        ):
            raise PackManagerError(
                "pack_activation_failed", reason="ensure_would_downgrade"
            )
        return self._install_entry(entry, receipt, offline=False)

    def ensure(
        self, pack_id: str, *, version: str | None = None, offline: bool = False
    ) -> dict[str, Any]:
        try:
            self._validate_pack_id(pack_id)
            if version is not None:
                _version_key(version)
            self._assert_managed_layout()
            with _interprocess_lock(self.paths.manager_lock):
                return self._ensure_locked(pack_id, version=version, offline=offline)
        except Exception as exc:
            raise self._translate(exc) from exc

    def _archive_sha_for_version(self, pack_id: str, version: str) -> str:
        return self._durable_installed_entry(pack_id, version)["sha256"]

    def update(self, pack_id: str) -> dict[str, Any]:
        try:
            self._validate_pack_id(pack_id)
            self._assert_managed_layout()
            with _interprocess_lock(self.paths.manager_lock):
                self._recover()
                state, _ = self._load_active()
                active = state["packs"].get(pack_id)
                floor_version = active["version"] if active is not None else None
                active_manifest: dict[str, Any] | None = None
                if active is not None:
                    try:
                        _, active_manifest = self._verify_store(
                            pack_id, active["version"]
                        )
                    except PackManagerError as exc:
                        if exc.code != "pack_drift_detected":
                            raise
                        self._quarantine(pack_id, active["version"])
                        active = None
                resumed = self._resume_entry(pack_id, None)
                if resumed is not None:
                    resumed_entry, resumed_receipt = resumed
                    if (
                        floor_version is not None
                        and _version_key(resumed_entry["version"])
                        < _version_key(floor_version)
                    ):
                        raise PackManagerError(
                            "pack_activation_failed", reason="update_would_downgrade"
                        )
                    if active is None or _version_key(resumed_entry["version"]) > _version_key(
                        active["version"]
                    ):
                        result = self._install_entry(
                            resumed_entry, resumed_receipt, offline=False
                        )
                        result["action"] = "update"
                        return result
                registry, receipt = self._fetch_registry()
                entry = self._select_entry(registry, pack_id, None)
                if (
                    floor_version is not None
                    and _version_key(entry["version"]) < _version_key(floor_version)
                ):
                    raise PackManagerError(
                        "pack_activation_failed", reason="update_would_downgrade"
                    )
                if active is not None:
                    current_key = _version_key(active["version"])
                    target_key = _version_key(entry["version"])
                    if target_key < current_key:
                        raise PackManagerError(
                            "pack_activation_failed", reason="update_would_downgrade"
                        )
                    if target_key == current_key:
                        if active_manifest is None:
                            raise PackManagerError(
                                "pack_drift_detected",
                                reason="active_manifest_missing",
                            )
                        self._refresh_cache_receipt(entry, receipt)
                        self._record_installed(
                            pack_id,
                            active["version"],
                            entry["sha256"],
                            active_manifest,
                            receipt,
                        )
                        return {
                            "success": True,
                            "action": "update",
                            "pack_id": pack_id,
                            "version": active["version"],
                            "changed": False,
                            "source": "active",
                        }
                result = self._install_entry(entry, receipt, offline=False)
                result["action"] = "update"
                return result
        except Exception as exc:
            raise self._translate(exc) from exc

    def rollback(self, pack_id: str, *, version: str | None = None) -> dict[str, Any]:
        try:
            self._validate_pack_id(pack_id)
            if version is not None:
                _version_key(version)
            self._assert_managed_layout()
            with _interprocess_lock(self.paths.manager_lock):
                self._recover()
                state, _ = self._load_active()
                active = state["packs"].get(pack_id)
                if active is None:
                    raise PackManagerError(
                        "pack_activation_failed", reason="rollback_without_active_version"
                    )
                self._verify_store(pack_id, active["version"])
                installed = self._installed_versions(pack_id)
                older = [
                    item
                    for item in installed
                    if _version_key(item) < _version_key(active["version"])
                ]
                target_version = version or (older[-1] if older else None)
                if (
                    target_version is None
                    or target_version not in older
                ):
                    raise PackManagerError(
                        "pack_activation_failed", reason="rollback_target_unavailable"
                    )
                self._verify_store(pack_id, target_version)
                digest = self._archive_sha_for_version(pack_id, target_version)
                self._activate(pack_id, target_version, digest)
                return {
                    "success": True,
                    "action": "rollback",
                    "pack_id": pack_id,
                    "version": target_version,
                    "changed": True,
                    "source": "store",
                }
        except Exception as exc:
            raise self._translate(exc) from exc


__all__ = [
    "ALLOWED_PACKS",
    "DEFAULT_CORE_VERSION",
    "DEFAULT_USER_ROOT",
    "FetchResponse",
    "PackManager",
    "PackManagerError",
    "PackPaths",
    "Transport",
    "UrlTransport",
]

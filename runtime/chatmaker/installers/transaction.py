"""Locked, journaled, reversible installation transactions.

The transaction owns only the content declared in its changes.  A Skill is
owned as one directory; an MCP registration is owned as one key inside
``mcpServers``.  Full before-images remain available for explicit disaster
restore, while normal uninstall edits only those managed units.

Durability requires local filesystems with atomic same-directory replacement
and directory sync. Windows UNC and mapped network drives are rejected up
front; a POSIX filesystem that cannot honor rename/fsync fails the transaction
and is compensated rather than being treated as installed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import time
from typing import Any
import uuid

from .file_lock import exclusive_file_lock, is_reparse
from . import knowledge_state_migration as _safe_fs
from .knowledge_state_migration import _fsync_directory as _reviewed_fsync_directory


FailureInjector = Callable[[str, Mapping[str, Any]], None]
_MISSING_HASH = hashlib.sha256(b"chatmaker:missing:v1").hexdigest()
_TRANSACTION_ID_LENGTH = 32


class UnsafeInstallPath(OSError):
    """A transaction path could escape or redirect a managed write."""


class InstallConflict(RuntimeError):
    """Managed content changed after ChatMaker installed it."""


@dataclass(frozen=True)
class TransactionResult(Mapping[str, Any]):
    success: bool
    status: str
    transaction_id: str | None = None
    managed_hash: str | None = None
    changes: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    conflicts: tuple[dict[str, Any], ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = {
            "success": self.success,
            "status": self.status,
            "transaction_id": self.transaction_id,
            "managed_hash": self.managed_hash,
            "changes": list(self.changes),
            "unchanged": list(self.unchanged),
            "conflicts": [dict(item) for item in self.conflicts],
        }
        value.update(dict(self.details))
        return value

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())


@dataclass(frozen=True)
class _Change:
    kind: str
    identity: str
    target: Path
    name: str | None = None
    source: Path | None = None
    server_key: str | None = None
    server: Mapping[str, Any] | None = None


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _json_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _windows_long_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    existing = path
    suffix: list[str] = []
    while not _lexists(existing) and existing.parent != existing:
        suffix.append(existing.name)
        existing = existing.parent
    if not _lexists(existing):
        return path
    size = 32768
    buffer = ctypes.create_unicode_buffer(size)
    written = ctypes.windll.kernel32.GetLongPathNameW(str(existing), buffer, size)
    expanded = Path(buffer.value) if written and written < size else existing
    for part in reversed(suffix):
        expanded /= part
    return expanded


def _reject_windows_network_path(value: str, path: Path) -> None:
    if os.name != "nt":
        return
    lowered = value.lower()
    if lowered.startswith("\\\\?\\unc\\") or lowered.startswith("\\\\"):
        raise UnsafeInstallPath("UNC and network install paths are unsupported")
    drive = path.drive
    if drive:
        root = drive + "\\"
        if ctypes.windll.kernel32.GetDriveTypeW(root) == 4:
            raise UnsafeInstallPath("network install paths are unsupported")


def _absolute(path: Path | str) -> Path:
    candidate = Path(path).expanduser()
    raw = str(candidate)
    if os.name == "nt":
        if raw.lower().startswith("\\\\?\\unc\\"):
            raise UnsafeInstallPath("UNC and network install paths are unsupported")
        if raw.startswith("\\\\?\\"):
            raw = raw[4:]
            candidate = Path(raw)
        _reject_windows_network_path(raw, candidate)
    if not candidate.is_absolute():
        raise UnsafeInstallPath(f"install path must be absolute: {candidate}")
    absolute = Path(os.path.abspath(candidate))
    if os.name == "nt":
        absolute = _windows_long_path(absolute)
        absolute = Path(os.path.normcase(str(absolute)))
    return absolute


def canonical_install_path(path: Path | str) -> Path:
    """Return one local, absolute identity for a public install path."""
    return _absolute(path)


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _unsafe_link(path: Path) -> bool:
    return path.is_symlink() or is_reparse(path)


def _assert_safe_ancestors(path: Path, *, include_final: bool = True) -> None:
    absolute = _absolute(path)
    candidates = (absolute, *absolute.parents) if include_final else absolute.parents
    for candidate in candidates:
        if not _lexists(candidate):
            continue
        if _unsafe_link(candidate):
            raise UnsafeInstallPath(f"symlink or reparse path is not allowed: {candidate}")
        try:
            value = candidate.lstat()
        except OSError as exc:
            raise UnsafeInstallPath(f"install path is unreadable: {candidate}") from exc
        if candidate == absolute and stat.S_ISREG(value.st_mode) and value.st_nlink != 1:
            raise UnsafeInstallPath(f"hard-linked install file is not allowed: {candidate}")


def _assert_safe_tree(path: Path) -> None:
    _assert_safe_ancestors(path)
    if not path.is_dir():
        raise UnsafeInstallPath(f"Skill directory is missing: {path}")
    for current, directories, files in os.walk(path, followlinks=False):
        root = Path(current)
        if _unsafe_link(root):
            raise UnsafeInstallPath(f"linked Skill directory is not allowed: {root}")
        for entry in (*directories, *files):
            item = root / entry
            if _unsafe_link(item):
                raise UnsafeInstallPath(f"linked Skill content is not allowed: {item}")
            value = item.lstat()
            if not (stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode)):
                raise UnsafeInstallPath(f"special Skill content is not allowed: {item}")
            if stat.S_ISREG(value.st_mode) and value.st_nlink != 1:
                raise UnsafeInstallPath(f"hard-linked Skill content is not allowed: {item}")


def _ensure_safe_directory(path: Path) -> None:
    path = _absolute(path)
    if os.name != "nt":
        descriptor = _safe_fs._open_posix_directory(
            path,
            root=Path(path.anchor),
            create=True,
        )
        os.close(descriptor)
        return
    for directory in reversed((path, *path.parents)):
        if _lexists(directory):
            _assert_safe_ancestors(directory)
            if not directory.is_dir():
                raise UnsafeInstallPath(f"install parent is not a directory: {directory}")
            continue
        try:
            directory.mkdir()
        except FileExistsError:
            pass
        _assert_safe_ancestors(directory)
        if not directory.is_dir():
            raise UnsafeInstallPath(f"install parent is not a directory: {directory}")


def _posix_directory_flags() -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _posix_remove_entry(directory: int, name: str) -> None:
    try:
        value = os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISREG(value.st_mode):
        if value.st_nlink != 1:
            raise UnsafeInstallPath(f"refusing to remove hard-linked file: {name}")
        os.unlink(name, dir_fd=directory)
        return
    if not stat.S_ISDIR(value.st_mode):
        raise UnsafeInstallPath(f"refusing to remove linked or special path: {name}")
    child = os.open(name, _posix_directory_flags(), dir_fd=directory)
    try:
        opened = os.fstat(child)
        if (value.st_dev, value.st_ino) != (opened.st_dev, opened.st_ino):
            raise UnsafeInstallPath(f"directory identity changed before removal: {name}")
        with os.scandir(child) as entries:
            names = sorted(entry.name for entry in entries)
        for entry_name in names:
            _posix_remove_entry(child, entry_name)
        os.fsync(child)
    finally:
        os.close(child)
    os.rmdir(name, dir_fd=directory)


def _posix_copy_entry(
    source_directory: int,
    source_name: str,
    target_directory: int,
    target_name: str,
) -> None:
    source_value = os.stat(
        source_name,
        dir_fd=source_directory,
        follow_symlinks=False,
    )
    if stat.S_ISDIR(source_value.st_mode):
        os.mkdir(target_name, 0o700, dir_fd=target_directory)
        source_child = os.open(
            source_name,
            _posix_directory_flags(),
            dir_fd=source_directory,
        )
        target_child = os.open(
            target_name,
            _posix_directory_flags(),
            dir_fd=target_directory,
        )
        try:
            opened = os.fstat(source_child)
            if (source_value.st_dev, source_value.st_ino) != (
                opened.st_dev,
                opened.st_ino,
            ):
                raise UnsafeInstallPath(
                    f"source directory identity changed during copy: {source_name}"
                )
            with os.scandir(source_child) as entries:
                names = sorted(entry.name for entry in entries)
            for entry_name in names:
                _posix_copy_entry(
                    source_child,
                    entry_name,
                    target_child,
                    entry_name,
                )
            os.fchmod(target_child, stat.S_IMODE(source_value.st_mode))
            os.fsync(target_child)
        finally:
            os.close(target_child)
            os.close(source_child)
        return
    if not stat.S_ISREG(source_value.st_mode) or source_value.st_nlink != 1:
        raise UnsafeInstallPath(f"linked or special source path is not allowed: {source_name}")
    source_file = os.open(
        source_name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=source_directory,
    )
    target_file: int | None = None
    try:
        opened = os.fstat(source_file)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (source_value.st_dev, source_value.st_ino)
            != (opened.st_dev, opened.st_ino)
        ):
            raise UnsafeInstallPath(
                f"source file identity changed during copy: {source_name}"
            )
        target_file = os.open(
            target_name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=target_directory,
        )
        while True:
            chunk = os.read(source_file, 1024 * 1024)
            if not chunk:
                break
            offset = 0
            while offset < len(chunk):
                written = os.write(target_file, chunk[offset:])
                if written == 0:
                    raise OSError("short install copy write")
                offset += written
        os.fchmod(target_file, stat.S_IMODE(source_value.st_mode))
        os.fsync(target_file)
    finally:
        if target_file is not None:
            os.close(target_file)
        os.close(source_file)


def _remove_path(path: Path) -> None:
    path = _absolute(path)
    if os.name != "nt":
        try:
            directory = _safe_fs._open_posix_directory(
                path.parent,
                root=Path(path.anchor),
                create=False,
            )
        except FileNotFoundError:
            return
        try:
            _posix_remove_entry(directory, path.name)
            os.fsync(directory)
        finally:
            os.close(directory)
        return
    if not _lexists(path):
        return
    if _unsafe_link(path):
        raise UnsafeInstallPath(f"refusing to remove linked path: {path}")
    if path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        raise UnsafeInstallPath(f"refusing to remove special path: {path}")
    _fsync_directory(path.parent)


def _path_hash(path: Path) -> str:
    if not _lexists(path):
        return _MISSING_HASH
    _assert_safe_tree(path)
    entries: list[dict[str, Any]] = []
    for current, directories, files in os.walk(path, followlinks=False):
        root = Path(current)
        directories.sort()
        files.sort()
        for directory in directories:
            relative = (root / directory).relative_to(path).as_posix()
            entries.append({"path": relative, "type": "directory"})
        for filename in files:
            item = root / filename
            relative = item.relative_to(path).as_posix()
            digest = hashlib.sha256()
            size = 0
            with item.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
            entries.append(
                {
                    "path": relative,
                    "type": "file",
                    "size": size,
                    "sha256": digest.hexdigest(),
                }
            )
    return _json_hash({"type": "directory", "entries": entries})


def _full_path_hash(path: Path) -> str:
    if not _lexists(path):
        return _MISSING_HASH
    _assert_safe_ancestors(path)
    if path.is_dir():
        return _path_hash(path)
    if not path.is_file():
        raise UnsafeInstallPath(f"managed path is not a file or directory: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return _json_hash(
        {"type": "file", "size": size, "sha256": digest.hexdigest()}
    )


def _fsync_directory(path: Path) -> None:
    """Durably publish a directory mutation using the reviewed adapter."""
    path = _absolute(path)
    if os.name != "nt":
        _safe_fs._sync_safe_directory(
            path,
            root=Path(path.anchor),
        )
        return
    _reviewed_fsync_directory(path)


def _read_json_object(path: Path, *, missing_ok: bool = False) -> dict[str, Any]:
    if not _lexists(path):
        if missing_ok:
            return {}
        raise FileNotFoundError(path)
    _assert_safe_ancestors(path)
    if not path.is_file():
        raise UnsafeInstallPath(f"JSON target is not a regular file: {path}")
    try:
        if os.name == "nt":
            content = path.read_bytes()
        else:
            content = _safe_fs._read_safe_bytes(
                path,
                root=Path(path.anchor),
            )
        value = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _mcp_value(path: Path, key: str) -> tuple[bool, Any]:
    data = _read_json_object(path, missing_ok=True)
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be an object")
    return key in servers, servers.get(key)


def _mcp_hash(path: Path, key: str) -> str:
    exists, value = _mcp_value(path, key)
    return _json_hash({"exists": exists, "value": value if exists else None})


def _write_bytes_atomic(path: Path, content: bytes) -> None:
    path = _absolute(path)
    if os.name != "nt":
        _safe_fs._atomic_write(
            path,
            content,
            root=Path(path.anchor),
        )
        return
    _ensure_safe_directory(path.parent)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb", delete=False, dir=path.parent, prefix=".chatmaker-", suffix=".tmp"
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        _assert_safe_ancestors(path, include_final=False)
        if _lexists(path):
            _assert_safe_ancestors(path)
        os.replace(temporary_name, path)
        temporary_name = None
        _fsync_directory(path.parent)
    finally:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    _write_bytes_atomic(path, _canonical_json(dict(value)))


def _atomic_backup(
    source: Path,
    destination: Path,
    source_guards: _TargetDirectoryGuards | None = None,
) -> None:
    _assert_safe_ancestors(source)
    _ensure_safe_directory(destination.parent)
    temporary = destination.with_name(f".{destination.name}-{uuid.uuid4().hex}.tmp")
    if _lexists(temporary):
        raise UnsafeInstallPath(f"backup staging collision: {temporary}")
    if os.name != "nt":
        with _TargetDirectoryGuards([destination.parent]) as destination_guards:
            try:
                destination_guards.copy_path(
                    source,
                    temporary,
                    source_guards=source_guards,
                )
                destination_guards.replace(temporary, destination)
            finally:
                destination_guards.remove(temporary)
        return
    try:
        if source.is_dir():
            _assert_safe_tree(source)
            shutil.copytree(source, temporary)
        elif source.is_file():
            shutil.copy2(source, temporary)
        else:
            raise UnsafeInstallPath(f"cannot back up special path: {source}")
        _assert_safe_ancestors(destination, include_final=False)
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    finally:
        if _lexists(temporary):
            _remove_path(temporary)


class _TargetDirectoryGuards(AbstractContextManager):
    """Pin target parents while mutations run.

    Windows handles omit delete sharing so a parent cannot be replaced by a
    junction. POSIX descriptors preserve and verify the no-follow identity and
    are used for relative renames.
    """

    def __init__(self, parents: Sequence[Path]) -> None:
        self.parents = tuple(dict.fromkeys(_absolute(path) for path in parents))
        self.handles: dict[str, int] = {}

    def __enter__(self):
        try:
            for parent in self.parents:
                _assert_safe_ancestors(parent)
                key = os.path.normcase(str(parent))
                if os.name == "nt":
                    handle = _safe_fs._nt_create_file(
                        None,
                        _safe_fs._windows_nt_path(parent),
                        desired_access=0x80000000 | 0x00100000,
                        disposition=1,
                        options=0x00000001 | 0x00000020 | 0x00200000,
                        share_access=0x00000001 | 0x00000002,
                    )
                    _safe_fs._assert_windows_directory_handle(handle)
                else:
                    handle = _safe_fs._open_posix_directory(
                        parent,
                        root=Path(parent.anchor),
                        create=False,
                    )
                self.handles[key] = handle
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type, exc, traceback):
        for handle in self.handles.values():
            if os.name == "nt":
                _safe_fs._WINDOWS_KERNEL32.CloseHandle(handle)
            else:
                os.close(handle)
        self.handles.clear()
        return False

    def _handle(self, parent: Path) -> int:
        parent = _absolute(parent)
        return self.handles[os.path.normcase(str(parent))]

    def verify_all(self) -> None:
        if os.name == "nt":
            return
        for parent in self.parents:
            handle = self._handle(parent)
            try:
                named = parent.lstat()
            except OSError as exc:
                raise UnsafeInstallPath(
                    "target parent identity changed during transaction"
                ) from exc
            opened = os.fstat(handle)
            if (
                parent.is_symlink()
                or is_reparse(parent)
                or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
            ):
                raise UnsafeInstallPath(
                    "target parent identity changed during transaction"
                )

    def exists(self, path: Path) -> bool:
        path = _absolute(path)
        handle = self._handle(path.parent)
        if os.name == "nt":
            return _lexists(path)
        try:
            os.stat(path.name, dir_fd=handle, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return True

    def fsync(self, parent: Path) -> None:
        parent = _absolute(parent)
        handle = self._handle(parent)
        if os.name == "nt":
            _reviewed_fsync_directory(parent)
        else:
            os.fsync(handle)

    def copy_path(
        self,
        source: Path,
        target: Path,
        *,
        source_guards: _TargetDirectoryGuards | None = None,
    ) -> None:
        source = _absolute(source)
        target = _absolute(target)
        target_handle = self._handle(target.parent)
        if self.exists(target):
            raise UnsafeInstallPath(f"copy target already exists: {target}")
        if os.name == "nt":
            if source.is_dir():
                _assert_safe_tree(source)
                shutil.copytree(source, target)
            elif source.is_file():
                shutil.copy2(source, target)
            else:
                raise UnsafeInstallPath(f"cannot copy special path: {source}")
            self.fsync(target.parent)
            return
        close_source = source_guards is None
        if source_guards is None:
            source_handle = _safe_fs._open_posix_directory(
                source.parent,
                root=Path(source.anchor),
                create=False,
            )
        else:
            source_handle = source_guards._handle(source.parent)
        try:
            try:
                _posix_copy_entry(
                    source_handle,
                    source.name,
                    target_handle,
                    target.name,
                )
            except Exception:
                _posix_remove_entry(target_handle, target.name)
                raise
            os.fsync(target_handle)
        finally:
            if close_source:
                os.close(source_handle)

    def write_bytes(self, path: Path, content: bytes) -> None:
        path = _absolute(path)
        handle = self._handle(path.parent)
        if self.exists(path):
            raise UnsafeInstallPath(f"write target already exists: {path}")
        if os.name == "nt":
            _write_bytes_atomic(path, content)
            return
        descriptor = os.open(
            path.name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=handle,
        )
        try:
            offset = 0
            while offset < len(content):
                written = os.write(descriptor, content[offset:])
                if written == 0:
                    raise OSError("short install stage write")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(handle)

    def remove(self, path: Path) -> None:
        path = _absolute(path)
        handle = self._handle(path.parent)
        if os.name == "nt":
            _remove_path(path)
            return
        _posix_remove_entry(handle, path.name)
        os.fsync(handle)

    def replace(self, source: Path, target: Path) -> None:
        if _absolute(source.parent) != _absolute(target.parent):
            raise UnsafeInstallPath("guarded replace must stay in one target parent")
        handle = self._handle(target.parent)
        if os.name == "nt":
            os.replace(source, target)
        else:
            os.replace(
                source.name,
                target.name,
                src_dir_fd=handle,
                dst_dir_fd=handle,
            )
        self.fsync(target.parent)


def _activate_staging(
    staging: Path,
    target: Path,
    guards: _TargetDirectoryGuards | None = None,
) -> None:
    """Activate a same-directory stage, with the established Windows fallback."""
    try:
        if guards is None:
            os.replace(staging, target)
            _fsync_directory(target.parent)
        else:
            guards.replace(staging, target)
    except PermissionError:
        if os.name != "nt":
            raise
        if _lexists(target):
            raise
        if guards is not None and guards.exists(target):
            raise
        try:
            if guards is None:
                shutil.copytree(staging, target)
            else:
                guards.copy_path(staging, target, source_guards=guards)
        except Exception:
            if guards is None:
                if _lexists(target):
                    _remove_path(target)
            elif guards.exists(target):
                guards.remove(target)
            raise
        else:
            if guards is None:
                _remove_path(staging)
                _fsync_directory(target.parent)
            else:
                guards.remove(staging)


def _aggregate_hash(records: Sequence[Mapping[str, Any]]) -> str:
    values = sorted(
        ({"identity": str(item["identity"]), "hash": str(item["installed_hash"])} for item in records),
        key=lambda item: item["identity"],
    )
    return _json_hash(values)


def _path_token(identity: str) -> str:
    """Return a bounded filename token; managed names remain data, never paths."""
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def _record_set_hash(
    transaction_id: str,
    installation_id: str,
    records: Sequence[Mapping[str, Any]],
) -> str:
    return _json_hash(
        {
            "transaction_id": transaction_id,
            "installation_id": installation_id,
            "records": [dict(record) for record in records],
        }
    )


def _journal_binding(journal: Mapping[str, Any]) -> str:
    keys = (
        "schema_version",
        "transaction_id",
        "installation_id",
        "kind",
        "target_transaction_id",
        "record_set_hash",
        "records",
        "after_records",
        "previous_state",
        "next_state",
    )
    return _json_hash({key: journal.get(key) for key in keys})


def _active_state_binding(state: Mapping[str, Any]) -> str:
    keys = (
        "schema_version",
        "installation_id",
        "active_transaction_id",
        "active_record_set_hash",
        "managed_hash",
        "managed",
    )
    return _json_hash({key: state.get(key) for key in keys})


class InstallTransaction:
    """Apply and reverse one named installation under a global root lock."""

    def __init__(
        self,
        *,
        root: Path | str | None = None,
        installation_id: str = "default",
        failure_injector: FailureInjector | None = None,
    ) -> None:
        if not installation_id or "\x00" in installation_id:
            raise ValueError("installation_id must be non-empty")
        self.root = _absolute(root or (Path.home() / ".chatmaker"))
        self.installation_id = installation_id
        self.failure_injector = failure_injector
        state_name = hashlib.sha256(installation_id.encode("utf-8")).hexdigest() + ".json"
        self.state_path = self.root / "state" / state_name
        self.transactions_root = self.root / "transactions"
        self.backups_root = self.root / "backups"
        self.lock_path = self.root / "locks" / "install.lock"

    def _inject(self, point: str, context: Mapping[str, Any]) -> None:
        if self.failure_injector is not None:
            self.failure_injector(point, context)

    def _prepare_management_root(self) -> None:
        for path in (
            self.root,
            self.root / "state",
            self.transactions_root,
            self.backups_root,
            self.root / "locks",
        ):
            _ensure_safe_directory(path)

    def _read_state_raw(self) -> dict[str, Any] | None:
        if not _lexists(self.state_path):
            return None
        value = _read_json_object(self.state_path)
        if value.get("installation_id") != self.installation_id:
            raise InstallConflict("installer state belongs to another installation")
        return value

    def _write_pending_state(
        self,
        previous_state: Mapping[str, Any] | None,
        journal: Mapping[str, Any],
    ) -> None:
        if previous_state is None:
            pending: dict[str, Any] = {
                "schema_version": "1.0",
                "installation_id": self.installation_id,
                "phase": "pending",
                "active_transaction_id": None,
                "managed_hash": _aggregate_hash([]),
                "managed": [],
            }
        else:
            pending = json.loads(_canonical_json(dict(previous_state)).decode("utf-8"))
            pending["phase"] = "pending"
        pending["pending"] = {
            "transaction_id": journal["transaction_id"],
            "journal_binding": _journal_binding(journal),
            "had_previous_state": previous_state is not None,
        }
        _write_json_atomic(self.state_path, pending)

    def _restore_state_value(self, value: Mapping[str, Any] | None) -> None:
        if value is None:
            if _lexists(self.state_path):
                _remove_path(self.state_path)
            return
        restored = json.loads(_canonical_json(dict(value)).decode("utf-8"))
        restored["phase"] = "active"
        restored.pop("pending", None)
        _write_json_atomic(self.state_path, restored)

    def _transition_state(self, journal: dict[str, Any]) -> None:
        receipt = {
            "transaction_id": journal["transaction_id"],
            "journal_binding": _journal_binding(journal),
        }
        next_state = journal.get("next_state")
        if next_state is None:
            value: dict[str, Any] = {
                "schema_version": "1.0",
                "installation_id": self.installation_id,
                "phase": "completed",
                "active_transaction_id": None,
                "managed_hash": _aggregate_hash([]),
                "managed": [],
                "last_operation": receipt,
            }
        elif isinstance(next_state, Mapping):
            value = json.loads(_canonical_json(dict(next_state)).decode("utf-8"))
            value["phase"] = "active"
            value["last_operation"] = receipt
        else:
            raise InstallConflict("journal next state is malformed")
        _write_json_atomic(self.state_path, value)

    def _finalize_journal(self, journal_path: Path, journal: dict[str, Any]) -> None:
        journal["status"] = "finalized"
        journal["finalized_at_ns"] = time.time_ns()
        _write_json_atomic(journal_path, journal)
        if journal.get("kind") == "restore":
            target_path = self._journal_path(str(journal["target_transaction_id"]))
            target = _read_json_object(target_path)
            target["status"] = "restored"
            target["restored_at_ns"] = time.time_ns()
            _write_json_atomic(target_path, target)
        if journal.get("next_state") is None and _lexists(self.state_path):
            _remove_path(self.state_path)

    def _validate_record_shape(
        self,
        record: Mapping[str, Any],
        transaction_id: str,
        *,
        validate_backup_hash: bool,
    ) -> None:
        self._journal_path(transaction_id)
        target_value = record.get("target")
        if not isinstance(target_value, str):
            raise InstallConflict("journal target is malformed")
        target = _absolute(target_value)
        if str(target) != target_value:
            raise InstallConflict("journal target is not canonical")
        kind = record.get("kind")
        name = record.get("name")
        if not isinstance(name, str) or not name:
            raise InstallConflict("journal managed name is malformed")
        if kind == "skill":
            if target.name != name or record.get("identity") != f"skill:{target}":
                raise InstallConflict("journal Skill identity is malformed")
        elif kind == "mcp":
            key = record.get("server_key")
            if key != name or record.get("identity") != f"mcp:{target}#{key}":
                raise InstallConflict("journal MCP identity is malformed")
        else:
            raise InstallConflict("journal record kind is malformed")
        for key in ("before_hash", "installed_hash"):
            value = record.get(key)
            if value is not None and (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise InstallConflict(f"journal {key} is malformed")
        before_exists = record.get("before_exists")
        if not isinstance(before_exists, bool):
            raise InstallConflict("journal before_exists is malformed")
        backup = record.get("backup")
        self._validate_backup(backup, transaction_id)
        if before_exists:
            if not isinstance(backup, str) or not _lexists(_absolute(backup)):
                raise InstallConflict("journal before-image is missing")
            if validate_backup_hash and _full_path_hash(_absolute(backup)) != record.get(
                "before_hash"
            ):
                raise InstallConflict("journal before-image hash mismatch")
        elif backup is not None or record.get("before_hash") != _MISSING_HASH:
            raise InstallConflict("journal missing before-image is inconsistent")

    def _validate_journal_binding(
        self,
        journal: Mapping[str, Any],
        *,
        expected_transaction_id: str,
        expected_binding: str | None = None,
        active_state: Mapping[str, Any] | None = None,
    ) -> None:
        if (
            journal.get("schema_version") != "1.0"
            or journal.get("transaction_id") != expected_transaction_id
            or journal.get("installation_id") != self.installation_id
            or journal.get("kind") not in {"apply", "restore", "uninstall"}
        ):
            raise InstallConflict("journal identity is malformed")
        records = journal.get("records")
        if not isinstance(records, list) or not all(
            isinstance(record, Mapping) for record in records
        ):
            raise InstallConflict("journal records are malformed")
        calculated = _record_set_hash(
            expected_transaction_id,
            self.installation_id,
            records,
        )
        if calculated != journal.get("record_set_hash"):
            raise InstallConflict("journal record set binding mismatch")
        if expected_binding is not None and _journal_binding(journal) != expected_binding:
            raise InstallConflict("journal binding mismatch")
        if active_state is not None:
            if (
                active_state.get("active_transaction_id") != expected_transaction_id
                or active_state.get("active_record_set_hash") != calculated
            ):
                raise InstallConflict("active state does not bind this journal")
            active_records = active_state.get("managed")
            if not isinstance(active_records, list):
                raise InstallConflict("active state managed set is malformed")
            if _aggregate_hash(active_records) != active_state.get("managed_hash"):
                raise InstallConflict("active state managed hash mismatch")
            next_state = journal.get("next_state")
            if (
                journal.get("kind") != "apply"
                or not isinstance(next_state, Mapping)
                or _active_state_binding(active_state)
                != _active_state_binding(next_state)
            ):
                raise InstallConflict("active state managed set does not match journal")
            managed = {
                str(record["identity"]): record
                for record in active_records
            }
            for record in records:
                installed = managed.get(str(record["identity"]))
                if installed is None or installed.get("installed_hash") != record.get(
                    "installed_hash"
                ):
                    raise InstallConflict("active state record set does not match journal")
        for record in records:
            self._validate_record_shape(
                record,
                str(record.get("backup_transaction_id") or expected_transaction_id),
                validate_backup_hash=True,
            )
        after_records = journal.get("after_records", [])
        if not isinstance(after_records, list):
            raise InstallConflict("journal after-records are malformed")
        for record in after_records:
            if not isinstance(record, Mapping):
                raise InstallConflict("journal after-record is malformed")
            self._validate_record_shape(
                record,
                str(record.get("backup_transaction_id") or expected_transaction_id),
                validate_backup_hash=True,
            )

    @staticmethod
    def _restore_stage_path(target: Path, operation_id: str, identity: str) -> Path:
        return target.parent / (
            f".chatmaker-{operation_id}-{_path_token(identity)}.restore-staging"
        )

    @staticmethod
    def _restore_displaced_path(target: Path, operation_id: str, identity: str) -> Path:
        return target.parent / (
            f".chatmaker-{operation_id}-{_path_token(identity)}.restore-current"
        )

    def _restore_records_atomically(
        self,
        records: Sequence[Mapping[str, Any]],
        operation_id: str,
        *,
        inject_point: str | None = None,
        target_guards: _TargetDirectoryGuards | None = None,
        verify_targets: bool = True,
    ) -> None:
        stages: dict[str, Path] = {}
        displaced: dict[str, Path] = {}
        applied: list[Mapping[str, Any]] = []
        parents = [_absolute(record["target"]).parent for record in records]
        for parent in parents:
            _ensure_safe_directory(parent)
        owns_guards = target_guards is None
        if target_guards is None:
            target_guards = _TargetDirectoryGuards(parents)
            target_guards.__enter__()
        else:
            for parent in parents:
                target_guards._handle(parent)
        try:
            for record in records:
                self._validate_record_shape(
                    record,
                    str(record.get("backup_transaction_id") or operation_id),
                    validate_backup_hash=True,
                )
                identity = str(record["identity"])
                if not record["before_exists"]:
                    continue
                target = _absolute(record["target"])
                stage = self._restore_stage_path(target, operation_id, identity)
                if target_guards.exists(stage):
                    raise UnsafeInstallPath(f"restore staging collision: {stage}")
                backup = _absolute(record["backup"])
                target_guards.copy_path(backup, stage)
                if _full_path_hash(stage) != record["before_hash"]:
                    raise InstallConflict("staged before-image hash mismatch")
                stages[identity] = stage

            for record in records:
                identity = str(record["identity"])
                target = _absolute(record["target"])
                moved = self._restore_displaced_path(target, operation_id, identity)
                if target_guards.exists(moved):
                    raise UnsafeInstallPath(f"restore displacement collision: {moved}")
                if target_guards.exists(target):
                    target_guards.replace(target, moved)
                    displaced[identity] = moved
                if record["before_exists"]:
                    stage = stages[identity]
                    if stage.is_dir():
                        _activate_staging(stage, target, target_guards)
                    else:
                        target_guards.replace(stage, target)
                applied.append(record)
                if inject_point is not None:
                    self._inject(
                        inject_point,
                        {"identity": identity, "target": str(target)},
                    )

            if verify_targets:
                for record in records:
                    target = _absolute(record["target"])
                    if _full_path_hash(target) != record["before_hash"]:
                        raise InstallConflict("restored target hash mismatch")
            for identity, moved in tuple(displaced.items()):
                target_guards.remove(moved)
                displaced.pop(identity, None)
        except Exception:
            for record in reversed(applied):
                identity = str(record["identity"])
                target = _absolute(record["target"])
                moved = displaced.get(identity)
                if target_guards.exists(target):
                    target_guards.remove(target)
                if moved is not None and target_guards.exists(moved):
                    target_guards.replace(moved, target)
                    displaced.pop(identity, None)
            raise
        finally:
            for stage in stages.values():
                if target_guards.exists(stage):
                    target_guards.remove(stage)
            if owns_guards:
                target_guards.__exit__(None, None, None)

    def _cleanup_operation_displaced(
        self,
        records: Sequence[Mapping[str, Any]],
        operation_id: str,
        target_guards: _TargetDirectoryGuards | None = None,
    ) -> None:
        parents = [_absolute(record["target"]).parent for record in records]
        owns_guards = target_guards is None
        if target_guards is None:
            target_guards = _TargetDirectoryGuards(parents)
            target_guards.__enter__()
        try:
            for record in records:
                target = _absolute(record["target"])
                path = self._restore_displaced_path(
                    target, operation_id, str(record["identity"])
                )
                if target_guards.exists(path):
                    target_guards.remove(path)
        finally:
            if owns_guards:
                target_guards.__exit__(None, None, None)

    def _cleanup_apply_displaced(
        self,
        records: Sequence[Mapping[str, Any]],
        operation_id: str,
        target_guards: _TargetDirectoryGuards | None = None,
    ) -> None:
        skill_records = [record for record in records if record["kind"] == "skill"]
        parents = [_absolute(record["target"]).parent for record in skill_records]
        owns_guards = target_guards is None
        if target_guards is None:
            target_guards = _TargetDirectoryGuards(parents)
            target_guards.__enter__()
        try:
            for record in skill_records:
                target = _absolute(record["target"])
                path = target.parent / (
                    f".chatmaker-{operation_id}-{record['name']}.displaced"
                )
                if target_guards.exists(path):
                    target_guards.remove(path)
        finally:
            if owns_guards:
                target_guards.__exit__(None, None, None)

    def _roll_forward_journal(self, path: Path, journal: dict[str, Any]) -> None:
        kind = str(journal["kind"])
        verification = journal["records"] if kind == "apply" else journal["after_records"]
        for record in verification:
            if kind == "apply":
                actual = self._current_hash(record)
                expected = record["installed_hash"]
            else:
                actual = _full_path_hash(_absolute(record["target"]))
                expected = record["before_hash"]
            if actual != expected:
                raise InstallConflict("committed journal targets do not verify")
        self._transition_state(journal)
        self._finalize_journal(path, journal)

    def _recover_locked(self) -> None:
        state = self._read_state_raw()
        if state is None:
            self._retire_unbound_journals(set())
            return
        phase = state.get("phase", "active")
        if phase == "completed":
            operation = state.get("last_operation")
            if isinstance(operation, Mapping):
                path = self._journal_path(str(operation["transaction_id"]))
                journal = _read_json_object(path)
                if _journal_binding(journal) != operation.get("journal_binding"):
                    raise InstallConflict("completed operation journal binding mismatch")
                if journal.get("status") in {"committed", "finalized"}:
                    self._finalize_journal(path, journal)
            self._retire_unbound_journals(
                {str(operation.get("transaction_id"))}
                if isinstance(operation, Mapping)
                else set()
            )
            return
        if phase != "pending":
            operation = state.get("last_operation")
            if isinstance(operation, Mapping):
                path = self._journal_path(str(operation["transaction_id"]))
                journal = _read_json_object(path)
                if _journal_binding(journal) != operation.get("journal_binding"):
                    raise InstallConflict("active operation journal binding mismatch")
                if journal.get("status") in {"committed", "finalized"}:
                    self._finalize_journal(path, journal)
            bound = {str(state.get("active_transaction_id") or "")}
            if isinstance(operation, Mapping):
                bound.add(str(operation.get("transaction_id") or ""))
            self._retire_unbound_journals(bound)
            return
        pending = state.get("pending")
        if not isinstance(pending, Mapping):
            raise InstallConflict("pending installer state is malformed")
        transaction_id = str(pending.get("transaction_id") or "")
        path = self._journal_path(transaction_id)
        journal = _read_json_object(path)
        self._validate_journal_binding(
            journal,
            expected_transaction_id=transaction_id,
            expected_binding=str(pending.get("journal_binding") or ""),
        )
        status = journal.get("status")
        if status == "prepared":
            self._restore_records_atomically(
                journal["records"],
                uuid.uuid4().hex,
            )
            if journal["kind"] == "apply":
                self._cleanup_apply_displaced(journal["records"], transaction_id)
            else:
                self._cleanup_operation_displaced(journal["records"], transaction_id)
            journal["status"] = "rolled_back"
            journal["rolled_back_at_ns"] = time.time_ns()
            _write_json_atomic(path, journal)
            self._restore_state_value(journal.get("previous_state"))
            return
        if status in {"committed", "finalized"}:
            self._roll_forward_journal(path, journal)
            return
        if status == "rolled_back":
            self._restore_state_value(journal.get("previous_state"))
            return
        raise InstallConflict(f"pending journal has invalid status: {status}")

    def _retire_unbound_journals(self, bound: set[str]) -> None:
        for path in sorted(self.transactions_root.glob("*.json")):
            transaction_id = path.stem
            if transaction_id in bound:
                continue
            if (
                len(transaction_id) != _TRANSACTION_ID_LENGTH
                or any(character not in "0123456789abcdef" for character in transaction_id)
            ):
                continue
            try:
                journal = _read_json_object(path)
            except (OSError, ValueError):
                continue
            if journal.get("installation_id") != self.installation_id:
                continue
            status = journal.get("status")
            if status == "prepared":
                journal["status"] = "rolled_back"
                journal["recovery"] = "unbound_before_mutation"
                journal["rolled_back_at_ns"] = time.time_ns()
                _write_json_atomic(path, journal)
            elif status == "committed":
                raise InstallConflict("unbound committed journal cannot be trusted")

    def _normalize(self, changes: Sequence[Mapping[str, Any]]) -> list[_Change]:
        normalized: list[_Change] = []
        seen: set[str] = set()
        for raw in changes:
            if not isinstance(raw, Mapping):
                raise TypeError("install changes must be mappings")
            kind = str(raw.get("kind", ""))
            if kind == "skill_bundle":
                source_root = _absolute(raw["source"])
                target_root = _absolute(raw.get("path") or raw.get("target"))
                _assert_safe_ancestors(target_root, include_final=True)
                names = raw.get("names") or ("chatmaker", "chatduino", "chatweb")
                if isinstance(names, (str, bytes)):
                    raise ValueError("Skill names must be a sequence")
                for raw_name in names:
                    name = str(raw_name)
                    if not name or name in {".", ".."} or Path(name).name != name or any(
                        separator in name for separator in ("/", "\\")
                    ):
                        raise UnsafeInstallPath(f"unsafe Skill name: {name}")
                    source = source_root / name
                    target = target_root / name
                    _assert_safe_tree(source)
                    if not (source / "SKILL.md").is_file():
                        raise FileNotFoundError(f"missing source Skill: {source}")
                    _assert_safe_ancestors(target, include_final=True)
                    if _lexists(target) and not target.is_dir():
                        raise UnsafeInstallPath(
                            f"Skill target is not a directory: {target}"
                        )
                    identity = f"skill:{target}"
                    normalized.append(
                        _Change("skill", identity, target, name=name, source=source)
                    )
            elif kind == "mcp_server":
                target = _absolute(raw["path"])
                _assert_safe_ancestors(target, include_final=True)
                key = str(raw.get("server_key") or raw.get("key") or "")
                if not key or "\x00" in key:
                    raise ValueError("mcp_server requires a server_key")
                server = raw.get("server", raw.get("value"))
                if not isinstance(server, Mapping):
                    raise ValueError("mcp_server requires an object server")
                server_value = json.loads(_canonical_json(dict(server)).decode("utf-8"))
                identity = f"mcp:{target}#{key}"
                normalized.append(
                    _Change(
                        "mcp",
                        identity,
                        target,
                        name=key,
                        server_key=key,
                        server=server_value,
                    )
                )
            else:
                raise ValueError(f"unsupported install change kind: {kind}")
        for item in normalized:
            if item.identity in seen:
                raise ValueError(f"duplicate install change: {item.identity}")
            seen.add(item.identity)
        return normalized

    def _load_state(self) -> dict[str, Any] | None:
        value = self._read_state_raw()
        if value is None:
            return None
        if value.get("phase", "active") != "active":
            raise InstallConflict("installer state is not active after recovery")
        records = value.get("managed")
        if not isinstance(records, list):
            raise InstallConflict("active installer state is malformed")
        for record in records:
            if not isinstance(record, dict):
                raise InstallConflict("active installer record is malformed")
            self._validate_managed_record(record)
        transaction_id = value.get("active_transaction_id")
        if not isinstance(transaction_id, str):
            raise InstallConflict("active transaction id is malformed")
        journal = _read_json_object(self._journal_path(transaction_id))
        self._validate_journal_binding(
            journal,
            expected_transaction_id=transaction_id,
            active_state=value,
        )
        return value

    def _validate_managed_record(self, record: Mapping[str, Any]) -> None:
        target = _absolute(record["target"])
        _assert_safe_ancestors(target, include_final=True)
        kind = str(record.get("kind"))
        name = str(record.get("name") or "")
        if kind == "skill":
            if not name or target.name != name:
                raise UnsafeInstallPath("managed Skill target does not match its name")
            expected_identity = f"skill:{target}"
        elif kind == "mcp":
            key = str(record.get("server_key") or "")
            if not key or key != name:
                raise UnsafeInstallPath("managed MCP key is malformed")
            expected_identity = f"mcp:{target}#{key}"
        else:
            raise InstallConflict(f"unknown managed content kind: {kind}")
        if record.get("identity") != expected_identity:
            raise UnsafeInstallPath("managed content identity does not match its path")
        baseline = record.get("baseline")
        if not isinstance(baseline, Mapping):
            raise InstallConflict("managed content baseline is malformed")
        transaction_id = str(baseline.get("transaction_id") or "")
        self._journal_path(transaction_id)
        backup = baseline.get("backup")
        self._validate_backup(backup, transaction_id)
        if baseline.get("before_exists") and (
            not isinstance(backup, str) or not _lexists(_absolute(backup))
        ):
            raise InstallConflict(
                f"managed before-image is missing: {record.get('identity')}"
            )

    @staticmethod
    def _current_hash(change: _Change | Mapping[str, Any]) -> str:
        kind = change.kind if isinstance(change, _Change) else str(change["kind"])
        target = change.target if isinstance(change, _Change) else _absolute(change["target"])
        if kind == "skill":
            return _path_hash(target)
        key = change.server_key if isinstance(change, _Change) else str(change["server_key"])
        if key is None:
            raise ValueError("missing MCP server key")
        return _mcp_hash(target, key)

    @staticmethod
    def _desired_hash(change: _Change) -> str:
        if change.kind == "skill":
            assert change.source is not None
            return _path_hash(change.source)
        return _json_hash({"exists": True, "value": dict(change.server or {})})

    def _conflicts(self, state: Mapping[str, Any]) -> list[dict[str, Any]]:
        conflicts = []
        for record in state.get("managed", []):
            expected = str(record["installed_hash"])
            try:
                actual = self._current_hash(record)
            except (OSError, ValueError) as exc:
                conflicts.append(
                    {"identity": str(record.get("identity")), "reason": type(exc).__name__}
                )
                continue
            if actual != expected:
                conflicts.append(
                    {
                        "identity": str(record["identity"]),
                        "expected_hash": expected,
                        "actual_hash": actual,
                    }
                )
        return conflicts

    def _journal_path(self, transaction_id: str) -> Path:
        if (
            len(transaction_id) != _TRANSACTION_ID_LENGTH
            or any(character not in "0123456789abcdef" for character in transaction_id)
        ):
            raise UnsafeInstallPath("invalid transaction id")
        return self.transactions_root / f"{transaction_id}.json"

    def _validate_backup(self, value: str | None, transaction_id: str) -> None:
        if value is None:
            return
        backup = _absolute(value)
        expected = self.backups_root / transaction_id
        try:
            backup.relative_to(expected)
        except ValueError as exc:
            raise UnsafeInstallPath(f"before-image escaped transaction backup: {backup}") from exc
        _assert_safe_ancestors(backup)

    def _result_from_state(
        self,
        state: Mapping[str, Any],
        *,
        status: str,
        changes: Sequence[str] = (),
        unchanged: Sequence[str] = (),
    ) -> TransactionResult:
        transaction_id = str(state.get("active_transaction_id") or "") or None
        manifest = str(self._journal_path(transaction_id)) if transaction_id else None
        return TransactionResult(
            True,
            status,
            transaction_id=transaction_id,
            managed_hash=str(state.get("managed_hash") or "") or None,
            changes=tuple(changes),
            unchanged=tuple(unchanged),
            details={"manifest": manifest} if manifest else {},
        )

    def apply(self, changes: Sequence[Mapping[str, Any]]) -> TransactionResult:
        normalized = self._normalize(changes)
        self._prepare_management_root()
        with exclusive_file_lock(self.lock_path):
            self._recover_locked()
            return self._apply_locked(normalized)

    def _apply_locked(self, normalized: Sequence[_Change]) -> TransactionResult:
        active = self._load_state()
        if active is not None:
            conflicts = self._conflicts(active)
            if conflicts:
                return TransactionResult(
                    False,
                    "conflict",
                    transaction_id=str(active.get("active_transaction_id") or "") or None,
                    managed_hash=str(active.get("managed_hash") or "") or None,
                    conflicts=tuple(conflicts),
                )
        active_by_id = {
            str(item["identity"]): dict(item) for item in (active or {}).get("managed", [])
        }
        desired = {item.identity: self._desired_hash(item) for item in normalized}
        changed = [
            item
            for item in normalized
            if item.identity not in active_by_id
            or desired[item.identity] != active_by_id[item.identity]["installed_hash"]
        ]
        unchanged = [item.identity for item in normalized if item not in changed]
        if not changed:
            if active is None:
                return TransactionResult(True, "already_current", unchanged=tuple(unchanged))
            return self._result_from_state(
                active, status="already_current", unchanged=tuple(unchanged)
            )

        transaction_id = uuid.uuid4().hex
        journal_path = self._journal_path(transaction_id)
        backup_root = self.backups_root / transaction_id
        stages: dict[str, Path] = {}
        records: list[dict[str, Any]] = []
        applied: list[dict[str, Any]] = []
        displaced: dict[str, Path] = {}
        target_guards: _TargetDirectoryGuards | None = None
        journal_written = False
        previous_state = dict(active) if active is not None else None
        try:
            for item in changed:
                _ensure_safe_directory(item.target.parent)
            target_guards = _TargetDirectoryGuards(
                [item.target.parent for item in changed]
            )
            target_guards.__enter__()
            for index, item in enumerate(changed):
                self._inject("staging", {"identity": item.identity, "kind": item.kind})
                stage = item.target.parent / (
                    f".chatmaker-{transaction_id}-{index:03d}-{_path_token(item.identity)}.staging"
                )
                if target_guards.exists(stage):
                    raise UnsafeInstallPath(f"install staging path already exists: {stage}")
                if item.kind == "skill":
                    assert item.source is not None
                    _assert_safe_tree(item.source)
                    target_guards.copy_path(item.source, stage)
                else:
                    current = _read_json_object(item.target, missing_ok=True)
                    servers = current.setdefault("mcpServers", {})
                    if not isinstance(servers, dict):
                        raise ValueError("mcpServers must be an object")
                    servers[str(item.server_key)] = dict(item.server or {})
                    target_guards.write_bytes(stage, _canonical_json(current))
                stages[item.identity] = stage

            _ensure_safe_directory(backup_root)
            for index, item in enumerate(changed):
                before_exists = target_guards.exists(item.target)
                backup: str | None = None
                if before_exists:
                    _assert_safe_ancestors(item.target)
                    backup_path = backup_root / (
                        f"{index:03d}-{item.kind}-{_path_token(item.identity)}"
                    )
                    _atomic_backup(
                        item.target,
                        backup_path,
                        source_guards=target_guards,
                    )
                    backup = str(backup_path)
                record: dict[str, Any] = {
                    "kind": item.kind,
                    "identity": item.identity,
                    "target": str(item.target),
                    "name": item.name,
                    "before_exists": before_exists,
                    "backup": backup,
                    "backup_transaction_id": transaction_id,
                    "before_hash": _full_path_hash(item.target),
                    "installed_hash": desired[item.identity],
                }
                if item.kind == "mcp":
                    before_key_exists, before_value = _mcp_value(
                        item.target, str(item.server_key)
                    )
                    record.update(
                        {
                            "server_key": item.server_key,
                            "before_key_exists": before_key_exists,
                            "before_value": before_value if before_key_exists else None,
                            "installed_value": dict(item.server or {}),
                        }
                    )
                records.append(record)

            managed_by_id = dict(active_by_id)
            for item, record in zip(changed, records):
                if item.identity in active_by_id:
                    baseline = dict(active_by_id[item.identity]["baseline"])
                else:
                    baseline = {
                        key: record.get(key)
                        for key in (
                            "before_exists",
                            "backup",
                            "before_hash",
                            "before_key_exists",
                            "before_value",
                        )
                        if key in record
                    }
                    baseline["transaction_id"] = transaction_id
                managed = {
                    "kind": item.kind,
                    "identity": item.identity,
                    "target": str(item.target),
                    "name": item.name,
                    "installed_hash": desired[item.identity],
                    "baseline": baseline,
                }
                if item.kind == "mcp":
                    managed.update(
                        {
                            "server_key": item.server_key,
                            "installed_value": dict(item.server or {}),
                        }
                    )
                managed_by_id[item.identity] = managed
            managed_records = sorted(managed_by_id.values(), key=lambda item: item["identity"])
            managed_hash = _aggregate_hash(managed_records)
            record_hash = _record_set_hash(
                transaction_id,
                self.installation_id,
                records,
            )
            state = {
                "schema_version": "1.0",
                "installation_id": self.installation_id,
                "phase": "active",
                "active_transaction_id": transaction_id,
                "active_record_set_hash": record_hash,
                "managed_hash": managed_hash,
                "managed": managed_records,
            }
            journal = {
                "schema_version": "1.0",
                "transaction_id": transaction_id,
                "installation_id": self.installation_id,
                "kind": "apply",
                "status": "prepared",
                "created_at_ns": time.time_ns(),
                "previous_state": previous_state,
                "records": records,
                "after_records": [],
                "record_set_hash": record_hash,
                "managed_hash": managed_hash,
                "next_state": state,
                "entries": [
                    {
                        "name": item["name"],
                        "target": item["target"],
                        "backup": item["baseline"].get("backup"),
                    }
                    for item in managed_records
                    if item["kind"] == "skill"
                ],
                "skill_manifest": str(journal_path),
            }
            _write_json_atomic(journal_path, journal)
            journal_written = True
            self._inject(
                "pending_state_replacement",
                {"transaction_id": transaction_id, "path": str(self.state_path)},
            )
            self._write_pending_state(previous_state, journal)

            for record in records:
                identity = str(record["identity"])
                target = _absolute(record["target"])
                _assert_safe_ancestors(target, include_final=True)
                if record["kind"] == "skill":
                    self._inject(
                        "skill_activation", {"identity": identity, "target": str(target)}
                    )
                    displaced_path = target.parent / (
                        f".chatmaker-{transaction_id}-{record['name']}.displaced"
                    )
                    if target_guards.exists(displaced_path):
                        raise UnsafeInstallPath(
                            f"install displacement path already exists: {displaced_path}"
                        )
                    if target_guards.exists(target):
                        target_guards.replace(target, displaced_path)
                        displaced[identity] = displaced_path
                    try:
                        _activate_staging(stages[identity], target, target_guards)
                    except Exception:
                        if target_guards.exists(displaced_path) and not target_guards.exists(target):
                            target_guards.replace(displaced_path, target)
                            displaced.pop(identity, None)
                        raise
                else:
                    self._inject(
                        "mcp_replacement", {"identity": identity, "target": str(target)}
                    )
                    target_guards.replace(stages[identity], target)
                applied.append(record)

            self._inject(
                "verification", {"transaction_id": transaction_id, "records": records}
            )
            for item in changed:
                actual = self._current_hash(item)
                if actual != desired[item.identity]:
                    raise RuntimeError(f"installation verification failed: {item.identity}")

            for identity, path in tuple(displaced.items()):
                self._inject(
                    "displaced_cleanup",
                    {"identity": identity, "path": str(path)},
                )
                target_guards.remove(path)
                displaced.pop(identity, None)
            target_guards.verify_all()

            journal["status"] = "committed"
            journal["committed_at_ns"] = time.time_ns()
            self._inject(
                "journal_replacement", {"transaction_id": transaction_id, "path": str(journal_path)}
            )
            _write_json_atomic(journal_path, journal)
            self._inject(
                "state_replacement", {"transaction_id": transaction_id, "path": str(self.state_path)}
            )
            self._transition_state(journal)
            self._finalize_journal(journal_path, journal)
            details = {
                "manifest": str(journal_path),
                "backups": {
                    str(record["identity"]): record.get("backup") for record in records
                },
                "entries": journal["entries"],
            }
            return TransactionResult(
                True,
                "updated" if active is not None else "installed",
                transaction_id=transaction_id,
                managed_hash=managed_hash,
                changes=tuple(item.identity for item in changed),
                unchanged=tuple(unchanged),
                details=details,
            )
        except Exception:
            if records:
                self._restore_records_atomically(
                    records,
                    uuid.uuid4().hex,
                    target_guards=target_guards,
                    verify_targets=False,
                )
                self._cleanup_apply_displaced(
                    records,
                    transaction_id,
                    target_guards=target_guards,
                )
            self._restore_state_value(previous_state)
            if journal_written and journal_path.is_file():
                try:
                    failed = _read_json_object(journal_path)
                    failed["status"] = "rolled_back"
                    failed["rolled_back_at_ns"] = time.time_ns()
                    _write_json_atomic(journal_path, failed)
                except Exception:
                    pass
            raise
        finally:
            for path in stages.values():
                if target_guards is not None and target_guards.exists(path):
                    target_guards.remove(path)
            if target_guards is not None:
                target_guards.__exit__(None, None, None)

    def _snapshot_current_records(
        self,
        managed: Sequence[Mapping[str, Any]],
        transaction_id: str,
        target_guards: _TargetDirectoryGuards | None = None,
    ) -> list[dict[str, Any]]:
        backup_root = self.backups_root / transaction_id
        _ensure_safe_directory(backup_root)
        records: list[dict[str, Any]] = []
        for index, item in enumerate(managed):
            target = _absolute(item["target"])
            exists = (
                target_guards.exists(target)
                if target_guards is not None
                else _lexists(target)
            )
            backup: str | None = None
            if exists:
                backup_path = backup_root / (
                    f"{index:03d}-{item['kind']}-{_path_token(str(item['identity']))}"
                )
                _atomic_backup(
                    target,
                    backup_path,
                    source_guards=target_guards,
                )
                backup = str(backup_path)
            records.append(
                {
                    "kind": item["kind"],
                    "identity": item["identity"],
                    "target": str(target),
                    "name": item["name"],
                    "server_key": item.get("server_key"),
                    "before_exists": exists,
                    "backup": backup,
                    "backup_transaction_id": transaction_id,
                    "before_hash": _full_path_hash(target),
                    "installed_hash": item.get("installed_hash"),
                }
            )
        return records

    def _run_restore_operation(
        self,
        *,
        kind: str,
        current_state: Mapping[str, Any],
        current_records: list[dict[str, Any]],
        after_records: list[dict[str, Any]],
        next_state: Mapping[str, Any] | None,
        target_transaction_id: str | None = None,
        inject_point: str,
        target_guards: _TargetDirectoryGuards | None = None,
    ) -> tuple[str, dict[str, Any]]:
        transaction_id = str(current_records[0]["backup_transaction_id"]) if current_records else uuid.uuid4().hex
        journal_path = self._journal_path(transaction_id)
        journal = {
            "schema_version": "1.0",
            "transaction_id": transaction_id,
            "installation_id": self.installation_id,
            "kind": kind,
            "target_transaction_id": target_transaction_id,
            "status": "prepared",
            "created_at_ns": time.time_ns(),
            "records": current_records,
            "after_records": after_records,
            "record_set_hash": _record_set_hash(
                transaction_id, self.installation_id, current_records
            ),
            "previous_state": dict(current_state),
            "next_state": dict(next_state) if next_state is not None else None,
        }
        _write_json_atomic(journal_path, journal)
        self._write_pending_state(current_state, journal)
        try:
            self._restore_records_atomically(
                after_records,
                transaction_id,
                inject_point=inject_point,
                target_guards=target_guards,
            )
            if target_guards is not None:
                target_guards.verify_all()
            journal["status"] = "committed"
            journal["committed_at_ns"] = time.time_ns()
            _write_json_atomic(journal_path, journal)
            self._inject(
                f"{kind}_state_replacement",
                {"transaction_id": transaction_id, "path": str(self.state_path)},
            )
            self._transition_state(journal)
            self._inject(
                f"{kind}_journal_finalization",
                {"transaction_id": transaction_id, "path": str(journal_path)},
            )
            self._finalize_journal(journal_path, journal)
        except Exception:
            self._restore_records_atomically(
                current_records,
                uuid.uuid4().hex,
                target_guards=target_guards,
                verify_targets=False,
            )
            self._cleanup_operation_displaced(
                after_records,
                transaction_id,
                target_guards=target_guards,
            )
            journal["status"] = "rolled_back"
            journal["rolled_back_at_ns"] = time.time_ns()
            _write_json_atomic(journal_path, journal)
            self._restore_state_value(current_state)
            raise
        return transaction_id, journal

    def restore(self, transaction_id: str) -> TransactionResult:
        self._prepare_management_root()
        with exclusive_file_lock(self.lock_path):
            self._recover_locked()
            journal_path = self._journal_path(transaction_id)
            journal = _read_json_object(journal_path)
            status = str(journal.get("status"))
            if status in {"restored", "rolled_back"}:
                return TransactionResult(
                    True, "already_restored", transaction_id=transaction_id
                )
            if status not in {"committed", "finalized"}:
                raise InstallConflict(f"transaction is not restorable: {status}")
            active = self._load_state()
            if active is None or active.get("active_transaction_id") != transaction_id:
                return TransactionResult(
                    False,
                    "conflict",
                    transaction_id=transaction_id,
                    conflicts=(
                        {"identity": transaction_id, "reason": "transaction_not_active"},
                    ),
                )
            self._validate_journal_binding(
                journal,
                expected_transaction_id=transaction_id,
                active_state=active,
            )
            conflicts = self._conflicts(active)
            if conflicts:
                return TransactionResult(
                    False,
                    "conflict",
                    transaction_id=transaction_id,
                    conflicts=tuple(conflicts),
                )
            operation_id = uuid.uuid4().hex
            target_guards = _TargetDirectoryGuards(
                [_absolute(record["target"]).parent for record in active["managed"]]
            )
            target_guards.__enter__()
            try:
                current_records = self._snapshot_current_records(
                    active["managed"],
                    operation_id,
                    target_guards=target_guards,
                )
                after_records = []
                for record in journal["records"]:
                    desired = dict(record)
                    desired["backup_transaction_id"] = transaction_id
                    after_records.append(desired)
                previous = journal.get("previous_state")
                if previous is not None and not isinstance(previous, Mapping):
                    raise InstallConflict("transaction previous state is malformed")
                self._run_restore_operation(
                    kind="restore",
                    current_state=active,
                    current_records=current_records,
                    after_records=after_records,
                    next_state=previous,
                    target_transaction_id=transaction_id,
                    inject_point="restore_after_target",
                    target_guards=target_guards,
                )
            finally:
                target_guards.__exit__(None, None, None)
            return TransactionResult(
                True,
                "restored",
                transaction_id=transaction_id,
                managed_hash=(
                    str(previous.get("managed_hash")) if isinstance(previous, Mapping) else None
                ),
                changes=tuple(str(item["identity"]) for item in journal["records"]),
            )

    def _uninstall_after_records(
        self,
        active: Mapping[str, Any],
        transaction_id: str,
    ) -> list[dict[str, Any]]:
        backup_root = self.backups_root / transaction_id
        _ensure_safe_directory(backup_root)
        desired: list[dict[str, Any]] = []
        for index, managed in enumerate(active["managed"]):
            baseline = managed.get("baseline")
            if not isinstance(baseline, Mapping):
                raise InstallConflict("managed baseline is missing")
            target = _absolute(managed["target"])
            if managed["kind"] == "skill":
                desired.append(
                    {
                        "kind": "skill",
                        "identity": managed["identity"],
                        "target": str(target),
                        "name": managed["name"],
                        "server_key": None,
                        "before_exists": bool(baseline.get("before_exists")),
                        "backup": baseline.get("backup"),
                        "backup_transaction_id": baseline.get("transaction_id"),
                        "before_hash": baseline.get("before_hash"),
                        "installed_hash": managed.get("installed_hash"),
                    }
                )
                continue

            key = str(managed["server_key"])
            data = _read_json_object(target, missing_ok=True)
            servers = data.setdefault("mcpServers", {})
            if not isinstance(servers, dict):
                raise ValueError("mcpServers must be an object")
            if baseline.get("before_key_exists"):
                servers[key] = baseline.get("before_value")
            else:
                servers.pop(key, None)
            config_existed = bool(baseline.get("before_exists"))
            desired_exists = config_existed or bool(servers) or set(data) != {"mcpServers"}
            backup: str | None = None
            before_hash = _MISSING_HASH
            if desired_exists:
                backup_path = backup_root / (
                    f"after-{index:03d}-mcp-{_path_token(str(managed['identity']))}"
                )
                _write_bytes_atomic(backup_path, _canonical_json(data))
                backup = str(backup_path)
                before_hash = _full_path_hash(backup_path)
            desired.append(
                {
                    "kind": "mcp",
                    "identity": managed["identity"],
                    "target": str(target),
                    "name": managed["name"],
                    "server_key": key,
                    "before_exists": desired_exists,
                    "backup": backup,
                    "backup_transaction_id": transaction_id,
                    "before_hash": before_hash,
                    "installed_hash": managed.get("installed_hash"),
                }
            )
        return desired

    def uninstall(self) -> TransactionResult:
        self._prepare_management_root()
        with exclusive_file_lock(self.lock_path):
            self._recover_locked()
            active = self._load_state()
            if active is None:
                return TransactionResult(True, "already_absent")
            conflicts = self._conflicts(active)
            if conflicts:
                return TransactionResult(
                    False,
                    "conflict",
                    transaction_id=str(active.get("active_transaction_id") or "") or None,
                    managed_hash=str(active.get("managed_hash") or "") or None,
                    conflicts=tuple(conflicts),
                )
            transaction_id = uuid.uuid4().hex
            target_guards = _TargetDirectoryGuards(
                [_absolute(record["target"]).parent for record in active["managed"]]
            )
            target_guards.__enter__()
            try:
                current_records = self._snapshot_current_records(
                    active["managed"],
                    transaction_id,
                    target_guards=target_guards,
                )
                after_records = self._uninstall_after_records(active, transaction_id)
                self._run_restore_operation(
                    kind="uninstall",
                    current_state=active,
                    current_records=current_records,
                    after_records=after_records,
                    next_state=None,
                    inject_point="uninstall_after_target",
                    target_guards=target_guards,
                )
            finally:
                target_guards.__exit__(None, None, None)
            restored = [
                str(item["name"])
                for item in active["managed"]
                if item["kind"] == "skill" and item["baseline"].get("before_exists")
            ]
            removed = [
                str(item["name"])
                for item in active["managed"]
                if item["kind"] == "skill" and not item["baseline"].get("before_exists")
            ]
            return TransactionResult(
                True,
                "uninstalled",
                transaction_id=transaction_id,
                changes=tuple(str(item["identity"]) for item in active["managed"]),
                details={
                    "restored_skills": restored,
                    "removed_skills": removed,
                    "config_restored": any(
                        item["kind"] == "mcp"
                        and item["baseline"].get("before_exists")
                        for item in active["managed"]
                    ),
                },
            )


__all__ = [
    "InstallConflict",
    "InstallTransaction",
    "TransactionResult",
    "UnsafeInstallPath",
    "canonical_install_path",
]

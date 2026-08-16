"""One-time, non-destructive deactivation of pre-Knowledge pack identities."""

from __future__ import annotations

import ctypes
import json
import os
import re
import stat
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Callable

from .file_lock import (
    FileLockFailure,
    UnsafeLockPath,
    exclusive_file_lock,
    is_reparse,
)

if TYPE_CHECKING:
    from .pack_manager import PackPaths


LEGACY_KNOWLEDGE_PACK_IDS = frozenset(
    {
        "chatmaker-board-arduino-nano-classic-wiki",
        "chatmaker-board-arduino-uno-r3-wiki",
        "chatmaker-board-esp32-devkit-v1-wiki",
    }
)
_MARKER_NAME = "knowledge-state-migration-v1.json"
_BACKUP_ROOT = Path("backups") / "knowledge-state-migration-v1"
_WINDOWS_REPARSE_POINT = 0x400
_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()

if os.name == "nt":
    from ctypes import wintypes

    class _WindowsFileInformation(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    _WINDOWS_KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _WINDOWS_KERNEL32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _WINDOWS_KERNEL32.CreateFileW.restype = wintypes.HANDLE
    _WINDOWS_KERNEL32.GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_WindowsFileInformation),
    ]
    _WINDOWS_KERNEL32.GetFileInformationByHandle.restype = wintypes.BOOL
    _WINDOWS_KERNEL32.WriteFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    _WINDOWS_KERNEL32.WriteFile.restype = wintypes.BOOL
    _WINDOWS_KERNEL32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    _WINDOWS_KERNEL32.FlushFileBuffers.restype = wintypes.BOOL
    _WINDOWS_KERNEL32.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _WINDOWS_KERNEL32.SetFileInformationByHandle.restype = wintypes.BOOL
    _WINDOWS_KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    _WINDOWS_KERNEL32.CloseHandle.restype = wintypes.BOOL
    _WINDOWS_INVALID_HANDLE = wintypes.HANDLE(-1).value


class KnowledgeStateMigrationError(OSError):
    """A safe migration could not complete without risking user state."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"knowledge state migration failed: {reason}")


@dataclass(frozen=True)
class MigrationResult:
    changed: bool
    backup_dir: Path | None
    deactivated_pack_ids: tuple[str, ...]
    preserved_paths: tuple[Path, ...]


def _thread_lock(path: Path) -> threading.RLock:
    key = os.path.normcase(str(path.resolve(strict=False)))
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


def _normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def _validate_pack_paths(paths: PackPaths) -> None:
    try:
        expected = type(paths).from_root(paths.root)
        field_names = tuple(expected.__dataclass_fields__)
    except (AttributeError, TypeError) as exc:
        raise KnowledgeStateMigrationError("pack_paths_invalid") from exc
    for name in field_names:
        actual_path = getattr(paths, name, None)
        expected_path = getattr(expected, name)
        if not isinstance(actual_path, Path):
            raise KnowledgeStateMigrationError("pack_paths_invalid")
        if _normalized_path(actual_path) != _normalized_path(expected_path):
            raise KnowledgeStateMigrationError("pack_paths_invalid")


def _assert_safe_directory(path: Path) -> None:
    if not path.exists():
        return
    try:
        value = path.lstat()
    except OSError as exc:
        raise KnowledgeStateMigrationError("managed_path_unsafe") from exc
    if path.is_symlink() or is_reparse(path) or not stat.S_ISDIR(value.st_mode):
        raise KnowledgeStateMigrationError("managed_path_unsafe")


def _safe_relative_parts(path: Path, root: Path) -> tuple[str, ...]:
    root = Path(os.path.abspath(root))
    target = Path(os.path.abspath(path))
    try:
        return target.relative_to(root).parts
    except ValueError as exc:
        raise KnowledgeStateMigrationError("managed_path_unsafe") from exc


def _ensure_safe_directory(path: Path, *, root: Path) -> None:
    current = Path(os.path.abspath(root))
    _assert_safe_directory(current)
    for part in _safe_relative_parts(path, current):
        current /= part
        if os.path.lexists(current):
            _assert_safe_directory(current)
            continue
        try:
            current.mkdir()
        except FileExistsError:
            pass
        _assert_safe_directory(current)


def _assert_windows_directory_handle(handle: int) -> None:
    information = _WindowsFileInformation()
    if not _WINDOWS_KERNEL32.GetFileInformationByHandle(
        handle, ctypes.byref(information)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    attributes = int(information.dwFileAttributes)
    if attributes & _WINDOWS_REPARSE_POINT or not attributes & 0x10:
        raise KnowledgeStateMigrationError("managed_path_unsafe")


def _guard_windows_directory_chain(
    path: Path,
    handles: list[int],
    guarded_paths: dict[str, int],
    *,
    create: bool,
) -> None:
    if os.name != "nt":
        return
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        key = _normalized_path(current)
        if key in guarded_paths:
            continue
        if not os.path.lexists(current):
            if not create:
                raise KnowledgeStateMigrationError("managed_path_unsafe")
            current.mkdir()
        handle = _WINDOWS_KERNEL32.CreateFileW(
            str(current),
            0x00000001 | 0x00000020 | 0x00000080,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,
            0x02000000 | 0x00200000,
            None,
        )
        if handle == _WINDOWS_INVALID_HANDLE:
            raise KnowledgeStateMigrationError("managed_path_unsafe")
        try:
            _assert_windows_directory_handle(handle)
        except Exception:
            _WINDOWS_KERNEL32.CloseHandle(handle)
            raise
        handles.append(handle)
        guarded_paths[key] = handle


def _close_windows_directory_guards(handles: list[int]) -> None:
    if os.name != "nt":
        return
    for handle in reversed(handles):
        _WINDOWS_KERNEL32.CloseHandle(handle)
    handles.clear()


def _assert_safe_file(path: Path) -> None:
    if not os.path.lexists(path):
        return
    try:
        value = path.lstat()
    except OSError as exc:
        raise KnowledgeStateMigrationError("managed_path_unsafe") from exc
    if (
        path.is_symlink()
        or is_reparse(path)
        or not stat.S_ISREG(value.st_mode)
        or value.st_nlink != 1
    ):
        raise KnowledgeStateMigrationError("managed_path_unsafe")


def _open_posix_directory(path: Path, *, root: Path, create: bool) -> int:
    root_path = Path(os.path.abspath(root))
    parts = _safe_relative_parts(path, root_path)
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(root_path, flags)
    try:
        for part in parts:
            try:
                child = os.open(part, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, dir_fd=descriptor)
                child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _read_safe_bytes(path: Path, *, root: Path) -> bytes:
    if os.name == "nt":
        _assert_safe_file(path)
        return path.read_bytes()
    directory = _open_posix_directory(path.parent, root=root, create=False)
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path.name, flags, dir_fd=directory)
        value = os.fstat(descriptor)
        if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
            raise KnowledgeStateMigrationError("managed_path_unsafe")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)


def _safe_unlink(path: Path, *, root: Path) -> None:
    if os.name == "nt":
        path.unlink(missing_ok=True)
        return
    directory = _open_posix_directory(path.parent, root=root, create=False)
    try:
        try:
            os.unlink(path.name, dir_fd=directory)
        except FileNotFoundError:
            pass
        os.fsync(directory)
    finally:
        os.close(directory)


def _sync_safe_directory(path: Path, *, root: Path) -> None:
    if os.name == "nt":
        _fsync_directory(path)
        return
    descriptor = _open_posix_directory(path, root=root, create=False)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _flush_windows_directory(path: Path) -> None:
    handle = _WINDOWS_KERNEL32.CreateFileW(
        str(path),
        0x40000000,
        0x00000001 | 0x00000002 | 0x00000004,
        None,
        3,
        0x02000000,
        None,
    )
    if handle == _WINDOWS_INVALID_HANDLE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not _WINDOWS_KERNEL32.FlushFileBuffers(handle):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        _WINDOWS_KERNEL32.CloseHandle(handle)


def _fsync_directory(
    path: Path,
    *,
    windows_flusher: Callable[[Path], None] | None = None,
) -> None:
    if os.name == "nt":
        (windows_flusher or _flush_windows_directory)(path)
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(
    path: Path,
    data: bytes,
    *,
    root: Path,
    after_replace: Callable[[], None] | None = None,
    windows_directory_handle: int | None = None,
    before_write: Callable[[], None] | None = None,
) -> None:
    if os.name == "nt":
        _ensure_safe_directory(path.parent, root=root)
        _assert_safe_file(path)
        _atomic_write_windows(
            path,
            data,
            after_replace=after_replace,
            directory_handle=windows_directory_handle,
            before_write=before_write,
        )
        return
    directory = _open_posix_directory(path.parent, root=root, create=True)
    temporary = f".{path.name}.{uuid.uuid4().hex}.tmp"
    descriptor: int | None = None
    replaced = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o600, dir_fd=directory)
        if before_write is not None:
            before_write()
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written == 0:
                raise OSError("short migration state write")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(
            temporary,
            path.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
        )
        replaced = True
        if after_replace is not None:
            after_replace()
        os.fsync(directory)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if not replaced:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
            except OSError:
                pass
        os.close(directory)


def _atomic_write_windows(
    path: Path,
    data: bytes,
    *,
    after_replace: Callable[[], None] | None,
    directory_handle: int | None,
    before_write: Callable[[], None] | None,
) -> None:
    if directory_handle is None:
        raise KnowledgeStateMigrationError("managed_path_unsafe")
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    handle = _WINDOWS_KERNEL32.CreateFileW(
        str(temporary),
        0x40000000 | 0x00010000,
        0x00000004,
        None,
        1,
        0x00000080 | 0x00200000,
        None,
    )
    if handle == _WINDOWS_INVALID_HANDLE:
        raise ctypes.WinError(ctypes.get_last_error())
    renamed = False
    try:
        if before_write is not None:
            before_write()
        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + 0xFFFFFFFF]
            buffer = ctypes.create_string_buffer(chunk)
            written = wintypes.DWORD()
            if not _WINDOWS_KERNEL32.WriteFile(
                handle,
                buffer,
                len(chunk),
                ctypes.byref(written),
                None,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            if written.value == 0:
                raise OSError("short migration state write")
            offset += written.value
        if not _WINDOWS_KERNEL32.FlushFileBuffers(handle):
            raise ctypes.WinError(ctypes.get_last_error())
        destination = "\\??\\" + str(path)

        class _WindowsRenameInfo(ctypes.Structure):
            _fields_ = [
                ("ReplaceIfExists", wintypes.DWORD),
                ("RootDirectory", wintypes.HANDLE),
                ("FileNameLength", wintypes.DWORD),
                ("FileName", ctypes.c_wchar * (len(destination) + 1)),
            ]

        rename = _WindowsRenameInfo()
        rename.ReplaceIfExists = 1
        rename.RootDirectory = None
        rename.FileNameLength = len(destination.encode("utf-16-le"))
        rename.FileName = destination
        if not _WINDOWS_KERNEL32.SetFileInformationByHandle(
            handle,
            3,
            ctypes.byref(rename),
            _WindowsRenameInfo.FileName.offset + rename.FileNameLength + 2,
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        renamed = True
        if after_replace is not None:
            after_replace()
        _fsync_directory(path.parent)
    finally:
        _WINDOWS_KERNEL32.CloseHandle(handle)
        if not renamed:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _canonical_json(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _load_state_file(
    path: Path, *, active: bool, root: Path
) -> tuple[bytes | None, dict[str, Any] | None]:
    try:
        raw = _read_safe_bytes(path, root=root)
        value = json.loads(raw.decode("utf-8"))
    except FileNotFoundError:
        return None, None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KnowledgeStateMigrationError("state_invalid") from exc
    required = {"schema_version", "packs"}
    if active:
        required.add("generation")
    if (
        not isinstance(value, dict)
        or set(value) != required
        or value.get("schema_version") != "1.0"
        or not isinstance(value.get("packs"), dict)
        or (
            active
            and (
                not isinstance(value.get("generation"), int)
                or value["generation"] < 0
            )
        )
    ):
        raise KnowledgeStateMigrationError("state_invalid")
    return raw, value


def _relative_to_root(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _path_from_marker(value: object, root: Path) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
    ):
        raise KnowledgeStateMigrationError("marker_invalid")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise KnowledgeStateMigrationError("marker_invalid")
    absolute_root = Path(os.path.abspath(root)).resolve(strict=False)
    candidate = absolute_root.joinpath(*relative.parts)
    canonical = candidate.resolve(strict=False)
    try:
        canonical.relative_to(absolute_root)
    except ValueError as exc:
        raise KnowledgeStateMigrationError("marker_invalid") from exc
    return canonical


def _load_marker(marker: Path, root: Path) -> MigrationResult | None:
    try:
        value = json.loads(_read_safe_bytes(marker, root=root).decode("utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != "1.0"
            or value.get("migration") != "knowledge-pack-identity-v1"
            or not isinstance(value.get("deactivated_pack_ids"), list)
            or not isinstance(value.get("preserved_paths"), list)
        ):
            raise ValueError("invalid marker")
        deactivated = tuple(value["deactivated_pack_ids"])
        if (
            not deactivated
            or any(not isinstance(item, str) for item in deactivated)
            or not set(deactivated).issubset(LEGACY_KNOWLEDGE_PACK_IDS)
            or deactivated != tuple(sorted(set(deactivated)))
        ):
            raise ValueError("invalid marker identities")
        backup_dir = _path_from_marker(value.get("backup_dir"), root)
        expected_backup_parent = (
            Path(os.path.abspath(root)) / "state" / _BACKUP_ROOT
        ).resolve(strict=False)
        if (
            backup_dir.parent != expected_backup_parent
            or re.fullmatch(r"[0-9a-f]{32}", backup_dir.name) is None
        ):
            raise ValueError("invalid marker backup")
        preserved = tuple(
            _path_from_marker(item, root) for item in value["preserved_paths"]
        )
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise KnowledgeStateMigrationError("marker_invalid") from exc
    return MigrationResult(False, backup_dir, deactivated, preserved)


def _marker_backup_is_valid(result: MigrationResult, *, root: Path) -> bool:
    backup_dir = result.backup_dir
    if backup_dir is None or not backup_dir.is_dir():
        return False
    try:
        _assert_safe_directory(backup_dir)
        backed_up_ids: set[str] = set()
        for name, active in (
            ("active.json", True),
            ("installed-packs.json", False),
        ):
            _, value = _load_state_file(
                backup_dir / name,
                active=active,
                root=root,
            )
            if value is not None:
                backed_up_ids.update(
                    set(value["packs"]).intersection(LEGACY_KNOWLEDGE_PACK_IDS)
                )
    except KnowledgeStateMigrationError:
        return False
    return set(result.deactivated_pack_ids).issubset(backed_up_ids)


def _preserved_paths(paths: PackPaths, legacy_ids: set[str]) -> tuple[Path, ...]:
    preserved: list[Path] = []
    if paths.cache.exists():
        preserved.append(paths.cache)
    for root in (paths.store, paths.overrides):
        preserved.extend(
            root / pack_id
            for pack_id in sorted(legacy_ids)
            if (root / pack_id).exists()
        )
    return tuple(preserved)


def _restore_state(
    path: Path,
    raw: bytes | None,
    *,
    root: Path,
    windows_directory_handle: int | None = None,
) -> None:
    if raw is None:
        _safe_unlink(path, root=root)
    else:
        _atomic_write(
            path,
            raw,
            root=root,
            windows_directory_handle=windows_directory_handle,
        )


def migrate_legacy_knowledge_state(
    paths: PackPaths,
    *,
    failure_injector: Callable[[str], None] | None = None,
) -> MigrationResult:
    """Deactivate exact legacy IDs while retaining all legacy data for recovery."""

    _validate_pack_paths(paths)
    local_lock = _thread_lock(paths.manager_lock)
    with local_lock:
        directory_guards: list[int] = []
        guarded_paths: dict[str, int] = {}
        try:
            with exclusive_file_lock(paths.manager_lock):
                _assert_safe_directory(paths.root)
                _assert_safe_directory(paths.state)
                if not paths.state.exists():
                    return MigrationResult(False, None, (), ())
                _guard_windows_directory_chain(
                    paths.state,
                    directory_guards,
                    guarded_paths,
                    create=False,
                )
                state_directory_handle = guarded_paths.get(
                    _normalized_path(paths.state)
                )
                active_raw, active = _load_state_file(
                    paths.active,
                    active=True,
                    root=paths.root,
                )
                installed_raw, installed = _load_state_file(
                    paths.installed_metadata,
                    active=False,
                    root=paths.root,
                )
                active_ids = (
                    set(active["packs"]).intersection(LEGACY_KNOWLEDGE_PACK_IDS)
                    if active is not None
                    else set()
                )
                installed_ids = (
                    set(installed["packs"]).intersection(LEGACY_KNOWLEDGE_PACK_IDS)
                    if installed is not None
                    else set()
                )
                legacy_ids = active_ids | installed_ids
                marker = paths.state / _MARKER_NAME
                try:
                    existing = _load_marker(marker, paths.root)
                except KnowledgeStateMigrationError as exc:
                    if exc.reason != "marker_invalid":
                        raise
                    existing = None
                existing_backup_valid = False
                if not legacy_ids and existing is not None:
                    try:
                        if os.name == "nt" and existing.backup_dir is not None:
                            _guard_windows_directory_chain(
                                existing.backup_dir,
                                directory_guards,
                                guarded_paths,
                                create=False,
                            )
                        existing_backup_valid = _marker_backup_is_valid(
                            existing,
                            root=paths.root,
                        )
                    except KnowledgeStateMigrationError:
                        existing_backup_valid = False
                if (
                    not legacy_ids
                    and existing is not None
                    and existing_backup_valid
                ):
                    return existing
                if not legacy_ids:
                    return MigrationResult(False, None, (), ())

                replacements: list[tuple[Path, bytes]] = []
                if active_ids and active is not None:
                    active_after = dict(active)
                    active_after["packs"] = {
                        pack_id: item
                        for pack_id, item in active["packs"].items()
                        if pack_id not in active_ids
                    }
                    active_after["generation"] = active["generation"] + 1
                    replacements.append((paths.active, _canonical_json(active_after)))
                if installed_ids and installed is not None:
                    installed_after = dict(installed)
                    installed_after["packs"] = {
                        pack_id: item
                        for pack_id, item in installed["packs"].items()
                        if pack_id not in installed_ids
                    }
                    replacements.append(
                        (paths.installed_metadata, _canonical_json(installed_after))
                    )

                backup_dir = paths.state / _BACKUP_ROOT / uuid.uuid4().hex
                if os.name == "nt":
                    _guard_windows_directory_chain(
                        backup_dir,
                        directory_guards,
                        guarded_paths,
                        create=True,
                    )
                else:
                    backup_descriptor = _open_posix_directory(
                        backup_dir,
                        root=paths.state,
                        create=True,
                    )
                    os.close(backup_descriptor)
                backup_directory_handle = guarded_paths.get(
                    _normalized_path(backup_dir)
                )
                def before_first_backup_write() -> None:
                    if failure_injector is None:
                        return
                    try:
                        failure_injector(
                            "knowledge_migration.before_first_backup_write"
                        )
                    except Exception as exc:
                        raise KnowledgeStateMigrationError(
                            "failure_injected"
                        ) from exc

                first_backup = True
                for source, raw in (
                    (paths.active, active_raw),
                    (paths.installed_metadata, installed_raw),
                ):
                    if raw is not None:
                        _atomic_write(
                            backup_dir / source.name,
                            raw,
                            root=paths.state,
                            windows_directory_handle=backup_directory_handle,
                            before_write=(
                                before_first_backup_write if first_backup else None
                            ),
                        )
                        first_backup = False
                _sync_safe_directory(backup_dir, root=paths.state)

                preserved = _preserved_paths(paths, legacy_ids)
                marker_value = {
                    "schema_version": "1.0",
                    "migration": "knowledge-pack-identity-v1",
                    "backup_dir": _relative_to_root(backup_dir, paths.root),
                    "deactivated_pack_ids": sorted(legacy_ids),
                    "preserved_paths": [
                        _relative_to_root(path, paths.root) for path in preserved
                    ],
                }
                if failure_injector is not None:
                    try:
                        failure_injector("knowledge_migration.before_state_replace")
                    except Exception as exc:
                        raise KnowledgeStateMigrationError("failure_injected") from exc

                originals = {
                    paths.active: active_raw,
                    paths.installed_metadata: installed_raw,
                }
                replaced: list[Path] = []
                marker_replaced = False

                def record_marker_replace() -> None:
                    nonlocal marker_replaced
                    marker_replaced = True

                try:
                    for path, raw in replacements:
                        _atomic_write(
                            path,
                            raw,
                            root=paths.root,
                            after_replace=lambda path=path: replaced.append(path),
                            windows_directory_handle=state_directory_handle,
                        )
                    _atomic_write(
                        marker,
                        _canonical_json(marker_value),
                        root=paths.root,
                        after_replace=record_marker_replace,
                        windows_directory_handle=state_directory_handle,
                    )
                except Exception:
                    compensation_errors: list[OSError] = []
                    if marker_replaced:
                        try:
                            _safe_unlink(marker, root=paths.root)
                        except OSError as exc:
                            compensation_errors.append(exc)
                    for path in reversed(replaced):
                        try:
                            _restore_state(
                                path,
                                originals[path],
                                root=paths.root,
                                windows_directory_handle=state_directory_handle,
                            )
                        except OSError as exc:
                            compensation_errors.append(exc)
                    if compensation_errors:
                        raise KnowledgeStateMigrationError(
                            "compensation_failed"
                        ) from compensation_errors[0]
                    raise
                return MigrationResult(
                    True,
                    backup_dir,
                    tuple(sorted(legacy_ids)),
                    preserved,
                )
        except KnowledgeStateMigrationError:
            raise
        except UnsafeLockPath as exc:
            raise KnowledgeStateMigrationError("manager_lock_unsafe") from exc
        except FileLockFailure as exc:
            raise KnowledgeStateMigrationError("manager_lock_failed") from exc
        except OSError as exc:
            raise KnowledgeStateMigrationError("filesystem_operation_failed") from exc
        finally:
            _close_windows_directory_guards(directory_guards)


__all__ = [
    "KnowledgeStateMigrationError",
    "LEGACY_KNOWLEDGE_PACK_IDS",
    "MigrationResult",
    "migrate_legacy_knowledge_state",
]

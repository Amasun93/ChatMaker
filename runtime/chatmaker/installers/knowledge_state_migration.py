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

    class _UnicodeString(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.USHORT),
            ("MaximumLength", wintypes.USHORT),
            ("Buffer", wintypes.LPWSTR),
        ]

    class _ObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.ULONG),
            ("RootDirectory", wintypes.HANDLE),
            ("ObjectName", ctypes.POINTER(_UnicodeString)),
            ("Attributes", wintypes.ULONG),
            ("SecurityDescriptor", wintypes.LPVOID),
            ("SecurityQualityOfService", wintypes.LPVOID),
        ]

    class _IoStatusValue(ctypes.Union):
        _fields_ = [
            ("Status", wintypes.LONG),
            ("Pointer", wintypes.LPVOID),
        ]

    class _IoStatusBlock(ctypes.Structure):
        _anonymous_ = ("Value",)
        _fields_ = [
            ("Value", _IoStatusValue),
            ("Information", ctypes.c_size_t),
        ]

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
    _WINDOWS_KERNEL32.ReadFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    _WINDOWS_KERNEL32.ReadFile.restype = wintypes.BOOL
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
    _WINDOWS_NTDLL = ctypes.WinDLL("ntdll")
    _WINDOWS_NTDLL.NtCreateFile.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        ctypes.POINTER(_ObjectAttributes),
        ctypes.POINTER(_IoStatusBlock),
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _WINDOWS_NTDLL.NtCreateFile.restype = wintypes.LONG
    _WINDOWS_NTDLL.NtSetInformationFile.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_IoStatusBlock),
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    _WINDOWS_NTDLL.NtSetInformationFile.restype = wintypes.LONG
    _WINDOWS_NTDLL.RtlNtStatusToDosError.argtypes = [wintypes.LONG]
    _WINDOWS_NTDLL.RtlNtStatusToDosError.restype = wintypes.ULONG


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


def _windows_nt_path(path: Path) -> str:
    value = str(Path(os.path.abspath(path)))
    if value.startswith("\\\\?\\UNC\\"):
        return "\\??\\UNC\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return "\\??\\" + value[4:]
    if value.startswith("\\\\"):
        return "\\??\\UNC\\" + value[2:]
    return "\\??\\" + value


def _raise_nt_status(status: int, name: str) -> None:
    code = int(_WINDOWS_NTDLL.RtlNtStatusToDosError(status))
    message = ctypes.FormatError(code)
    if code in {2, 3}:
        raise FileNotFoundError(code, message, name)
    raise OSError(code, message, name)


def _nt_create_file(
    root_handle: int | None,
    name: str,
    *,
    desired_access: int,
    disposition: int,
    options: int,
    file_attributes: int = 0x00000080,
    share_access: int = 0x00000001 | 0x00000002 | 0x00000004,
) -> int:
    name_buffer = ctypes.create_unicode_buffer(name)
    encoded_length = len(name.encode("utf-16-le"))
    unicode_name = _UnicodeString(
        encoded_length,
        encoded_length + 2,
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    attributes = _ObjectAttributes(
        ctypes.sizeof(_ObjectAttributes),
        root_handle,
        ctypes.pointer(unicode_name),
        0x00000040 | 0x00001000,
        None,
        None,
    )
    io_status = _IoStatusBlock()
    handle = wintypes.HANDLE()
    status = _WINDOWS_NTDLL.NtCreateFile(
        ctypes.byref(handle),
        desired_access,
        ctypes.byref(attributes),
        ctypes.byref(io_status),
        None,
        file_attributes,
        share_access,
        disposition,
        options,
        None,
        0,
    )
    if status < 0:
        _raise_nt_status(status, name)
    return int(handle.value)


def _assert_windows_directory_handle(handle: int) -> None:
    information = _WindowsFileInformation()
    if not _WINDOWS_KERNEL32.GetFileInformationByHandle(
        handle, ctypes.byref(information)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    attributes = int(information.dwFileAttributes)
    if attributes & _WINDOWS_REPARSE_POINT or not attributes & 0x10:
        raise KnowledgeStateMigrationError("managed_path_unsafe")


def _assert_windows_file_handle(handle: int) -> None:
    information = _WindowsFileInformation()
    if not _WINDOWS_KERNEL32.GetFileInformationByHandle(
        handle, ctypes.byref(information)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    attributes = int(information.dwFileAttributes)
    if (
        attributes & _WINDOWS_REPARSE_POINT
        or attributes & 0x10
        or int(information.nNumberOfLinks) != 1
    ):
        raise KnowledgeStateMigrationError("managed_path_unsafe")


def _windows_read_relative(directory_handle: int, name: str) -> bytes:
    handle = _nt_create_file(
        directory_handle,
        name,
        desired_access=0x80000000 | 0x00100000,
        disposition=1,
        options=0x00000040 | 0x00000020 | 0x00200000,
    )
    try:
        _assert_windows_file_handle(handle)
        chunks: list[bytes] = []
        while True:
            buffer = ctypes.create_string_buffer(64 * 1024)
            read = wintypes.DWORD()
            if not _WINDOWS_KERNEL32.ReadFile(
                handle,
                buffer,
                len(buffer),
                ctypes.byref(read),
                None,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            if read.value == 0:
                return b"".join(chunks)
            chunks.append(buffer.raw[: read.value])
    finally:
        _WINDOWS_KERNEL32.CloseHandle(handle)


def _windows_rename_relative(
    handle: int,
    directory_handle: int,
    name: str,
) -> None:
    class _FileRenameInformation(ctypes.Structure):
        _fields_ = [
            ("ReplaceIfExists", ctypes.c_ubyte),
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.ULONG),
            ("FileName", ctypes.c_wchar * (len(name) + 1)),
        ]

    rename = _FileRenameInformation()
    rename.ReplaceIfExists = 1
    rename.RootDirectory = directory_handle
    rename.FileNameLength = len(name.encode("utf-16-le"))
    rename.FileName = name
    io_status = _IoStatusBlock()
    status = _WINDOWS_NTDLL.NtSetInformationFile(
        handle,
        ctypes.byref(io_status),
        ctypes.byref(rename),
        _FileRenameInformation.FileName.offset + rename.FileNameLength + 2,
        10,
    )
    if status < 0:
        _raise_nt_status(status, name)


def _windows_unlink_relative(directory_handle: int, name: str) -> None:
    try:
        handle = _nt_create_file(
            directory_handle,
            name,
            desired_access=0x00000080 | 0x00010000 | 0x00100000,
            disposition=1,
            options=0x00000040 | 0x00000020 | 0x00200000,
        )
    except FileNotFoundError:
        return
    try:
        _assert_windows_file_handle(handle)

        class _FileDispositionInformation(ctypes.Structure):
            _fields_ = [("DeleteFile", ctypes.c_ubyte)]

        disposition = _FileDispositionInformation(1)
        if not _WINDOWS_KERNEL32.SetFileInformationByHandle(
            handle,
            4,
            ctypes.byref(disposition),
            ctypes.sizeof(disposition),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        _WINDOWS_KERNEL32.CloseHandle(handle)


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
    anchor_key = _normalized_path(current)
    if anchor_key not in guarded_paths:
        anchor_handle = _nt_create_file(
            None,
            _windows_nt_path(current),
            desired_access=0x80000000 | 0x00100000,
            disposition=1,
            options=0x00000001 | 0x00000020 | 0x00200000,
        )
        try:
            _assert_windows_directory_handle(anchor_handle)
        except Exception:
            _WINDOWS_KERNEL32.CloseHandle(anchor_handle)
            raise
        handles.append(anchor_handle)
        guarded_paths[anchor_key] = anchor_handle
    parent_handle = guarded_paths[anchor_key]
    for part in absolute.parts[1:]:
        current /= part
        key = _normalized_path(current)
        if key in guarded_paths:
            parent_handle = guarded_paths[key]
            continue
        desired_access = 0x80000000 | 0x00100000
        if current == absolute:
            desired_access |= 0x40000000
        handle = _nt_create_file(
            parent_handle,
            part,
            desired_access=desired_access,
            disposition=3 if create else 1,
            options=0x00000001 | 0x00000020 | 0x00200000,
            file_attributes=0x10,
        )
        try:
            _assert_windows_directory_handle(handle)
        except Exception:
            _WINDOWS_KERNEL32.CloseHandle(handle)
            raise
        handles.append(handle)
        guarded_paths[key] = handle
        parent_handle = handle


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


def _read_safe_bytes(
    path: Path,
    *,
    root: Path,
    windows_directory_handle: int | None = None,
) -> bytes:
    if os.name == "nt":
        if windows_directory_handle is None:
            raise KnowledgeStateMigrationError("managed_path_unsafe")
        return _windows_read_relative(windows_directory_handle, path.name)
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


def _safe_unlink(
    path: Path,
    *,
    root: Path,
    windows_directory_handle: int | None = None,
) -> None:
    if os.name == "nt":
        if windows_directory_handle is None:
            raise KnowledgeStateMigrationError("managed_path_unsafe")
        _windows_unlink_relative(windows_directory_handle, path.name)
        _fsync_directory(path.parent, windows_handle=windows_directory_handle)
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


def _sync_safe_directory(
    path: Path,
    *,
    root: Path,
    windows_handle: int | None = None,
) -> None:
    if os.name == "nt":
        _fsync_directory(path, windows_handle=windows_handle)
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


def _flush_windows_handle(handle: int) -> None:
    if not _WINDOWS_KERNEL32.FlushFileBuffers(handle):
        raise ctypes.WinError(ctypes.get_last_error())


def _fsync_directory(
    path: Path,
    *,
    windows_flusher: Callable[[Path], None] | None = None,
    windows_handle: int | None = None,
) -> None:
    if os.name == "nt":
        if windows_flusher is not None:
            windows_flusher(path)
        elif windows_handle is not None:
            _flush_windows_handle(windows_handle)
        else:
            _flush_windows_directory(path)
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
    before_temp_create: Callable[[], None] | None = None,
    before_rename: Callable[[], None] | None = None,
) -> None:
    if os.name == "nt":
        _atomic_write_windows(
            path,
            data,
            after_replace=after_replace,
            directory_handle=windows_directory_handle,
            before_write=before_write,
            before_temp_create=before_temp_create,
            before_rename=before_rename,
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
    before_temp_create: Callable[[], None] | None,
    before_rename: Callable[[], None] | None,
) -> None:
    if directory_handle is None:
        raise KnowledgeStateMigrationError("managed_path_unsafe")
    temporary = f".{path.name}.{uuid.uuid4().hex}.tmp"
    if before_temp_create is not None:
        before_temp_create()
    handle = _nt_create_file(
        directory_handle,
        temporary,
        desired_access=0x40000000 | 0x00010000 | 0x00100000,
        disposition=2,
        options=0x00000040 | 0x00000020 | 0x00200000,
        share_access=0x00000004,
    )
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
        if before_rename is not None:
            before_rename()
        _windows_rename_relative(handle, directory_handle, path.name)
        renamed = True
        if after_replace is not None:
            after_replace()
        _fsync_directory(path.parent, windows_handle=directory_handle)
    finally:
        _WINDOWS_KERNEL32.CloseHandle(handle)
        if not renamed:
            try:
                _windows_unlink_relative(directory_handle, temporary)
            except OSError:
                pass


def _canonical_json(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _load_state_file(
    path: Path,
    *,
    active: bool,
    root: Path,
    windows_directory_handle: int | None = None,
) -> tuple[bytes | None, dict[str, Any] | None]:
    try:
        raw = _read_safe_bytes(
            path,
            root=root,
            windows_directory_handle=windows_directory_handle,
        )
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


def _load_marker(
    marker: Path,
    root: Path,
    *,
    windows_directory_handle: int | None = None,
) -> MigrationResult | None:
    try:
        value = json.loads(
            _read_safe_bytes(
                marker,
                root=root,
                windows_directory_handle=windows_directory_handle,
            ).decode("utf-8")
        )
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


def _marker_backup_is_valid(
    result: MigrationResult,
    *,
    root: Path,
    windows_directory_handle: int | None = None,
) -> bool:
    backup_dir = result.backup_dir
    if backup_dir is None:
        return False
    if os.name == "nt":
        if windows_directory_handle is None:
            return False
    elif not backup_dir.is_dir():
        return False
    try:
        if os.name != "nt":
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
                windows_directory_handle=windows_directory_handle,
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
        _safe_unlink(
            path,
            root=root,
            windows_directory_handle=windows_directory_handle,
        )
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
                def inject(point: str) -> None:
                    if failure_injector is None:
                        return
                    try:
                        failure_injector(point)
                    except Exception as exc:
                        raise KnowledgeStateMigrationError(
                            "failure_injected"
                        ) from exc

                if os.name == "nt":
                    try:
                        _guard_windows_directory_chain(
                            paths.state,
                            directory_guards,
                            guarded_paths,
                            create=False,
                        )
                    except FileNotFoundError:
                        return MigrationResult(False, None, (), ())
                else:
                    _assert_safe_directory(paths.root)
                    _assert_safe_directory(paths.state)
                    if not paths.state.exists():
                        return MigrationResult(False, None, (), ())
                state_directory_handle = guarded_paths.get(
                    _normalized_path(paths.state)
                )
                inject("knowledge_migration.before_state_read")
                active_raw, active = _load_state_file(
                    paths.active,
                    active=True,
                    root=paths.root,
                    windows_directory_handle=state_directory_handle,
                )
                installed_raw, installed = _load_state_file(
                    paths.installed_metadata,
                    active=False,
                    root=paths.root,
                    windows_directory_handle=state_directory_handle,
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
                    existing = _load_marker(
                        marker,
                        paths.root,
                        windows_directory_handle=state_directory_handle,
                    )
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
                        existing_backup_handle = guarded_paths.get(
                            _normalized_path(existing.backup_dir)
                        )
                        existing_backup_valid = _marker_backup_is_valid(
                            existing,
                            root=paths.root,
                            windows_directory_handle=existing_backup_handle,
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
                    inject("knowledge_migration.before_first_backup_write")

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
                            before_temp_create=(
                                lambda: inject(
                                    "knowledge_migration.before_backup_temp_create"
                                )
                                if first_backup
                                else None
                            ),
                        )
                        first_backup = False
                _sync_safe_directory(
                    backup_dir,
                    root=paths.state,
                    windows_handle=backup_directory_handle,
                )

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
                            before_rename=lambda: inject(
                                "knowledge_migration.before_state_rename"
                            ),
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
                            _safe_unlink(
                                marker,
                                root=paths.root,
                                windows_directory_handle=state_directory_handle,
                            )
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

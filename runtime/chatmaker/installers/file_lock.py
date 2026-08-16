"""Shared no-follow, single-link interprocess lock primitives."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import stat


_WINDOWS_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)


class UnsafeLockPath(OSError):
    pass


class FileLockFailure(OSError):
    pass


def is_reparse(path: Path) -> bool:
    try:
        return bool(getattr(path.lstat(), "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise UnsafeLockPath("lock path identity is unreadable") from exc


def _unsafe_existing_file(path: Path) -> bool:
    if not os.path.lexists(path):
        return False
    if path.is_symlink() or is_reparse(path):
        return True
    try:
        value = path.lstat()
    except OSError:
        return True
    return not stat.S_ISREG(value.st_mode) or value.st_nlink != 1


def _unsafe_parent(path: Path) -> bool:
    if not path.exists() or path.is_symlink() or is_reparse(path):
        return True
    try:
        value = path.lstat()
    except OSError:
        return True
    return not stat.S_ISDIR(value.st_mode)


def _ensure_safe_directory(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    chain = tuple(reversed((absolute, *absolute.parents)))
    for directory in chain:
        if os.path.lexists(directory):
            if _unsafe_parent(directory):
                raise UnsafeLockPath("unsafe lock parent")
            continue
        try:
            directory.mkdir()
        except FileExistsError:
            pass
        if _unsafe_parent(directory):
            raise UnsafeLockPath("unsafe lock parent")
    if any(_unsafe_parent(directory) for directory in chain):
        raise UnsafeLockPath("unsafe lock parent")


@contextmanager
def exclusive_file_lock(path: Path):
    """Lock one regular, single-link file without following a final link."""

    path = Path(os.path.abspath(path))
    descriptor: int | None = None
    handle = None
    locked = False
    try:
        try:
            _ensure_safe_directory(path.parent)
            if _unsafe_existing_file(path):
                raise UnsafeLockPath("unsafe lock path")
            flags = os.O_CREAT | os.O_RDWR
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(path, flags, 0o600)
            opened = os.fstat(descriptor)
            try:
                named = path.lstat()
            except OSError as exc:
                raise UnsafeLockPath("lock path disappeared") from exc
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or named.st_nlink != 1
                or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
                or path.is_symlink()
                or is_reparse(path)
            ):
                raise UnsafeLockPath("unsafe lock identity")
            handle = os.fdopen(descriptor, "a+b")
            descriptor = None
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
        except UnsafeLockPath:
            raise
        except OSError as exc:
            raise FileLockFailure("file lock failed") from exc

        yield
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
        elif descriptor is not None:
            os.close(descriptor)


__all__ = [
    "FileLockFailure",
    "UnsafeLockPath",
    "exclusive_file_lock",
    "is_reparse",
]

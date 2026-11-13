"""OS-owned locks release automatically even when a preparation is killed."""
from contextlib import contextmanager
import os
from pathlib import Path
from time import sleep


def rename_directory(source: Path, destination: Path) -> None:
    """Give a just-extracted directory a moment to clear transient file locks."""
    for delay in (0.25, 0.5, 1.0):
        try:
            source.rename(destination)
            return
        except PermissionError:
            sleep(delay)
    source.rename(destination)


@contextmanager
def exclusive_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f'operation_in_progress:{path.name}') from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)

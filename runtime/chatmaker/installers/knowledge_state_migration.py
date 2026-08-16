"""One-time, non-destructive deactivation of pre-Knowledge pack identities."""

from __future__ import annotations

import json
import os
import stat
import tempfile
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
_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


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


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, data: bytes, *, root: Path) -> None:
    _ensure_safe_directory(path.parent, root=root)
    _assert_safe_file(path)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        _fsync_directory(path.parent)
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass


def _canonical_json(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _load_state_file(
    path: Path, *, active: bool
) -> tuple[bytes | None, dict[str, Any] | None]:
    _assert_safe_file(path)
    if not path.exists():
        return None, None
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
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
    if not isinstance(value, str):
        raise KnowledgeStateMigrationError("marker_invalid")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise KnowledgeStateMigrationError("marker_invalid")
    candidate = root.joinpath(*relative.parts)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise KnowledgeStateMigrationError("marker_invalid") from exc
    return candidate


def _load_marker(marker: Path, root: Path) -> MigrationResult | None:
    _assert_safe_file(marker)
    if not marker.exists():
        return None
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
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
            any(not isinstance(item, str) for item in deactivated)
            or not set(deactivated).issubset(LEGACY_KNOWLEDGE_PACK_IDS)
        ):
            raise ValueError("invalid marker identities")
        backup_dir = _path_from_marker(value.get("backup_dir"), root)
        preserved = tuple(
            _path_from_marker(item, root) for item in value["preserved_paths"]
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise KnowledgeStateMigrationError("marker_invalid") from exc
    return MigrationResult(False, backup_dir, deactivated, preserved)


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


def _restore_state(path: Path, raw: bytes | None, *, root: Path) -> None:
    if raw is None:
        path.unlink(missing_ok=True)
        _fsync_directory(path.parent)
    else:
        _atomic_write(path, raw, root=root)


def migrate_legacy_knowledge_state(
    paths: PackPaths,
    *,
    failure_injector: Callable[[str], None] | None = None,
) -> MigrationResult:
    """Deactivate exact legacy IDs while retaining all legacy data for recovery."""

    local_lock = _thread_lock(paths.manager_lock)
    with local_lock:
        try:
            with exclusive_file_lock(paths.manager_lock):
                _assert_safe_directory(paths.root)
                _assert_safe_directory(paths.state)
                marker = paths.state / _MARKER_NAME
                existing = _load_marker(marker, paths.root)
                if existing is not None:
                    return existing

                active_raw, active = _load_state_file(paths.active, active=True)
                installed_raw, installed = _load_state_file(
                    paths.installed_metadata, active=False
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
                _ensure_safe_directory(backup_dir, root=paths.state)
                for source, raw in (
                    (paths.active, active_raw),
                    (paths.installed_metadata, installed_raw),
                ):
                    if raw is not None:
                        _atomic_write(
                            backup_dir / source.name,
                            raw,
                            root=paths.state,
                        )
                _fsync_directory(backup_dir)

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
                try:
                    for path, raw in replacements:
                        _atomic_write(path, raw, root=paths.root)
                        replaced.append(path)
                    _atomic_write(
                        marker,
                        _canonical_json(marker_value),
                        root=paths.root,
                    )
                except Exception:
                    for path in reversed(replaced):
                        _restore_state(path, originals[path], root=paths.root)
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


__all__ = [
    "KnowledgeStateMigrationError",
    "LEGACY_KNOWLEDGE_PACK_IDS",
    "MigrationResult",
    "migrate_legacy_knowledge_state",
]

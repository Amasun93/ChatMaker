"""Locked, journaled, reversible installation transactions.

The transaction owns only the content declared in its changes.  A Skill is
owned as one directory; an MCP registration is owned as one key inside
``mcpServers``.  Full before-images remain available for explicit disaster
restore, while normal uninstall edits only those managed units.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
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


def _absolute(path: Path | str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        raise UnsafeInstallPath(f"install path must be absolute: {candidate}")
    return Path(os.path.abspath(candidate))


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


def _remove_path(path: Path) -> None:
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


def _path_hash(path: Path) -> str:
    if not _lexists(path):
        return _MISSING_HASH
    _assert_safe_tree(path)
    digest = hashlib.sha256(b"chatmaker:directory:v1\0")
    for current, directories, files in os.walk(path, followlinks=False):
        root = Path(current)
        directories.sort()
        files.sort()
        for directory in directories:
            relative = (root / directory).relative_to(path).as_posix()
            digest.update(b"d\0" + relative.encode("utf-8") + b"\0")
        for filename in files:
            item = root / filename
            relative = item.relative_to(path).as_posix()
            digest.update(b"f\0" + relative.encode("utf-8") + b"\0")
            with item.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest()


def _read_json_object(path: Path, *, missing_ok: bool = False) -> dict[str, Any]:
    if not _lexists(path):
        if missing_ok:
            return {}
        raise FileNotFoundError(path)
    _assert_safe_ancestors(path)
    if not path.is_file():
        raise UnsafeInstallPath(f"JSON target is not a regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
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
    finally:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    _write_bytes_atomic(path, _canonical_json(dict(value)))


def _atomic_backup(source: Path, destination: Path) -> None:
    _assert_safe_ancestors(source)
    _ensure_safe_directory(destination.parent)
    temporary = destination.with_name(f".{destination.name}-{uuid.uuid4().hex}.tmp")
    if _lexists(temporary):
        raise UnsafeInstallPath(f"backup staging collision: {temporary}")
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
    finally:
        if _lexists(temporary):
            _remove_path(temporary)


def _activate_staging(staging: Path, target: Path) -> None:
    """Activate a same-directory stage, with the established Windows fallback."""
    try:
        os.replace(staging, target)
    except PermissionError:
        if _lexists(target):
            raise
        shutil.copytree(staging, target)
        _remove_path(staging)


def _restore_full(target: Path, *, before_exists: bool, backup: str | None) -> None:
    _assert_safe_ancestors(target, include_final=False)
    if _lexists(target):
        _assert_safe_ancestors(target)
        _remove_path(target)
    if not before_exists:
        return
    if not backup:
        raise FileNotFoundError(f"missing before-image for {target}")
    source = _absolute(backup)
    _assert_safe_ancestors(source)
    if source.is_dir():
        _assert_safe_tree(source)
        shutil.copytree(source, target)
    elif source.is_file():
        _ensure_safe_directory(target.parent)
        shutil.copy2(source, target)
    else:
        raise FileNotFoundError(f"before-image is missing: {source}")


def _aggregate_hash(records: Sequence[Mapping[str, Any]]) -> str:
    values = sorted(
        ({"identity": str(item["identity"]), "hash": str(item["installed_hash"])} for item in records),
        key=lambda item: item["identity"],
    )
    return _json_hash(values)


def _path_token(identity: str) -> str:
    """Return a bounded filename token; managed names remain data, never paths."""
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


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
        if not _lexists(self.state_path):
            return None
        value = _read_json_object(self.state_path)
        if value.get("installation_id") != self.installation_id:
            raise InstallConflict("active installer state belongs to another installation")
        records = value.get("managed")
        if not isinstance(records, list):
            raise InstallConflict("active installer state is malformed")
        for record in records:
            if not isinstance(record, dict):
                raise InstallConflict("active installer record is malformed")
            self._validate_managed_record(record)
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
        journal_written = False
        previous_state = dict(active) if active is not None else None
        try:
            for index, item in enumerate(changed):
                self._inject("staging", {"identity": item.identity, "kind": item.kind})
                _ensure_safe_directory(item.target.parent)
                stage = item.target.parent / (
                    f".chatmaker-{transaction_id}-{index:03d}-{_path_token(item.identity)}.staging"
                )
                if _lexists(stage):
                    raise UnsafeInstallPath(f"install staging path already exists: {stage}")
                if item.kind == "skill":
                    assert item.source is not None
                    _assert_safe_tree(item.source)
                    shutil.copytree(item.source, stage)
                else:
                    current = _read_json_object(item.target, missing_ok=True)
                    servers = current.setdefault("mcpServers", {})
                    if not isinstance(servers, dict):
                        raise ValueError("mcpServers must be an object")
                    servers[str(item.server_key)] = dict(item.server or {})
                    _write_bytes_atomic(stage, _canonical_json(current))
                stages[item.identity] = stage

            _ensure_safe_directory(backup_root)
            for index, item in enumerate(changed):
                before_exists = _lexists(item.target)
                backup: str | None = None
                if before_exists:
                    _assert_safe_ancestors(item.target)
                    backup_path = backup_root / (
                        f"{index:03d}-{item.kind}-{_path_token(item.identity)}"
                    )
                    _atomic_backup(item.target, backup_path)
                    backup = str(backup_path)
                record: dict[str, Any] = {
                    "kind": item.kind,
                    "identity": item.identity,
                    "target": str(item.target),
                    "name": item.name,
                    "before_exists": before_exists,
                    "backup": backup,
                    "before_hash": self._current_hash(item),
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
            state = {
                "schema_version": "1.0",
                "installation_id": self.installation_id,
                "active_transaction_id": transaction_id,
                "managed_hash": managed_hash,
                "managed": managed_records,
            }
            journal = {
                "schema_version": "1.0",
                "transaction_id": transaction_id,
                "installation_id": self.installation_id,
                "status": "prepared",
                "created_at_ns": time.time_ns(),
                "previous_state": previous_state,
                "records": records,
                "managed_hash": managed_hash,
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
                    if _lexists(displaced_path):
                        raise UnsafeInstallPath(
                            f"install displacement path already exists: {displaced_path}"
                        )
                    if _lexists(target):
                        os.replace(target, displaced_path)
                        displaced[identity] = displaced_path
                    try:
                        _activate_staging(stages[identity], target)
                    except Exception:
                        if _lexists(displaced_path) and not _lexists(target):
                            os.replace(displaced_path, target)
                            displaced.pop(identity, None)
                        raise
                else:
                    self._inject(
                        "mcp_replacement", {"identity": identity, "target": str(target)}
                    )
                    os.replace(stages[identity], target)
                applied.append(record)

            self._inject(
                "verification", {"transaction_id": transaction_id, "records": records}
            )
            for item in changed:
                actual = self._current_hash(item)
                if actual != desired[item.identity]:
                    raise RuntimeError(f"installation verification failed: {item.identity}")

            journal["status"] = "committed"
            journal["committed_at_ns"] = time.time_ns()
            self._inject(
                "journal_replacement", {"transaction_id": transaction_id, "path": str(journal_path)}
            )
            _write_json_atomic(journal_path, journal)
            self._inject(
                "state_replacement", {"transaction_id": transaction_id, "path": str(self.state_path)}
            )
            _write_json_atomic(self.state_path, state)
            for path in displaced.values():
                _remove_path(path)
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
            for record in reversed(applied):
                identity = str(record["identity"])
                target = _absolute(record["target"])
                moved = displaced.get(identity)
                if moved is not None and _lexists(moved):
                    if _lexists(target):
                        _remove_path(target)
                    os.replace(moved, target)
                    displaced.pop(identity, None)
                else:
                    _restore_full(
                        target,
                        before_exists=bool(record["before_exists"]),
                        backup=record.get("backup"),
                    )
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
            for path in (*stages.values(), *displaced.values()):
                if _lexists(path):
                    _remove_path(path)

    def restore(self, transaction_id: str) -> TransactionResult:
        self._prepare_management_root()
        with exclusive_file_lock(self.lock_path):
            journal_path = self._journal_path(transaction_id)
            journal = _read_json_object(journal_path)
            status = str(journal.get("status"))
            if status in {"restored", "rolled_back"}:
                return TransactionResult(
                    True, "already_restored", transaction_id=transaction_id
                )
            if status != "committed":
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
            conflicts = []
            for record in journal.get("records", []):
                actual = self._current_hash(record)
                if actual != record["installed_hash"]:
                    conflicts.append(
                        {
                            "identity": str(record["identity"]),
                            "expected_hash": str(record["installed_hash"]),
                            "actual_hash": actual,
                        }
                    )
            if conflicts:
                return TransactionResult(
                    False,
                    "conflict",
                    transaction_id=transaction_id,
                    conflicts=tuple(conflicts),
                )
            for record in reversed(journal.get("records", [])):
                self._validate_backup(record.get("backup"), transaction_id)
                _restore_full(
                    _absolute(record["target"]),
                    before_exists=bool(record["before_exists"]),
                    backup=record.get("backup"),
                )
            previous = journal.get("previous_state")
            if previous is None:
                if _lexists(self.state_path):
                    self.state_path.unlink()
            elif isinstance(previous, dict):
                _write_json_atomic(self.state_path, previous)
            else:
                raise InstallConflict("transaction previous state is malformed")
            journal["status"] = "restored"
            journal["restored_at_ns"] = time.time_ns()
            _write_json_atomic(journal_path, journal)
            return TransactionResult(
                True,
                "restored",
                transaction_id=transaction_id,
                managed_hash=(
                    str(previous.get("managed_hash")) if isinstance(previous, dict) else None
                ),
                changes=tuple(str(item["identity"]) for item in journal.get("records", [])),
            )

    @staticmethod
    def _restore_managed_baseline(record: Mapping[str, Any]) -> None:
        target = _absolute(record["target"])
        baseline = record.get("baseline")
        if not isinstance(baseline, Mapping):
            raise InstallConflict(f"managed baseline is missing: {record.get('identity')}")
        if record["kind"] == "skill":
            _restore_full(
                target,
                before_exists=bool(baseline.get("before_exists")),
                backup=baseline.get("backup"),
            )
            return

        key = str(record["server_key"])
        data = _read_json_object(target, missing_ok=True)
        servers = data.setdefault("mcpServers", {})
        if not isinstance(servers, dict):
            raise ValueError("mcpServers must be an object")
        if baseline.get("before_key_exists"):
            servers[key] = baseline.get("before_value")
        else:
            servers.pop(key, None)
        config_existed = bool(baseline.get("before_exists"))
        if not config_existed and not servers and set(data) == {"mcpServers"}:
            if _lexists(target):
                _remove_path(target)
        else:
            _write_bytes_atomic(target, _canonical_json(data))

    def uninstall(self) -> TransactionResult:
        self._prepare_management_root()
        with exclusive_file_lock(self.lock_path):
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
            journal_path = self._journal_path(transaction_id)
            backup_root = self.backups_root / transaction_id
            _ensure_safe_directory(backup_root)
            current_records: list[dict[str, Any]] = []
            for index, record in enumerate(active["managed"]):
                target = _absolute(record["target"])
                exists = _lexists(target)
                backup: str | None = None
                if exists:
                    backup_path = backup_root / (
                        f"{index:03d}-{record['kind']}-{_path_token(str(record['identity']))}"
                    )
                    _atomic_backup(target, backup_path)
                    backup = str(backup_path)
                current_records.append(
                    {
                        "kind": record["kind"],
                        "identity": record["identity"],
                        "target": str(target),
                        "name": record["name"],
                        "server_key": record.get("server_key"),
                        "before_exists": exists,
                        "backup": backup,
                    }
                )
            journal = {
                "schema_version": "1.0",
                "transaction_id": transaction_id,
                "installation_id": self.installation_id,
                "kind": "uninstall",
                "status": "prepared",
                "created_at_ns": time.time_ns(),
                "records": current_records,
            }
            _write_json_atomic(journal_path, journal)
            applied: list[dict[str, Any]] = []
            try:
                for managed in reversed(active["managed"]):
                    self._restore_managed_baseline(managed)
                    applied.append(managed)
                journal["status"] = "committed"
                journal["committed_at_ns"] = time.time_ns()
                _write_json_atomic(journal_path, journal)
                self.state_path.unlink()
            except Exception:
                current_by_id = {
                    str(item["identity"]): item for item in current_records
                }
                for managed in reversed(applied):
                    before = current_by_id[str(managed["identity"])]
                    _restore_full(
                        _absolute(before["target"]),
                        before_exists=bool(before["before_exists"]),
                        backup=before.get("backup"),
                    )
                journal["status"] = "rolled_back"
                journal["rolled_back_at_ns"] = time.time_ns()
                _write_json_atomic(journal_path, journal)
                raise
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
]

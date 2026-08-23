"""Strictly-local installer for a checked, platform-specific ChatMaker Core."""

from __future__ import annotations

import argparse
import base64
import binascii
import configparser
from contextlib import contextmanager
import csv
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
import venv
import zipfile
from typing import Any, Iterator


SCHEMA_VERSION = 2
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_PROJECT = re.compile(r"[._-]+")
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{number}" for number in range(1, 10)), *(f"LPT{number}" for number in range(1, 10))}
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
_MAX_ARCHIVE = 512 * 1024 * 1024
_MAX_FILES = 20_000


class BootstrapError(RuntimeError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise BootstrapError(message)


def _platform_tag() -> str:
    system, machine = platform.system(), platform.machine().lower()
    if system == "Windows" and machine in {"amd64", "x86_64"}:
        return "windows-amd64"
    if system == "Darwin" and machine == "x86_64":
        return "macos-x86_64"
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64"
    raise BootstrapError("unsupported_bootstrap_platform")


def _tag_supports_runtime(tag: str, platform_tag: str) -> bool:
    try:
        interpreter, abi, wheel_platform = tag.split("-", 2)
    except ValueError:
        return False
    if interpreter == "py3" and abi == "none" and wheel_platform == "any":
        return True
    abi3_compatible = abi == "abi3" and re.fullmatch(r"cp3\d+", interpreter) is not None and int(interpreter[3:]) <= 11
    if (interpreter not in {"cp311", "py311", "py3"} and not abi3_compatible) or abi not in {"cp311", "abi3", "none"}:
        return False
    if platform_tag == "windows-amd64":
        return wheel_platform == "win_amd64"
    suffixes = ("_x86_64", "_universal2") if platform_tag == "macos-x86_64" else ("_arm64", "_universal2")
    return wheel_platform.startswith("macosx_") and wheel_platform.endswith(suffixes)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def _load_release_verifier():
    path = Path(__file__).with_name("core_release_signature.py")
    spec = importlib.util.spec_from_file_location("chatmaker_core_release_signature_bootstrap", path)
    if spec is None or spec.loader is None:
        raise BootstrapError("release_verifier_unavailable")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise BootstrapError("release_verifier_unavailable") from exc
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_checksum(archive: Path, checksum: Path) -> str:
    try:
        lines = checksum.read_text(encoding="ascii").splitlines()
    except OSError as exc:
        raise BootstrapError("checksum_file_unreadable") from exc
    if len(lines) != 1 or "  " not in lines[0]:
        raise BootstrapError("checksum_file_invalid")
    digest, filename = lines[0].split("  ", 1)
    if _SHA.fullmatch(digest) is None or filename != archive.name:
        raise BootstrapError("checksum_file_invalid")
    return digest


def _is_reparse(path: Path) -> bool:
    try:
        return bool(getattr(path.lstat(), "st_file_attributes", 0) & _REPARSE)
    except OSError:
        return True


def _safe_existing(path: Path, *, directory: bool | None = None) -> bool:
    if not os.path.lexists(path) or path.is_symlink() or _is_reparse(path):
        return False
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISDIR(mode) if directory is True else stat.S_ISREG(mode) if directory is False else True


def _safe_directory(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    chain = tuple(reversed((absolute, *absolute.parents)))
    for current in chain:
        if os.path.lexists(current):
            if not _safe_existing(current, directory=True):
                raise BootstrapError("management_path_unsafe")
        else:
            try:
                current.mkdir()
            except FileExistsError:
                pass
            if not _safe_existing(current, directory=True):
                raise BootstrapError("management_path_unsafe")


def _validate_management_aliases(path: Path) -> None:
    original = Path(path)
    absolute = Path(os.path.abspath(path))
    for candidate in (original, absolute):
        for part in candidate.parts:
            if part == candidate.anchor:
                continue
            plain = part.rstrip(" .")
            if (not plain or plain != part or unicodedata.normalize("NFC", part) != part
                    or plain.split(".", 1)[0].upper() in _WINDOWS_RESERVED):
                raise BootstrapError("management_path_unsafe")


def _require_safe_parent_chain(path: Path) -> None:
    """Reject a caller-supplied path that crosses a link or reparse point."""
    absolute = Path(os.path.abspath(path))
    chain = tuple(reversed((absolute.parent, *absolute.parents)))
    for current in chain:
        if not os.path.lexists(current) or not _safe_existing(current, directory=True):
            raise BootstrapError("management_path_unsafe")


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, data: bytes, *, executable: bool = False) -> None:
    _safe_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if executable:
            os.chmod(temporary_path, 0o755)
        os.replace(temporary_path, path)
        _fsync_directory(path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_if_different(path: Path, data: bytes, *, executable: bool = False) -> None:
    try:
        if _safe_existing(path, directory=False) and path.read_bytes() == data:
            if executable and os.name != "nt" and not (path.stat().st_mode & stat.S_IXUSR):
                os.chmod(path, 0o755)
            return
    except OSError:
        pass
    _atomic_write(path, data, executable=executable)


def _persist_active(path: Path, data: bytes, fault_inject: Any | None = None) -> None:
    """Persist the one active pointer with explicit crash-test boundaries."""
    _safe_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if fault_inject is not None:
            fault_inject("after_active_file_fsync")
        os.replace(temporary_path, path)
        if fault_inject is not None:
            fault_inject("after_active_replace")
        _fsync_directory(path.parent)
        if fault_inject is not None:
            fault_inject("after_active_parent_fsync")
    finally:
        temporary_path.unlink(missing_ok=True)


def _read_active(path: Path) -> dict[str, Any] | None:
    if not os.path.lexists(path):
        return None
    if not _safe_existing(path, directory=False):
        raise BootstrapError("active_pointer_invalid")
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootstrapError("active_pointer_invalid") from exc
    if (not isinstance(value, dict) or raw != _canonical_json(value)
            or set(value) != {"schema_version", "version", "archive_sha256", "platform_tag", "release_sequence", "release_manifest_sha256"}
            or value.get("schema_version") != SCHEMA_VERSION
            or not isinstance(value.get("version"), str) or _VERSION.fullmatch(value["version"]) is None
            or value["version"] != value["version"].rstrip(" .")
            or value.get("platform_tag") not in {"windows-amd64", "macos-x86_64", "macos-arm64"}
            or not isinstance(value.get("release_sequence"), int) or isinstance(value.get("release_sequence"), bool)
            or value["release_sequence"] < 1
            or _SHA.fullmatch(str(value.get("archive_sha256", ""))) is None
            or _SHA.fullmatch(str(value.get("release_manifest_sha256", ""))) is None):
        raise BootstrapError("active_pointer_invalid")
    return value


@contextmanager
def _lock(path: Path) -> Iterator[None]:
    _safe_directory(path.parent)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        if not _safe_existing(path, directory=False) or os.fstat(descriptor).st_nlink != 1:
            raise BootstrapError("bootstrap_lock_unsafe")
        if os.name == "nt":
            import msvcrt
            os.write(descriptor, b"\0") if os.fstat(descriptor).st_size == 0 else None
            deadline = time.monotonic() + 300
            while True:
                os.lseek(descriptor, 0, os.SEEK_SET)
                try:
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise BootstrapError("bootstrap_lock_timeout") from exc
                    time.sleep(0.05)
        else:
            import fcntl
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(descriptor)


def _snapshot(
    archive: Path,
    checksum: Path,
    *,
    signed_digest: str | None = None,
    signed_size: int | None = None,
) -> tuple[int, Path, str]:
    """Copy one no-follow archive handle and retain that descriptor for all reads."""
    _require_safe_parent_chain(archive)
    _require_safe_parent_chain(checksum)
    expected = _read_checksum(archive, checksum)
    if signed_digest is not None and not hmac.compare_digest(expected, signed_digest):
        raise BootstrapError("checksum_manifest_mismatch")
    if not _safe_existing(archive, directory=False):
        raise BootstrapError("core_archive_unreadable")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    source_fd = os.open(archive, flags)
    destination_fd, destination_name = tempfile.mkstemp(prefix="chatmaker-core-", suffix=".zip")
    snapshot = Path(destination_name)
    succeeded = False
    try:
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise BootstrapError("core_archive_unreadable")
        if signed_size is not None and before.st_size != signed_size:
            raise BootstrapError("archive_size_mismatch")
        digest = hashlib.sha256()
        with os.fdopen(source_fd, "rb", closefd=False) as source, os.fdopen(destination_fd, "wb", closefd=False) as destination:
            while True:
                block = source.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
                destination.write(block)
            destination.flush()
            os.fsync(destination.fileno())
        if not hmac.compare_digest(digest.hexdigest(), expected):
            raise BootstrapError("archive_checksum_mismatch")
        after = os.fstat(source_fd)
        if (before.st_dev, before.st_ino, before.st_size) != (after.st_dev, after.st_ino, after.st_size):
            raise BootstrapError("core_archive_changed_during_snapshot")
        succeeded = True
        return destination_fd, snapshot, expected
    except Exception:
        os.close(source_fd)
        os.close(destination_fd)
        source_fd = destination_fd = -1
        snapshot.unlink(missing_ok=True)
        raise
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        # Ownership of a successful snapshot descriptor transfers to caller.
        if destination_fd >= 0 and not succeeded:
            os.close(destination_fd)


def _read_release_evidence(
    manifest_path: Path,
    signature_path: Path,
    archive: Path,
    platform_tag: str,
) -> tuple[dict[str, Any], bytes, dict[str, str]]:
    """Verify detached origin evidence before the archive pathname is trusted."""
    for path in (manifest_path, signature_path):
        _require_safe_parent_chain(path)
        if not _safe_existing(path, directory=False):
            raise BootstrapError("release_evidence_unsafe")
    try:
        manifest_bytes = manifest_path.read_bytes()
        signature_bytes = signature_path.read_bytes()
        verifier = _load_release_verifier()
        verified = verifier.verify_release_manifest(manifest_bytes, signature_bytes)
        manifest = json.loads(manifest_bytes)
    except Exception as exc:
        raise BootstrapError("release_signature_invalid") from exc
    expected_keys = {
        "schema_version", "release_sequence", "core_version", "core_wheel_version",
        "platform_tag", "python_tag", "archive", "runtime_manifest_sha256", "release_metadata",
    }
    archive_value = manifest.get("archive")
    metadata = manifest.get("release_metadata")
    version = manifest.get("core_version")
    wheel_version = manifest.get("core_wheel_version")
    if (set(manifest) != expected_keys or manifest.get("schema_version") != 1
            or not isinstance(manifest.get("release_sequence"), int)
            or isinstance(manifest.get("release_sequence"), bool)
            or manifest["release_sequence"] < 1
            or not isinstance(version, str) or _VERSION.fullmatch(version) is None
            or version != version.rstrip(" .")
            or version.rstrip(" .").split(".", 1)[0].upper() in _WINDOWS_RESERVED
            or not isinstance(wheel_version, str) or not wheel_version or not wheel_version.isascii()
            or manifest.get("platform_tag") != platform_tag or manifest.get("python_tag") != "cp311"
            or not isinstance(manifest.get("runtime_manifest_sha256"), str)
            or _SHA.fullmatch(manifest["runtime_manifest_sha256"]) is None
            or not isinstance(archive_value, dict) or set(archive_value) != {"filename", "size", "sha256"}
            or archive_value.get("filename") != archive.name
            or not isinstance(archive_value.get("size"), int) or isinstance(archive_value.get("size"), bool)
            or archive_value["size"] <= 0
            or not isinstance(archive_value.get("sha256"), str) or _SHA.fullmatch(archive_value["sha256"]) is None
            or not isinstance(metadata, dict)
            or set(metadata) != {"archive_format", "compression", "member_count", "timestamp"}
            or metadata.get("archive_format") != "zip" or metadata.get("compression") != "deflate-9"
            or not isinstance(metadata.get("member_count"), int) or isinstance(metadata.get("member_count"), bool)
            or metadata["member_count"] < 1 or metadata.get("timestamp") != "2026-08-14T00:00:00Z"):
        raise BootstrapError("release_manifest_invalid")
    return manifest, manifest_bytes, verified


def _portable_key(parts: tuple[str, ...]) -> str:
    return "/".join(unicodedata.normalize("NFC", part).rstrip(" .").casefold() for part in parts)


def _member_parts(name: str) -> tuple[str, ...]:
    if not name or "\\" in name or "\x00" in name:
        raise BootstrapError("archive_member_path_unsafe")
    value = PurePosixPath(name)
    if value.is_absolute() or not value.parts:
        raise BootstrapError("archive_member_path_unsafe")
    for part in value.parts:
        plain = part.rstrip(" .")
        if part in {"", ".", ".."} or not plain or ":" in part or plain.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
            raise BootstrapError("archive_member_path_unsafe")
    return value.parts


def _snapshot_stream(descriptor: int):
    return os.fdopen(os.dup(descriptor), "rb")


def _validate_archive(snapshot: int, expected_platform: str) -> tuple[str, tuple[zipfile.ZipInfo, ...]]:
    try:
        stream = _snapshot_stream(snapshot)
        archive = zipfile.ZipFile(stream)
    except (OSError, zipfile.BadZipFile) as exc:
        raise BootstrapError("core_archive_invalid") from exc
    try:
        infos = tuple(archive.infolist())
        if not infos or len(infos) > _MAX_FILES or os.fstat(snapshot).st_size > _MAX_ARCHIVE or archive.comment:
            raise BootstrapError("core_archive_invalid")
        keys: set[str] = set()
        roots: set[str] = set()
        total = 0
        for info in infos:
            if info.is_dir() or info.flag_bits & 1:
                raise BootstrapError("archive_member_unsafe")
            parts = _member_parts(info.filename)
            key = _portable_key(parts)
            if key in keys:
                raise BootstrapError("archive_member_collision")
            keys.add(key); roots.add(parts[0]); total += info.file_size
            mode = info.external_attr >> 16
            if stat.S_IFMT(mode) not in {0, stat.S_IFREG} or info.file_size < 0 or total > _MAX_ARCHIVE:
                raise BootstrapError("archive_member_unsafe")
        for key in keys:
            parent = key.rpartition("/")[0]
            while parent:
                if parent in keys:
                    raise BootstrapError("archive_member_collision")
                parent = parent.rpartition("/")[0]
        if len(roots) != 1:
            raise BootstrapError("core_archive_layout_invalid")
        root = next(iter(roots))
        prefix = "ChatMaker-Core-"
        suffix = "-" + expected_platform
        if not root.startswith(prefix) or not root.endswith(suffix):
            raise BootstrapError("core_platform_mismatch")
        version = root[len(prefix):-len(suffix)]
        if _VERSION.fullmatch(version) is None or version != version.rstrip(" .") or version.rstrip(" .").split(".", 1)[0].upper() in _WINDOWS_RESERVED:
            raise BootstrapError("version_path_unsafe")
        required = {f"{root}/core-runtime/manifest.json", f"{root}/core-runtime/requirements.txt", f"{root}/scripts/bootstrap.py"}
        if not required.issubset({info.filename for info in infos}):
            raise BootstrapError("core_archive_layout_invalid")
        return version, infos
    finally:
        archive.close()
        stream.close()


def _extract(snapshot: int, infos: tuple[zipfile.ZipInfo, ...], destination: Path) -> Path:
    _safe_directory(destination)
    stream = _snapshot_stream(snapshot)
    archive = zipfile.ZipFile(stream)
    try:
        for info in infos:
            target = destination.joinpath(*_member_parts(info.filename))
            _safe_directory(target.parent)
            with archive.open(info) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            os.chmod(target, 0o644)
    except (OSError, zipfile.BadZipFile) as exc:
        raise BootstrapError("core_archive_extract_failed") from exc
    finally:
        archive.close()
        stream.close()
    roots = list(destination.iterdir())
    if len(roots) != 1 or not _safe_existing(roots[0], directory=True):
        raise BootstrapError("core_archive_layout_invalid")
    return roots[0]


def _runtime_bundle(root: Path, expected_platform: str) -> tuple[dict[str, Any], Path, Path]:
    runtime = root / "core-runtime"
    try:
        manifest_bytes = (runtime / "manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        requirements = runtime / "requirements.txt"
        requirements_bytes = requirements.read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootstrapError("runtime_bundle_invalid") from exc
    if (manifest_bytes != _canonical_json(manifest) or manifest.get("schema_version") != 2
            or manifest.get("platform_tag") != expected_platform
            or manifest.get("python_requires") != "==3.11.*"):
        raise BootstrapError("runtime_bundle_invalid")
    wheelhouse = runtime / "wheelhouse"
    wheels = manifest.get("wheels")
    if not _safe_existing(wheelhouse, directory=True) or not isinstance(wheels, list) or not isinstance(manifest.get("core_wheel"), str):
        raise BootstrapError("runtime_bundle_invalid")
    expected: set[str] = set(); requirement_lines: dict[str, bytes] = {}; projects: set[str] = set(); dependencies: dict[str, set[str]] = {}
    for item in wheels:
        if not isinstance(item, dict) or set(item) != {"filename", "project", "version", "size", "sha256", "tags", "requires"}:
            raise BootstrapError("runtime_bundle_invalid")
        filename, project, item_version, size, digest, tags, requires = item["filename"], item["project"], item["version"], item["size"], item["sha256"], item["tags"], item["requires"]
        if (not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".whl") or not filename.isascii()
                or not isinstance(project, str) or not project or _PROJECT.sub("-", project).lower() != project
                or project in projects or not isinstance(item_version, str) or not item_version or not item_version.isascii()
                or not isinstance(size, int) or isinstance(size, bool) or size <= 0
                or not isinstance(digest, str) or _SHA.fullmatch(digest) is None
                or not isinstance(tags, list) or tags != sorted(set(tags)) or not tags
                or any(not isinstance(tag, str) for tag in tags)
                or not any(_tag_supports_runtime(tag, expected_platform) for tag in tags)
                or not isinstance(requires, list) or requires != sorted(set(requires))
                or any(not isinstance(value, str) or _PROJECT.sub("-", value).lower() != value for value in requires)):
            raise BootstrapError("runtime_bundle_invalid")
        wheel = wheelhouse / filename
        if not _safe_existing(wheel, directory=False) or wheel.stat().st_size != size or _sha256(wheel) != digest:
            raise BootstrapError("runtime_bundle_invalid")
        expected.add(filename); projects.add(project); dependencies[project] = set(requires); requirement_lines[project] = f"{project}=={item_version} --hash=sha256:{digest}\n".encode("ascii")
    if len(expected) != len(wheels) or manifest["core_wheel"] not in expected or {entry.name for entry in wheelhouse.iterdir()} != expected or requirements_bytes.splitlines(keepends=True) != [requirement_lines[project] for project in sorted(requirement_lines)]:
        raise BootstrapError("runtime_bundle_invalid")
    if any(not values.issubset(projects) for values in dependencies.values()):
        raise BootstrapError("runtime_bundle_invalid")
    core_project = next(item["project"] for item in wheels if item["filename"] == manifest["core_wheel"])
    reachable = {core_project}; pending = [core_project]
    while pending:
        for dependency in dependencies[pending.pop()]:
            if dependency not in reachable:
                reachable.add(dependency); pending.append(dependency)
    if reachable != projects:
        raise BootstrapError("runtime_bundle_invalid")
    return manifest, wheelhouse, requirements


def _python(venv_path: Path) -> Path:
    return venv_path / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")


def _site_packages(venv_path: Path) -> Path:
    """Compute the venv purelib path without starting its mutable interpreter."""
    if os.name == "nt":
        return venv_path / "Lib" / "site-packages"
    return venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"


def _record_digest(value: str) -> str:
    if not value.startswith("sha256="):
        raise BootstrapError("runtime_wheel_record_invalid")
    encoded = value.removeprefix("sha256=")
    try:
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except (binascii.Error, ValueError) as exc:
        raise BootstrapError("runtime_wheel_record_invalid") from exc
    if len(raw) != 32 or base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != encoded:
        raise BootstrapError("runtime_wheel_record_invalid")
    return raw.hex()


def _wheel_contract(wheel: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Derive installed hashes and console entry points from the signed wheel RECORD."""
    try:
        with zipfile.ZipFile(wheel) as archive:
            infos = tuple(archive.infolist())
            names = [info.filename for info in infos if not info.is_dir()]
            records = [name for name in names if name.endswith(".dist-info/RECORD")]
            if len(records) != 1 or len(names) != len(set(names)):
                raise BootstrapError("runtime_wheel_record_invalid")
            record_name = records[0]
            rows = list(csv.reader(archive.read(record_name).decode("utf-8").splitlines()))
            recorded: dict[str, tuple[str, str]] = {}
            for row in rows:
                if len(row) != 3 or row[0] in recorded:
                    raise BootstrapError("runtime_wheel_record_invalid")
                parts = _member_parts(row[0])
                normalized = "/".join(parts)
                if normalized != row[0]:
                    raise BootstrapError("runtime_wheel_record_invalid")
                recorded[normalized] = (row[1], row[2])
            if set(recorded) != set(names) or recorded.get(record_name) != ("", ""):
                raise BootstrapError("runtime_wheel_record_invalid")
            expected: dict[str, str] = {}
            portable: set[str] = set()
            for name in names:
                if name == record_name:
                    continue
                raw = archive.read(name)
                digest, size = recorded[name]
                if not size.isascii() or not size.isdecimal() or int(size) != len(raw) or _record_digest(digest) != hashlib.sha256(raw).hexdigest():
                    raise BootstrapError("runtime_wheel_record_invalid")
                parts = _member_parts(name)
                if len(parts) > 2 and parts[0].endswith(".data") and parts[1] in {"purelib", "platlib"}:
                    parts = parts[2:]
                elif any(part.endswith(".data") for part in parts):
                    raise BootstrapError("runtime_wheel_layout_unsupported")
                relative = "/".join(parts)
                lower_name = parts[-1].casefold()
                top = parts[0].removesuffix(".py").casefold()
                if (lower_name.endswith(".pth") or lower_name in {"sitecustomize.py", "usercustomize.py"}
                        or top in {name.casefold() for name in sys.stdlib_module_names}):
                    raise BootstrapError("runtime_wheel_shadow_module")
                key = _portable_key(parts)
                if key in portable or relative in expected:
                    raise BootstrapError("runtime_wheel_collision")
                portable.add(key)
                expected[relative] = hashlib.sha256(raw).hexdigest()
            entries: dict[str, str] = {}
            entry_files = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
            if len(entry_files) > 1:
                raise BootstrapError("runtime_wheel_invalid")
            if entry_files:
                parser = configparser.ConfigParser(interpolation=None)
                parser.optionxform = str
                parser.read_string(archive.read(entry_files[0]).decode("utf-8"))
                for name, target in parser.items("console_scripts") if parser.has_section("console_scripts") else ():
                    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is None or re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*", target) is None:
                        raise BootstrapError("runtime_entry_point_invalid")
                    entries[name] = target
            return expected, entries
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile, csv.Error, configparser.Error) as exc:
        raise BootstrapError("runtime_wheel_invalid") from exc


def _expected_runtime(manifest: dict[str, Any], wheelhouse: Path) -> tuple[dict[str, str], dict[str, str]]:
    expected: dict[str, str] = {}
    entries: dict[str, str] = {}
    portable: set[str] = set()
    for item in manifest["wheels"]:
        wheel_expected, wheel_entries = _wheel_contract(wheelhouse / item["filename"])
        for relative, digest in wheel_expected.items():
            key = _portable_key(PurePosixPath(relative).parts)
            if relative in expected or key in portable:
                raise BootstrapError("runtime_wheel_collision")
            expected[relative] = digest
            portable.add(key)
        for name, target in wheel_entries.items():
            if name in entries and entries[name] != target:
                raise BootstrapError("runtime_entry_point_collision")
            entries[name] = target
    return expected, entries


def _site_inventory(site: Path) -> dict[str, str]:
    """Hash every regular site-packages file and reject links/reparse points."""
    if not _safe_existing(site, directory=True):
        raise BootstrapError("venv_invalid")
    inventory: dict[str, str] = {}
    for candidate in sorted(site.rglob("*"), key=lambda item: item.as_posix()):
        if candidate.is_dir():
            if not _safe_existing(candidate, directory=True):
                raise BootstrapError("venv_invalid")
        elif candidate.is_file():
            if not _safe_existing(candidate, directory=False):
                raise BootstrapError("venv_invalid")
            inventory[candidate.relative_to(site).as_posix()] = _sha256(candidate)
        else:
            raise BootstrapError("venv_invalid")
    return inventory


def _entrypoint_files(venv_path: Path, entries: dict[str, str]) -> dict[str, bytes]:
    scripts = venv_path / ("Scripts" if os.name == "nt" else "bin")
    result: dict[str, bytes] = {}
    for name, target in sorted(entries.items()):
        module, function = target.split(":", 1)
        runner_name = f".{name}-chatmaker.py"
        runner = (
            "import os,sys\nfrom pathlib import Path\n"
            "root=Path(sys.executable).parent.parent\n"
            "site=root / ('Lib/site-packages' if os.name == 'nt' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')\n"
            "sys.path.insert(0,str(site))\n"
            f"from {module} import {function} as entry\n"
            "raise SystemExit(entry())\n"
        ).encode("utf-8")
        result[runner_name] = runner
        if os.name == "nt":
            result[f"{name}.cmd"] = f'@echo off\r\n"%~dp0python.exe" -I -S -B "%~dp0{runner_name}" %*\r\n'.encode("utf-8")
        else:
            result[name] = f'#!/bin/sh\nexec "$(dirname "$0")/python" -I -S -B "$(dirname "$0")/{runner_name}" "$@"\n'.encode("utf-8")
    return result


def _interpreter_names() -> set[str]:
    if os.name == "nt":
        return {"python.exe", "pythonw.exe"}
    return {"python", "python3", f"python{sys.version_info.major}.{sys.version_info.minor}"}


def _sanitize_install(venv_path: Path, expected: dict[str, str], entries: dict[str, str]) -> None:
    site = _site_packages(venv_path)
    actual = _site_inventory(site)
    for relative, digest in expected.items():
        if actual.get(relative) != digest:
            raise BootstrapError("offline_runtime_install_failed")
    for relative in sorted(set(actual) - set(expected), key=lambda value: value.count("/"), reverse=True):
        target = site.joinpath(*PurePosixPath(relative).parts)
        if not _safe_existing(target, directory=False):
            raise BootstrapError("offline_runtime_install_failed")
        target.unlink()
    for directory in sorted((path for path in site.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if _site_inventory(site) != expected:
        raise BootstrapError("offline_runtime_install_failed")
    scripts = venv_path / ("Scripts" if os.name == "nt" else "bin")
    keep = _interpreter_names()
    for path in tuple(scripts.iterdir()):
        if path.name in keep:
            continue
        if path.is_symlink() or _is_reparse(path):
            raise BootstrapError("offline_runtime_install_failed")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for name, data in _entrypoint_files(venv_path, entries).items():
        _atomic_write(scripts / name, data, executable=os.name != "nt" and not name.startswith("."))


def _valid_base_interpreter(venv_path: Path) -> bool:
    try:
        trusted = Path(getattr(sys, "_base_executable", sys.executable))
        if (venv_path / "pyvenv.cfg").read_bytes() != _venv_config_bytes(venv_path):
            return False
        python = _python(venv_path)
        if os.name == "nt":
            with tempfile.TemporaryDirectory(prefix="chatmaker-venv-template-") as temporary:
                template = Path(temporary) / "venv"
                venv.EnvBuilder(with_pip=False, system_site_packages=False).create(template)
                for name in _interpreter_names():
                    installed = venv_path / "Scripts" / name
                    expected = template / "Scripts" / name
                    if not _safe_existing(installed, directory=False) or not _safe_existing(expected, directory=False) or _sha256(installed) != _sha256(expected):
                        return False
        else:
            if python.is_symlink():
                if not os.path.samefile(python, trusted):
                    return False
            elif not _safe_existing(python, directory=False) or _sha256(python) != _sha256(trusted):
                return False
        return True
    except (OSError, ValueError, BootstrapError):
        return False


def _venv_config_bytes(venv_path: Path) -> bytes:
    trusted = Path(os.path.abspath(getattr(sys, "_base_executable", sys.executable)))
    values = (
        f"home = {trusted.parent}\n"
        "include-system-site-packages = false\n"
        f"version = {platform.python_version()}\n"
        f"executable = {trusted}\n"
        f"command = {trusted} -m venv {Path(os.path.abspath(venv_path))}\n"
    )
    return values.encode("utf-8")


def _venv_tree_safe(venv_path: Path) -> bool:
    scripts = venv_path / ("Scripts" if os.name == "nt" else "bin")
    trusted = Path(getattr(sys, "_base_executable", sys.executable))
    pending = [venv_path]
    try:
        while pending:
            directory = pending.pop()
            for entry in os.scandir(directory):
                path = Path(entry.path)
                if entry.is_symlink():
                    if path.parent != scripts or path.name not in _interpreter_names() or not os.path.samefile(path, trusted):
                        return False
                    continue
                attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
                if attributes & _REPARSE:
                    return False
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif not entry.is_file(follow_symlinks=False):
                    return False
        return True
    except OSError:
        return False


def _verify_venv(venv_path: Path, manifest: dict[str, Any], wheelhouse: Path) -> bool:
    if not _safe_existing(venv_path, directory=True) or not _venv_tree_safe(venv_path) or not _valid_base_interpreter(venv_path):
        return False
    try:
        expected, entries = _expected_runtime(manifest, wheelhouse)
        if _site_inventory(_site_packages(venv_path)) != expected:
            return False
        scripts = venv_path / ("Scripts" if os.name == "nt" else "bin")
        expected_scripts = _entrypoint_files(venv_path, entries)
        actual_names = {path.name for path in scripts.iterdir()}
        if actual_names != _interpreter_names() | set(expected_scripts):
            return False
        for name, data in expected_scripts.items():
            path = scripts / name
            if not _safe_existing(path, directory=False) or path.read_bytes() != data:
                return False
        return True
    except (BootstrapError, OSError, TypeError, AttributeError, json.JSONDecodeError):
        return False


def _install(venv_path: Path, requirements: Path, wheelhouse: Path, manifest: dict[str, Any]) -> None:
    expected, entries = _expected_runtime(manifest, wheelhouse)
    venv.EnvBuilder(with_pip=True, system_site_packages=False, clear=False).create(venv_path)
    python = _python(venv_path)
    if (os.name == "nt" and not _safe_existing(python, directory=False)) or not python.exists():
        raise BootstrapError("venv_creation_failed")
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PIP_NO_INDEX": "1", "PIP_CONFIG_FILE": os.devnull, "TMP": str(venv_path.parent), "TEMP": str(venv_path.parent)}
    for name in ("SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "LANG", "LC_ALL"):
        if os.environ.get(name):
            env[name] = os.environ[name]
    completed = subprocess.run([str(python), "-I", "-m", "pip", "install", "--isolated", "--disable-pip-version-check", "--no-input", "--no-compile", "--no-index", "--find-links", str(wheelhouse), "--require-hashes", "--no-deps", "-r", str(requirements)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False)
    if completed.returncode:
        raise BootstrapError("offline_runtime_install_failed")
    _sanitize_install(venv_path, expected, entries)
    _atomic_write(venv_path / "pyvenv.cfg", _venv_config_bytes(venv_path))
    if not _verify_venv(venv_path, manifest, wheelhouse):
        raise BootstrapError("offline_runtime_install_failed")


def _tree_inventory(root: Path) -> dict[str, str]:
    if not _safe_existing(root, directory=True):
        raise BootstrapError("managed_core_drift_detected")
    inventory: dict[str, str] = {}
    portable: set[str] = set()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_dir():
            if not _safe_existing(path, directory=True):
                raise BootstrapError("managed_core_drift_detected")
            continue
        if not _safe_existing(path, directory=False):
            raise BootstrapError("managed_core_drift_detected")
        relative = path.relative_to(root).as_posix()
        key = _portable_key(PurePosixPath(relative).parts)
        if key in portable:
            raise BootstrapError("managed_core_drift_detected")
        portable.add(key)
        inventory[relative] = _sha256(path)
    return inventory


def _quarantine(home_root: Path, version: str, version_root: Path) -> Path:
    quarantine_root = home_root / "quarantine"
    _safe_directory(quarantine_root)
    destination = quarantine_root / f"{version}-{uuid.uuid4().hex}"
    os.replace(version_root, destination)
    _fsync_directory(version_root.parent)
    _fsync_directory(quarantine_root)
    return destination


def _restore_quarantined(home_root: Path, version: str, version_root: Path, quarantined: Path | None) -> None:
    if quarantined is None or not quarantined.exists():
        return
    if version_root.exists():
        _quarantine(home_root, version, version_root)
    os.replace(quarantined, version_root)
    _fsync_directory(version_root.parent)


def _stable_runner_source() -> bytes:
    return b'''import json,os,re,runpy,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
try:
 raw=(root/'active.json').read_bytes(); active=json.loads(raw); canonical=(json.dumps(active,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\\n').encode('ascii')
 if raw!=canonical or set(active)!={'schema_version','version','archive_sha256','platform_tag','release_sequence','release_manifest_sha256'} or active['schema_version']!=2 or not isinstance(active['release_sequence'],int) or isinstance(active['release_sequence'],bool) or active['release_sequence']<1 or re.fullmatch(r'[0-9a-f]{64}',active['archive_sha256']) is None or re.fullmatch(r'[0-9a-f]{64}',active['release_manifest_sha256']) is None: raise ValueError
 version=active['version']; platform_tag=active['platform_tag']
 if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',version) is None or version.rstrip(' .')!=version or platform_tag not in {'windows-amd64','macos-x86_64','macos-arm64'}: raise ValueError
except Exception: raise SystemExit('invalid active pointer')
args=sys.argv[1:]
if '--home' in args: raise SystemExit('managed launcher fixes --home')
version_root=root/'versions'/version; core=version_root/f'ChatMaker-Core-{version}-{platform_tag}'; venv=version_root/'venv'
try:
 bootstrap=runpy.run_path(str(core/'scripts/bootstrap.py'),run_name='chatmaker_installed_verifier'); manifest,wheelhouse,_=bootstrap['_runtime_bundle'](core,platform_tag)
 if not bootstrap['_verify_venv'](venv,manifest,wheelhouse): raise ValueError
except Exception: raise SystemExit('installed runtime integrity check failed')
python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
code="import os,runpy,sys; from pathlib import Path; root=Path(sys.executable).parent.parent; pure=root / ('Lib/site-packages' if os.name == 'nt' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages'); sys.path.insert(0,str(pure)); runpy.run_module('chatmaker.installers.auto',run_name='__main__')"
env={'HOME':str(root.parent),'USERPROFILE':str(root.parent),'PATH':os.environ.get('PATH',''),'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','CHATMAKER_PROJECT_ROOT':str(core)}
raise SystemExit(subprocess.call([str(python),'-I','-S','-B','-c',code,*args,'--home',str(root.parent)],env=env))
'''


def _stable_launcher(home_root: Path) -> None:
    bin_root = home_root / "bin"
    runner = bin_root / "chatmaker-launch.py"
    source = _stable_runner_source()
    _write_if_different(runner, source, executable=True)
    launcher = bin_root / ("chatmaker-install.cmd" if os.name == "nt" else "chatmaker-install")
    if os.name == "nt":
        trusted_python = str(Path(getattr(sys, "_base_executable", sys.executable)))
        body = f'@echo off\r\n"{trusted_python}" -I -S -B "%~dp0chatmaker-launch.py" %*\r\n'.encode("utf-8")
        _write_if_different(launcher, body)
    else:
        trusted_python = str(Path(getattr(sys, "_base_executable", sys.executable)))
        _write_if_different(launcher, f'#!/bin/sh\nexec "{trusted_python}" -I -S -B "$(dirname "$0")/chatmaker-launch.py" "$@"\n'.encode("utf-8"), executable=True)


def _auto(venv_path: Path, home: Path, core_root: Path) -> dict[str, Any]:
    temp = home / ".chatmaker" / "tmp"
    _safe_directory(temp)
    env = {"HOME": str(home), "USERPROFILE": str(home), "PATH": os.environ.get("PATH", ""), "TMP": str(temp), "TEMP": str(temp), "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PIP_NO_INDEX": "1", "CHATMAKER_PROJECT_ROOT": str(core_root)}
    code = "import os,runpy,sys; from pathlib import Path; root=Path(sys.executable).parent.parent; pure=root / ('Lib/site-packages' if os.name == 'nt' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages'); sys.path.insert(0,str(pure)); runpy.run_module('chatmaker.installers.auto',run_name='__main__')"
    completed = subprocess.run([str(_python(venv_path)), "-I", "-S", "-B", "-c", code, "auto", "--home", str(home)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False)
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BootstrapError("auto_installer_report_invalid") from exc
    if completed.returncode or not isinstance(value, dict) or not value.get("success"):
        raise BootstrapError("auto_installer_failed")
    return value


def run(
    *,
    archive: Path,
    checksum: Path,
    release_manifest: Path,
    release_signature: Path,
    home: Path | None = None,
    _fault_inject: Any | None = None,
) -> dict[str, Any]:
    if sys.version_info[:2] != (3, 11):
        raise BootstrapError("python_3_11_required")
    archive = Path(os.path.abspath(Path(archive).expanduser()))
    checksum = Path(os.path.abspath(Path(checksum).expanduser()))
    release_manifest = Path(os.path.abspath(Path(release_manifest).expanduser()))
    release_signature = Path(os.path.abspath(Path(release_signature).expanduser()))
    home_candidate = Path.home() if home is None else Path(home).expanduser()
    _validate_management_aliases(home_candidate)
    selected_home = Path(os.path.abspath(home_candidate))
    platform_tag = _platform_tag()
    signed, signed_bytes, verified_signature = _read_release_evidence(
        release_manifest,
        release_signature,
        archive,
        platform_tag,
    )
    snapshot, snapshot_path, digest = _snapshot(
        archive,
        checksum,
        signed_digest=signed["archive"]["sha256"],
        signed_size=signed["archive"]["size"],
    )
    try:
        version, infos = _validate_archive(snapshot, platform_tag)
        if (version != signed["core_version"]
                or signed["release_metadata"]["member_count"] != len(infos)):
            raise BootstrapError("release_manifest_archive_mismatch")
        home_root = selected_home / ".chatmaker"
        _safe_directory(home_root / "versions")
        with _lock(home_root / "locks" / "bootstrap.lock"):
            active_path = home_root / "active.json"
            active = _read_active(active_path)
            signed_manifest_sha256 = hashlib.sha256(signed_bytes).hexdigest()
            if active is not None:
                if signed["release_sequence"] < active["release_sequence"]:
                    raise BootstrapError("release_sequence_rollback")
                if (signed["release_sequence"] == active["release_sequence"]
                        and signed_manifest_sha256 != active["release_manifest_sha256"]):
                    raise BootstrapError("release_sequence_conflict")
            staging = home_root / "versions" / f".{version}.staging-{uuid.uuid4().hex}"
            core = _extract(snapshot, infos, staging)
            manifest, wheelhouse, requirements = _runtime_bundle(core, platform_tag)
            if hashlib.sha256(_canonical_json(manifest)).hexdigest() != signed["runtime_manifest_sha256"]:
                raise BootstrapError("release_runtime_manifest_mismatch")
            core_wheels = [item for item in manifest["wheels"] if item["filename"] == manifest["core_wheel"]]
            if len(core_wheels) != 1 or core_wheels[0]["version"] != signed["core_wheel_version"]:
                raise BootstrapError("release_core_wheel_mismatch")
            version_root = home_root / "versions" / version
            existing = version_root.exists()
            if existing and not _safe_existing(version_root, directory=True):
                raise BootstrapError("management_path_unsafe")
            runtime_manifest_sha256 = hashlib.sha256(_canonical_json(manifest)).hexdigest()
            bootstrap_metadata = {
                "schema_version": SCHEMA_VERSION,
                "version": version,
                "archive_sha256": digest,
                "platform_tag": platform_tag,
                "runtime_manifest_sha256": runtime_manifest_sha256,
                "release_sequence": signed["release_sequence"],
                "release_manifest_sha256": signed_manifest_sha256,
                "signing_key_id": verified_signature["key_id"],
            }
            repaired = False
            if existing:
                try:
                    metadata_raw = (version_root / ".bootstrap.json").read_bytes()
                    installed = json.loads(metadata_raw)
                    installed_core = version_root / core.name
                    reusable = (
                        metadata_raw == _canonical_json(installed)
                        and installed == bootstrap_metadata
                        and _tree_inventory(installed_core) == _tree_inventory(core)
                        and _verify_venv(version_root / "venv", manifest, wheelhouse)
                    )
                except (BootstrapError, OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
                    reusable = False
                if not reusable:
                    existing = False
                    repaired = True
            if not existing:
                _install(staging / "venv", requirements, wheelhouse, manifest)
                _atomic_write(staging / ".bootstrap.json", _canonical_json(bootstrap_metadata))
                quarantined: Path | None = None
                if repaired:
                    quarantined = _quarantine(home_root, version, version_root)
                try:
                    os.replace(staging, version_root)
                except Exception:
                    if repaired:
                        _restore_quarantined(home_root, version, version_root, quarantined)
                    raise
                _fsync_directory(version_root.parent)
                _atomic_write(version_root / "venv" / "pyvenv.cfg", _venv_config_bytes(version_root / "venv"))
                installed_manifest, installed_wheelhouse, _ = _runtime_bundle(version_root / core.name, platform_tag)
                if not _verify_venv(version_root / "venv", installed_manifest, installed_wheelhouse):
                    if repaired:
                        _restore_quarantined(home_root, version, version_root, quarantined)
                    raise BootstrapError("installed_runtime_drift_detected")
            else:
                shutil.rmtree(staging, ignore_errors=True)
                quarantined = None
            try:
                auto = _auto(version_root / "venv", selected_home, version_root / f"ChatMaker-Core-{version}-{platform_tag}")
            except Exception:
                if repaired:
                    _restore_quarantined(home_root, version, version_root, quarantined)
                raise
            _stable_launcher(home_root)
            _persist_active(active_path, _canonical_json({"schema_version": SCHEMA_VERSION, "version": version, "archive_sha256": digest, "platform_tag": platform_tag, "release_sequence": signed["release_sequence"], "release_manifest_sha256": signed_manifest_sha256}), _fault_inject)
            status = "repaired" if repaired else "already_current" if existing else "installed"
            return {"success": True, "status": status, "version": version, "platform_tag": platform_tag, "release_sequence": signed["release_sequence"], "sha256": digest, "venv": str(version_root / "venv"), "launcher": str(home_root / "bin" / ("chatmaker-install.cmd" if os.name == "nt" else "chatmaker-install")), "auto": auto}
    finally:
        os.close(snapshot)
        snapshot_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="Install a checked local platform-specific ChatMaker Core release.")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--checksum", type=Path, required=True)
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--release-signature", type=Path, required=True)
    parser.add_argument("--home", type=Path)
    try:
        args = parser.parse_args(argv)
        result = run(
            archive=args.archive,
            checksum=args.checksum,
            release_manifest=args.release_manifest,
            release_signature=args.release_signature,
            home=args.home,
        )
    except Exception as exc:
        result = {"success": False, "status": "failed", "error": type(exc).__name__, "detail": str(exc)}
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

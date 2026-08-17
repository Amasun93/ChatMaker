"""Install a checked local ChatMaker Core release without a preinstalled Core.

This is deliberately self-contained: it runs on Python 3.11 with only the
standard library, verifies the release before opening it, and invokes the Core
only after it has been installed into its versioned virtual environment.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import unicodedata
import uuid
import venv
import zipfile
from typing import Any, Iterable


SCHEMA_VERSION = 1
_CORE_NAME = re.compile(r"ChatMaker-Core-([A-Za-z0-9][A-Za-z0-9._-]*)\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ENTRY_POINT = re.compile(r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*):([A-Za-z_]\w*)\Z")
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_REQUIRED_CORE_FILES = {"pyproject.toml", "runtime/chatmaker/__init__.py"}
_MAX_FILES = 20_000
_MAX_UNCOMPRESSED = 512 * 1024 * 1024


class BootstrapError(RuntimeError):
    """A safe, user-actionable failure from the bootstrap boundary."""


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise BootstrapError(message)


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_expected_checksum(archive: Path, checksum: Path) -> str:
    try:
        content = checksum.read_text(encoding="ascii")
    except OSError as exc:
        raise BootstrapError("checksum_file_unreadable") from exc
    lines = content.splitlines()
    if len(lines) != 1:
        raise BootstrapError("checksum_file_invalid")
    expected_prefix = "  "
    if expected_prefix not in lines[0]:
        raise BootstrapError("checksum_file_invalid")
    digest, filename = lines[0].split(expected_prefix, 1)
    if _SHA256.fullmatch(digest) is None or filename != archive.name:
        raise BootstrapError("checksum_file_invalid")
    actual = _sha256(archive)
    if not hmac.compare_digest(actual, digest):
        raise BootstrapError("archive_checksum_mismatch")
    return actual


def _portable_member_key(parts: Iterable[str]) -> str:
    return "/".join(unicodedata.normalize("NFC", item).rstrip(" .").casefold() for item in parts)


def _validate_member_path(name: str) -> tuple[str, ...]:
    if not name or "\\" in name or "\x00" in name:
        raise BootstrapError("archive_member_path_unsafe")
    value = PurePosixPath(name)
    if value.is_absolute() or not value.parts:
        raise BootstrapError("archive_member_path_unsafe")
    parts = value.parts
    for part in parts:
        if part in {"", ".", ".."} or ":" in part or part.rstrip(" .") == "":
            raise BootstrapError("archive_member_path_unsafe")
        stem = part.rstrip(" .").split(".", 1)[0].upper()
        if stem in _WINDOWS_RESERVED:
            raise BootstrapError("archive_member_path_unsafe")
    return parts


def _validate_archive(archive: Path) -> tuple[str, tuple[zipfile.ZipInfo, ...]]:
    """Validate every ZIP member before extraction, returning its release version."""
    try:
        bundle = zipfile.ZipFile(archive)
    except (OSError, zipfile.BadZipFile) as exc:
        raise BootstrapError("core_archive_invalid") from exc
    try:
        infos = tuple(bundle.infolist())
        if not infos or len(infos) > _MAX_FILES or bundle.comment:
            raise BootstrapError("core_archive_invalid")
        seen: set[str] = set()
        member_keys: set[str] = set()
        total = 0
        root: str | None = None
        files: set[str] = set()
        for info in infos:
            if info.is_dir() or info.flag_bits & 0x1:
                raise BootstrapError("archive_member_unsafe")
            parts = _validate_member_path(info.filename)
            key = _portable_member_key(parts)
            if key in seen:
                raise BootstrapError("archive_member_collision")
            seen.add(key)
            member_keys.add(key)
            if root is None:
                root = parts[0]
            elif root != parts[0]:
                raise BootstrapError("core_archive_root_invalid")
            mode = info.external_attr >> 16
            type_bits = stat.S_IFMT(mode)
            if type_bits and type_bits != stat.S_IFREG:
                raise BootstrapError("archive_member_unsafe")
            if info.file_size < 0 or info.file_size > _MAX_UNCOMPRESSED:
                raise BootstrapError("archive_member_unsafe")
            total += info.file_size
            if total > _MAX_UNCOMPRESSED:
                raise BootstrapError("archive_member_unsafe")
            files.add("/".join(parts[1:]))
        for key in member_keys:
            parent = key.rpartition("/")[0]
            while parent:
                if parent in member_keys:
                    raise BootstrapError("archive_member_collision")
                parent = parent.rpartition("/")[0]
        if root is None:
            raise BootstrapError("core_archive_root_invalid")
        matched = _CORE_NAME.fullmatch(root)
        if matched is None or not _REQUIRED_CORE_FILES.issubset(files):
            raise BootstrapError("core_archive_layout_invalid")
        return matched.group(1), infos
    finally:
        bundle.close()


def _mkdir_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise BootstrapError("install_path_unsafe")


def _write_atomic(path: Path, data: bytes, *, executable: bool = False) -> None:
    _mkdir_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if executable:
            os.chmod(temporary_path, 0o755)
        os.replace(temporary_path, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        except OSError:
            pass
        finally:
            os.close(directory_fd)
    finally:
        temporary_path.unlink(missing_ok=True)


def _extract_verified_archive(archive: Path, infos: tuple[zipfile.ZipInfo, ...], destination: Path) -> Path:
    _mkdir_directory(destination)
    try:
        bundle = zipfile.ZipFile(archive)
        for info in infos:
            parts = _validate_member_path(info.filename)
            target = destination.joinpath(*parts)
            _mkdir_directory(target.parent)
            if target.exists() or target.is_symlink():
                raise BootstrapError("archive_member_collision")
            with bundle.open(info, "r") as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            os.chmod(target, 0o644)
    except (OSError, zipfile.BadZipFile) as exc:
        raise BootstrapError("core_archive_extract_failed") from exc
    finally:
        if "bundle" in locals():
            bundle.close()
    roots = [item for item in destination.iterdir()]
    if len(roots) != 1 or roots[0].is_symlink() or not roots[0].is_dir():
        raise BootstrapError("core_archive_layout_invalid")
    return roots[0]


def _venv_python(venv_path: Path) -> Path:
    name = "python.exe" if os.name == "nt" else "python"
    return venv_path / ("Scripts" if os.name == "nt" else "bin") / name


def _core_metadata(core: Path) -> tuple[list[str], str, str]:
    try:
        metadata = tomllib.loads((core / "pyproject.toml").read_text(encoding="utf-8"))
        dependencies = metadata.get("project", {}).get("dependencies", [])
        entry = metadata.get("project", {}).get("scripts", {}).get("chatmaker-install")
    except (AttributeError, OSError, tomllib.TOMLDecodeError) as exc:
        raise BootstrapError("core_metadata_invalid") from exc
    if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
        raise BootstrapError("core_metadata_invalid")
    if not isinstance(entry, str):
        raise BootstrapError("core_metadata_invalid")
    matched = _ENTRY_POINT.fullmatch(entry)
    if matched is None:
        raise BootstrapError("core_metadata_invalid")
    return dependencies, matched.group(1), matched.group(2)


def _run_entrypoint(venv_path: Path, module: str, callable_name: str, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    # Avoid generated Windows .exe/.py console wrappers: setuptools emits a
    # non-UTF-8 shebang for some Unicode target paths.  This is the exact same
    # declared console entry point, executed by the pinned venv interpreter.
    program = (
        "from importlib import import_module; import sys; "
        "module, callable_name=sys.argv[1:3]; sys.argv=[sys.argv[0], *sys.argv[3:]]; "
        "sys.exit(getattr(import_module(module), callable_name)())"
    )
    return subprocess.run(
        [str(_venv_python(venv_path)), "-c", program, module, callable_name, *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _entrypoint_available(venv_path: Path, module: str, callable_name: str) -> bool:
    probe = (
        "from importlib import import_module; import sys; "
        "getattr(import_module(sys.argv[1]), sys.argv[2])"
    )
    return subprocess.run(
        [str(_venv_python(venv_path)), "-c", probe, module, callable_name],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    ).returncode == 0


def _install_core(core: Path, venv_path: Path, dependencies: list[str], module: str, callable_name: str) -> None:
    venv.EnvBuilder(with_pip=True, system_site_packages=True, clear=False).create(venv_path)
    python = _venv_python(venv_path)
    if not python.is_file():
        raise BootstrapError("venv_creation_failed")
    if dependencies:
        dependency_install = subprocess.run(
            [
                str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                *dependencies,
            ],
            cwd=core,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if dependency_install.returncode:
            raise BootstrapError(
                f"core_dependency_install_failed: {dependency_install.stderr.strip() or dependency_install.stdout.strip()}"
            )
    completed = subprocess.run(
        [
            str(python), "-c", "from setuptools import setup; setup()", "--no-user-cfg",
            "install", "--single-version-externally-managed", "--record", "install-record.txt",
        ],
        cwd=core,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise BootstrapError(f"core_install_failed: {completed.stderr.strip() or completed.stdout.strip()}")
    if not _entrypoint_available(venv_path, module, callable_name):
        raise BootstrapError("core_install_missing_auto_installer")


def _run_auto(venv_path: Path, module: str, callable_name: str) -> dict[str, Any]:
    completed = _run_entrypoint(venv_path, module, callable_name, ["auto"])
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BootstrapError("auto_installer_report_invalid") from exc
    if not isinstance(value, dict):
        raise BootstrapError("auto_installer_report_invalid")
    if completed.returncode or not value.get("success"):
        detail = str(value.get("detail") or completed.stderr.strip() or "auto installer failed")
        raise BootstrapError(f"auto_installer_failed: {detail}")
    return value


def _launcher_bytes(version: str, venv_path: Path, module: str, callable_name: str) -> tuple[str, bytes, bool]:
    program = (
        "from importlib import import_module; import sys; "
        "module, callable_name=sys.argv[1:3]; sys.argv=[sys.argv[0], *sys.argv[3:]]; "
        "sys.exit(getattr(import_module(module), callable_name)())"
    )
    if os.name == "nt":
        # %~dp0 avoids putting a Unicode HOME into this batch file. cmd.exe
        # otherwise decodes the UTF-8 script using the active ANSI codepage.
        # %* preserves ordinary CLI arguments; module/callable are validated.
        python = f"%~dp0..\\versions\\{version}\\venv\\Scripts\\python.exe"
        return "chatmaker-install.cmd", (
            f'@echo off\r\n"{python}" -c "{program}" "{module}" "{callable_name}" %*\r\n'
        ).encode("utf-8"), False
    return "chatmaker-install", (
        f"#!/bin/sh\nexec {shlex.quote(str(_venv_python(venv_path)))} -c {shlex.quote(program)} "
        f"{shlex.quote(module)} {shlex.quote(callable_name)} \"$@\"\n"
    ).encode("utf-8"), True


def _activate(home_root: Path, version: str, digest: str, venv_path: Path, module: str, callable_name: str) -> Path:
    bin_root = home_root / "bin"
    launcher_name, launcher, executable = _launcher_bytes(version, venv_path, module, callable_name)
    launcher_path = bin_root / launcher_name
    _write_atomic(launcher_path, launcher, executable=executable)
    _write_atomic(
        home_root / "active.json",
        _canonical_json({"schema_version": SCHEMA_VERSION, "version": version, "archive_sha256": digest}),
    )
    return launcher_path


def _state(version: str, digest: str, module: str, callable_name: str) -> bytes:
    return _canonical_json(
        {
            "schema_version": SCHEMA_VERSION,
            "version": version,
            "archive_sha256": digest,
            "installer_module": module,
            "installer_callable": callable_name,
        }
    )


def _existing_install(version_root: Path, version: str, digest: str, module: str, callable_name: str) -> bool:
    state_path = version_root / ".bootstrap.json"
    if not version_root.exists():
        return False
    if version_root.is_symlink() or not version_root.is_dir():
        raise BootstrapError("install_path_unsafe")
    try:
        state = state_path.read_bytes()
    except OSError as exc:
        raise BootstrapError("existing_version_untrusted") from exc
    if state != _state(version, digest, module, callable_name):
        raise BootstrapError("existing_version_conflicts_with_archive")
    if not _entrypoint_available(version_root / "venv", module, callable_name):
        raise BootstrapError("existing_version_untrusted")
    return True


def run(*, archive: Path, checksum: Path, home: Path | None = None) -> dict[str, Any]:
    if sys.version_info < (3, 11):
        raise BootstrapError("python_3_11_or_newer_required")
    archive = Path(archive).expanduser().resolve()
    checksum = Path(checksum).expanduser().resolve()
    if not archive.is_file() or archive.is_symlink():
        raise BootstrapError("core_archive_unreadable")
    if not checksum.is_file() or checksum.is_symlink():
        raise BootstrapError("checksum_file_unreadable")
    digest = _read_expected_checksum(archive, checksum)
    version, infos = _validate_archive(archive)

    selected_home = (Path.home() if home is None else Path(home).expanduser()).resolve()
    home_root = selected_home / ".chatmaker"
    versions = home_root / "versions"
    _mkdir_directory(versions)
    version_root = versions / version
    existing_core = version_root / f"ChatMaker-Core-{version}"
    dependencies, module, callable_name = (
        _core_metadata(existing_core) if version_root.exists() else ([], "", "")
    )
    if version_root.exists() and (version != version_root.name or not module):
        raise BootstrapError("existing_version_untrusted")
    already_current = _existing_install(version_root, version, digest, module, callable_name)
    if not already_current:
        staging = versions / f".{version}.staging-{uuid.uuid4().hex}"
        try:
            core = _extract_verified_archive(archive, infos, staging)
            dependencies, module, callable_name = _core_metadata(core)
            _install_core(core, staging / "venv", dependencies, module, callable_name)
            _write_atomic(staging / ".bootstrap.json", _state(version, digest, module, callable_name))
            if version_root.exists():
                raise BootstrapError("existing_version_conflicts_with_archive")
            os.replace(staging, version_root)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    venv_path = version_root / "venv"
    auto = _run_auto(venv_path, module, callable_name)
    launcher = _activate(home_root, version, digest, venv_path, module, callable_name)
    return {
        "success": True,
        "status": "already_current" if already_current else "installed",
        "version": version,
        "archive": str(archive),
        "sha256": digest,
        "venv": str(venv_path),
        "launcher": str(launcher),
        "auto": auto,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(description="Install a checked local ChatMaker Core release.")
    parser.add_argument("--archive", required=True, type=Path, help="local ChatMaker-Core-<version>.zip")
    parser.add_argument("--checksum", required=True, type=Path, help="matching release .zip.sha256 file")
    parser.add_argument("--home", type=Path, help="advanced: user home directory for this installation")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        result = run(archive=args.archive, checksum=args.checksum, home=args.home)
    except Exception as exc:
        result = {
            "success": False,
            "status": "failed",
            "error": type(exc).__name__,
            "detail": str(exc),
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

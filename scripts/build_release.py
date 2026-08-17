from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import stat
from typing import Any
import unicodedata
import zipfile

try:
    from packaging.version import InvalidVersion, Version
except ImportError:
    from pip._vendor.packaging.version import InvalidVersion, Version


CORE_PATHS = (
    "LICENSE", "README.md", "README_EN.md", "pyproject.toml", "scripts/bootstrap.py", "scripts/core_release_signature.py",
    "docs/installation.md", "examples", "packs/boards", "packs/components", "knowledge/boards", "knowledge/mechanical", "knowledge/fabrication",
    "packs/recipes", "packs/schemas", "runtime", "skills/chatduino", "skills/chatmaker", "skills/chatweb", "skills/chatcad",
)
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".playwright-cli", ".chatmaker-esp32-builds", ".chatmaker-esp32-cache"}
EXCLUDED_PATH_PREFIXES = {("knowledge_sources",)}
PLATFORM_TAGS = {"windows-amd64", "macos-x86_64", "macos-arm64"}
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_PROJECT = re.compile(r"[._-]+")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{number}" for number in range(1, 10)), *(f"LPT{number}" for number in range(1, 10))}
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)


class ReleaseError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wheel_metadata(path: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            if len(names) != 1:
                raise ReleaseError("prepared_runtime_invalid")
            fields = {}
            for line in archive.read(names[0]).decode("utf-8").splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    if key in {"Name", "Version"}:
                        fields[key] = value.strip()
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise ReleaseError("prepared_runtime_invalid") from exc
    if set(fields) != {"Name", "Version"}:
        raise ReleaseError("prepared_runtime_invalid")
    return _PROJECT.sub("-", fields["Name"]).lower(), fields["Version"]


def current_platform_tag() -> str:
    system, machine = platform.system(), platform.machine().lower()
    if system == "Windows" and machine in {"amd64", "x86_64"}:
        return "windows-amd64"
    if system == "Darwin" and machine == "x86_64":
        return "macos-x86_64"
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64"
    raise ReleaseError("unsupported_bootstrap_platform")


def release_zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(2026, 8, 14, 0, 0, 0))
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.flag_bits = 0
    info.internal_attr = 0
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    info.comment = b""
    return info


def _source_unsafe(path: Path) -> bool:
    try:
        value = path.lstat()
    except OSError:
        return True
    return path.is_symlink() or bool(getattr(value, "st_file_attributes", 0) & _REPARSE)


def _walk_source(directory: Path, root: Path) -> list[Path]:
    files: list[Path] = []
    portable: set[str] = set()
    try:
        entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
    except OSError as exc:
        raise ReleaseError("core_source_unreadable") from exc
    for entry in entries:
        path = Path(entry.path)
        relative = path.relative_to(root).parts
        key = "/".join(unicodedata.normalize("NFC", part).rstrip(" .").casefold() for part in relative)
        if key in portable or entry.is_symlink() or _source_unsafe(path):
            raise ReleaseError(f"core_source_symlink_rejected:{path.relative_to(root).as_posix()}")
        portable.add(key)
        if entry.is_dir(follow_symlinks=False):
            files.extend(_walk_source(path, root))
        elif entry.is_file(follow_symlinks=False):
            files.append(path)
        else:
            raise ReleaseError(f"core_source_special_rejected:{path.relative_to(root).as_posix()}")
    return files


def _core_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in CORE_PATHS:
        path = root / relative
        if _source_unsafe(path):
            raise ReleaseError(f"core_source_symlink_rejected:{relative}")
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(_walk_source(path, root))
        else:
            raise ReleaseError(f"required_core_path_missing:{relative}")
    return sorted(
        (path for path in files if not EXCLUDED_PARTS.intersection(path.relative_to(root).parts)
         and not any(path.relative_to(root).parts[:len(prefix)] == prefix for prefix in EXCLUDED_PATH_PREFIXES)
         and not any(part.endswith(".egg-info") for part in path.relative_to(root).parts)
         and path.suffix.casefold() not in {".pyc", ".pyo"}),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def _read_prepared(prepared_root: Path, platform_tag: str) -> tuple[dict[str, Any], Path, bytes]:
    if platform_tag not in PLATFORM_TAGS or not prepared_root.is_dir() or _source_unsafe(prepared_root):
        raise ReleaseError("prepared_runtime_missing")
    manifest_path, requirements_path, wheelhouse = prepared_root / "manifest.json", prepared_root / "requirements.txt", prepared_root / "wheelhouse"
    if any(_source_unsafe(path) for path in (manifest_path, requirements_path, wheelhouse)):
        raise ReleaseError("prepared_runtime_invalid")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        requirements = requirements_path.read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseError("prepared_runtime_invalid") from exc
    if (manifest_bytes != canonical_json(manifest) or manifest.get("schema_version") != 2
            or manifest.get("platform_tag") != platform_tag
            or manifest.get("python_requires") != "==3.11.*"):
        raise ReleaseError("prepared_runtime_invalid")
    wheels = manifest.get("wheels")
    if not isinstance(wheels, list) or not isinstance(manifest.get("core_wheel"), str):
        raise ReleaseError("prepared_runtime_invalid")
    prepare_path = Path(__file__).with_name("prepare_core_runtime.py")
    spec = importlib.util.spec_from_file_location("chatmaker_prepare_core_runtime_for_builder", prepare_path)
    if spec is None or spec.loader is None:
        raise ReleaseError("prepared_runtime_invalid")
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    expected: set[str] = set(); projects: dict[str, str] = {}; dependencies: dict[str, set[str]] = {}; requirement_objects: dict[str, tuple[Any, ...]] = {}
    requirement_lines: dict[str, bytes] = {}
    for item in wheels:
        if not isinstance(item, dict) or set(item) != {"filename", "project", "version", "size", "sha256", "tags", "requires"}:
            raise ReleaseError("prepared_runtime_invalid")
        filename, digest, size = item["filename"], item["sha256"], item["size"]
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".whl") or not filename.isascii() or not isinstance(digest, str) or _SHA.fullmatch(digest) is None or not isinstance(size, int) or size <= 0:
            raise ReleaseError("prepared_runtime_invalid")
        wheel = wheelhouse / filename
        if _source_unsafe(wheel) or not wheel.is_file() or wheel.stat().st_size != size or sha256(wheel) != digest:
            raise ReleaseError("prepared_runtime_invalid")
        project, version, tags, parsed_requirements = prepare.wheel_metadata(wheel, platform_tag)
        prepare.validate_wheel_record(wheel)
        requires = sorted(prepare.normalize_project(requirement.name) for requirement in parsed_requirements)
        if (project != item["project"] or version != item["version"]
                or sorted(tags) != item["tags"] or requires != item["requires"]
                or project in projects):
            raise ReleaseError("prepared_runtime_invalid")
        projects[project] = version
        dependencies[project] = set(requires)
        requirement_objects[project] = parsed_requirements
        expected.add(filename)
        requirement_lines[project] = f"{item['project']}=={item['version']} --hash=sha256:{digest}\n".encode("ascii")
    actual = {path.name for path in wheelhouse.iterdir()} if wheelhouse.is_dir() and not wheelhouse.is_symlink() else set()
    if actual != expected or manifest["core_wheel"] not in expected or requirements.splitlines(keepends=True) != [requirement_lines[project] for project in sorted(requirement_lines)]:
        raise ReleaseError("prepared_runtime_invalid")
    for project, parsed_requirements in requirement_objects.items():
        for requirement in parsed_requirements:
            dependency = prepare.normalize_project(requirement.name)
            if dependency not in projects or (requirement.specifier and projects[dependency] not in requirement.specifier):
                raise ReleaseError("prepared_runtime_invalid")
    core_project = next(item["project"] for item in wheels if item["filename"] == manifest["core_wheel"])
    reachable = {core_project}; pending = [core_project]
    while pending:
        for dependency in dependencies[pending.pop()]:
            if dependency not in reachable:
                reachable.add(dependency); pending.append(dependency)
    if reachable != set(projects):
        raise ReleaseError("prepared_runtime_invalid")
    return manifest, wheelhouse, requirements


def build_release(
    root: Path,
    output_dir: Path,
    version: str,
    *,
    platform_tag: str | None = None,
    prepared_root: Path | None = None,
    release_sequence: int = 1,
) -> dict[str, object]:
    root, output_dir = Path(root).resolve(), Path(output_dir).resolve()
    if (_VERSION.fullmatch(version) is None or version != version.rstrip(" .") or unicodedata.normalize("NFC", version) != version
            or version.rstrip(" .").split(".", 1)[0].upper() in _WINDOWS_RESERVED or "/" in version or "\\" in version
            or not isinstance(release_sequence, int) or isinstance(release_sequence, bool) or release_sequence < 1):
        raise ReleaseError("release_version_invalid")
    selected = current_platform_tag() if platform_tag is None else platform_tag
    if selected not in PLATFORM_TAGS:
        raise ReleaseError("unsupported_bootstrap_platform")
    prepared = Path(os.path.abspath(prepared_root)) if prepared_root is not None else root / "distribution" / "core-runtime" / "prepared" / selected
    manifest, wheelhouse, requirements = _read_prepared(prepared, selected)
    core = next(item for item in manifest["wheels"] if item["filename"] == manifest["core_wheel"])
    try:
        versions_match = Version(core["version"]) == Version(version)
    except InvalidVersion as exc:
        raise ReleaseError("core_wheel_version_mismatch") from exc
    if not versions_match:
        raise ReleaseError("core_wheel_version_mismatch")
    output_dir.mkdir(parents=True, exist_ok=True)
    package_name = f"ChatMaker-Core-{version}-{selected}"
    archive = output_dir / f"{package_name}.zip"
    payload: list[tuple[str, bytes]] = []
    payload.extend((path.relative_to(root).as_posix(), path.read_bytes()) for path in _core_files(root))
    payload.append(("core-runtime/manifest.json", canonical_json(manifest)))
    payload.append(("core-runtime/requirements.txt", requirements))
    payload.extend((f"core-runtime/wheelhouse/{item['filename']}", (wheelhouse / item["filename"]).read_bytes()) for item in manifest["wheels"])
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        bundle.comment = b""
        for relative, data in sorted(payload, key=lambda item: item[0]):
            bundle.writestr(release_zip_info(f"{package_name}/{relative}"), data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = sha256(archive)
    checksum = output_dir / f"{archive.name}.sha256"
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii", newline="\n")
    release_manifest = output_dir / f"{archive.name}.manifest.json"
    release_manifest.write_bytes(canonical_json({
        "schema_version": 1,
        "release_sequence": release_sequence,
        "core_version": version,
        "core_wheel_version": core["version"],
        "platform_tag": selected,
        "python_tag": "cp311",
        "archive": {"filename": archive.name, "size": archive.stat().st_size, "sha256": digest},
        "runtime_manifest_sha256": hashlib.sha256(canonical_json(manifest)).hexdigest(),
        "release_metadata": {
            "archive_format": "zip",
            "compression": "deflate-9",
            "member_count": len(payload),
            "timestamp": "2026-08-14T00:00:00Z",
        },
    }))
    return {"success": True, "version": version, "platform_tag": selected, "archive": str(archive), "checksum_file": str(checksum), "release_manifest": str(release_manifest), "sha256": digest, "size_bytes": archive.stat().st_size, "file_count": len(payload), "release_sequence": release_sequence}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic platform-specific offline ChatMaker Core ZIP.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--version", default="0.1.0-rc5")
    parser.add_argument("--platform-tag", choices=tuple(sorted(PLATFORM_TAGS)))
    parser.add_argument("--prepared-root", type=Path)
    parser.add_argument("--release-sequence", type=int, default=1)
    args = parser.parse_args()
    try:
        result = build_release(args.root, args.output, args.version, platform_tag=args.platform_tag, prepared_root=args.prepared_root, release_sequence=args.release_sequence)
    except Exception as exc:
        result = {"success": False, "error": type(exc).__name__, "detail": str(exc)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

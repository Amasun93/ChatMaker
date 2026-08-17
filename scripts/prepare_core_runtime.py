"""Official, network-permitted preparation of a hash-locked Core wheelhouse.

This is a release-engineering command, never invoked by runtime bootstrap.
"""

from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any
import zipfile

try:
    from packaging.markers import default_environment
    from packaging.requirements import Requirement
    from packaging.utils import parse_wheel_filename
except ImportError:  # controlled build environments always include pip's vendored packaging
    from pip._vendor.packaging.markers import default_environment
    from pip._vendor.packaging.requirements import Requirement
    from pip._vendor.packaging.utils import parse_wheel_filename


_PROJECT = re.compile(r"[._-]+")
_LOCK = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)\Z")
_PLATFORMS = {
    "windows-amd64": "win_amd64",
    "macos-x86_64": "macosx_10_9_x86_64",
    "macos-arm64": "macosx_11_0_arm64",
}
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)


class PreparationError(RuntimeError):
    pass


_BOOTSTRAP_VALIDATOR = None


def validate_wheel_record(path: Path) -> None:
    global _BOOTSTRAP_VALIDATOR
    if _BOOTSTRAP_VALIDATOR is None:
        bootstrap_path = Path(__file__).with_name("bootstrap.py")
        spec = importlib.util.spec_from_file_location("chatmaker_bootstrap_wheel_validator", bootstrap_path)
        if spec is None or spec.loader is None:
            raise PreparationError("wheel_record_validator_unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _BOOTSTRAP_VALIDATOR = module
    try:
        _BOOTSTRAP_VALIDATOR._wheel_contract(path)
    except Exception as exc:
        raise PreparationError("wheel_record_invalid") from exc


def normalize_project(value: str) -> str:
    return _PROJECT.sub("-", value).lower()


def _unsafe_path(path: Path) -> bool:
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & _REPARSE)
    except OSError:
        return True


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_lock(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PreparationError("requirements_lock_unreadable") from exc
    values: dict[str, str] = {}
    for raw in lines:
        value = raw.split("#", 1)[0].strip()
        if not value:
            continue
        matched = _LOCK.fullmatch(value)
        if matched is None:
            raise PreparationError("requirements_lock_invalid")
        project, version = normalize_project(matched.group(1)), matched.group(2)
        if project in values or not version:
            raise PreparationError("requirements_lock_invalid")
        values[project] = version
    if not values:
        raise PreparationError("requirements_lock_invalid")
    return values


def _marker_environment(platform_tag: str) -> dict[str, str]:
    environment = default_environment()
    environment.update({"python_version": "3.11", "python_full_version": "3.11.0", "implementation_name": "cpython", "platform_python_implementation": "CPython"})
    if platform_tag == "windows-amd64":
        environment.update({"os_name": "nt", "sys_platform": "win32", "platform_system": "Windows", "platform_machine": "AMD64"})
    elif platform_tag == "macos-x86_64":
        environment.update({"os_name": "posix", "sys_platform": "darwin", "platform_system": "Darwin", "platform_machine": "x86_64"})
    else:
        environment.update({"os_name": "posix", "sys_platform": "darwin", "platform_system": "Darwin", "platform_machine": "arm64"})
    return environment


def wheel_metadata(path: Path, platform_tag: str) -> tuple[str, str, tuple[str, ...], tuple[Requirement, ...]]:
    try:
        with zipfile.ZipFile(path) as archive:
            candidates = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            if len(candidates) != 1:
                raise PreparationError("wheel_metadata_invalid")
            metadata_text = archive.read(candidates[0]).decode("utf-8")
            metadata = Parser().parsestr(metadata_text)
            fields = {key: metadata.get(key) for key in ("Name", "Version")}
            wheel_files = [name for name in archive.namelist() if name.endswith(".dist-info/WHEEL")]
            if len(wheel_files) != 1:
                raise PreparationError("wheel_metadata_invalid")
            tags = tuple(
                line.split(":", 1)[1].strip()
                for line in archive.read(wheel_files[0]).decode("utf-8").splitlines()
                if line.startswith("Tag:")
            )
            environment = _marker_environment(platform_tag)
            requirements = tuple(
                requirement
                for raw in metadata.get_all("Requires-Dist", [])
                for requirement in (Requirement(raw),)
                if requirement.marker is None or requirement.marker.evaluate(environment)
            )
            filename_project, filename_version, _, filename_tags = parse_wheel_filename(path.name)
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise PreparationError("wheel_metadata_invalid") from exc
    if not all(fields.values()) or not tags:
        raise PreparationError("wheel_metadata_invalid")
    project = normalize_project(str(fields["Name"]))
    version = str(fields["Version"])
    if (normalize_project(filename_project) != project or str(filename_version) != version
            or {str(tag) for tag in filename_tags} != set(tags)):
        raise PreparationError("wheel_metadata_invalid")
    return project, version, tags, requirements


def _tag_supports_platform(tag: str, platform_tag: str) -> bool:
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
    if platform_tag == "macos-x86_64":
        return wheel_platform.startswith("macosx_") and wheel_platform.endswith(("_x86_64", "_universal2"))
    if platform_tag == "macos-arm64":
        return wheel_platform.startswith("macosx_") and wheel_platform.endswith(("_arm64", "_universal2"))
    return False


def prepare_manifest(*, wheelhouse: Path, lock_path: Path, platform_tag: str, core_wheel: str) -> dict[str, Any]:
    """Validate a completed wheelhouse and return canonical runtime evidence."""
    if platform_tag not in _PLATFORMS:
        raise PreparationError("platform_unsupported")
    lock = read_lock(lock_path)
    if not wheelhouse.is_dir() or _unsafe_path(wheelhouse):
        raise PreparationError("wheelhouse_unsafe")
    wheels = sorted(wheelhouse.glob("*.whl"), key=lambda item: item.name.casefold())
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for wheel in wheels:
        if _unsafe_path(wheel) or not wheel.is_file() or wheel.name != wheel.name.encode("ascii", "strict").decode("ascii"):
            raise PreparationError("wheelhouse_unsafe")
        project, version, tags, requirements = wheel_metadata(wheel, platform_tag)
        validate_wheel_record(wheel)
        if not any(_tag_supports_platform(tag, platform_tag) for tag in tags):
            raise PreparationError("wheel_platform_mismatch")
        if project in seen or (project != "chatmaker" and lock.get(project) != version):
            raise PreparationError("wheelhouse_lock_mismatch")
        if project == "chatmaker" and wheel.name != core_wheel:
            raise PreparationError("core_wheel_invalid")
        seen.add(project)
        entries.append({
            "filename": wheel.name,
            "project": project,
            "version": version,
            "size": wheel.stat().st_size,
            "sha256": sha256(wheel),
            "tags": sorted(tags),
            "requires": sorted(normalize_project(requirement.name) for requirement in requirements),
        })
    if set(lock) != (seen - {"chatmaker"}) or "chatmaker" not in seen:
        raise PreparationError("wheelhouse_lock_mismatch")
    versions = {entry["project"]: entry["version"] for entry in entries}
    dependencies = {entry["project"]: set(entry["requires"]) for entry in entries}
    for wheel in wheels:
        project, _, _, requirements = wheel_metadata(wheel, platform_tag)
        for requirement in requirements:
            dependency = normalize_project(requirement.name)
            if dependency not in versions or (requirement.specifier and versions[dependency] not in requirement.specifier):
                raise PreparationError("wheelhouse_dependency_closure_invalid")
    reachable = {"chatmaker"}
    pending = ["chatmaker"]
    while pending:
        project = pending.pop()
        for dependency in dependencies.get(project, set()):
            if dependency not in reachable:
                reachable.add(dependency)
                pending.append(dependency)
    if reachable != seen:
        raise PreparationError("wheelhouse_dependency_closure_invalid")
    return {
        "schema_version": 2,
        "platform_tag": platform_tag,
        "python_requires": "==3.11.*",
        "core_wheel": core_wheel,
        "wheels": entries,
    }


def _run(command: list[str], *, cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode:
        raise PreparationError(completed.stderr.strip() or completed.stdout.strip() or "release_preparation_failed")


def prepare(*, source_root: Path, output_root: Path, lock_path: Path, platform_tag: str) -> dict[str, Any]:
    """Build/download an official platform wheelhouse; network is allowed only here."""
    if platform_tag not in _PLATFORMS:
        raise PreparationError("platform_unsupported")
    lock = read_lock(lock_path)
    target = output_root / platform_tag
    wheelhouse = target / "wheelhouse"
    wheelhouse.mkdir(parents=True, exist_ok=True)
    _run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheelhouse), str(source_root)], cwd=source_root)
    core_candidates = sorted(wheelhouse.glob("chatmaker-*.whl"))
    if len(core_candidates) != 1:
        raise PreparationError("core_wheel_invalid")
    download = [
        sys.executable, "-m", "pip", "download", "--only-binary=:all:", "--no-deps",
        "--dest", str(wheelhouse), "--platform", _PLATFORMS[platform_tag],
        "--implementation", "cp", "--python-version", "311", "--abi", "cp311",
    ]
    download.extend(f"{project}=={version}" for project, version in sorted(lock.items()))
    _run(download, cwd=source_root)
    manifest = prepare_manifest(
        wheelhouse=wheelhouse,
        lock_path=lock_path,
        platform_tag=platform_tag,
        core_wheel=core_candidates[0].name,
    )
    requirements = "".join(
        f"{item['project']}=={item['version']} --hash=sha256:{item['sha256']}\n"
        for item in sorted(manifest["wheels"], key=lambda item: item["project"])
    )
    (target / "requirements.txt").write_text(requirements, encoding="ascii", newline="\n")
    (target / "manifest.json").write_bytes(canonical_json(manifest))
    return {"success": True, "platform_tag": platform_tag, "prepared_root": str(target), "wheel_count": len(manifest["wheels"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare an official offline ChatMaker Core runtime bundle.")
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=Path(__file__).resolve().parents[1] / "distribution" / "core-runtime" / "requirements.lock")
    parser.add_argument("--platform-tag", choices=tuple(_PLATFORMS), required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(source_root=args.source_root.resolve(), output_root=args.output.resolve(), lock_path=args.lock.resolve(), platform_tag=args.platform_tag)
    except Exception as exc:
        result = {"success": False, "error": type(exc).__name__, "detail": str(exc)}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

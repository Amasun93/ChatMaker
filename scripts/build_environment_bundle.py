from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any
import zipfile


_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_PLATFORM = "windows-amd64"


class EnvironmentBundleError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def _zip_info(name: str) -> zipfile.ZipInfo:
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


def _python_artifact(source_root: Path, python_archive: Path) -> dict[str, Any]:
    try:
        registry = json.loads(
            (source_root / "runtime/chatmaker/installers/runtime_sources.json").read_text(encoding="utf-8")
        )
        artifact = registry["python"][_PLATFORM]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise EnvironmentBundleError("python_source_registry_invalid") from exc
    required = {"version", "filename", "size", "sha256"}
    if not isinstance(artifact, dict) or not required.issubset(artifact):
        raise EnvironmentBundleError("python_source_registry_invalid")
    if (
        python_archive.name != artifact["filename"]
        or python_archive.stat().st_size != artifact["size"]
        or _sha256(python_archive) != artifact["sha256"]
    ):
        raise EnvironmentBundleError("python_archive_identity_mismatch")
    return {key: artifact[key] for key in ("version", "build", "filename", "size", "sha256", "archive_root") if key in artifact}


def _core_payload(core_archive: Path, version: str) -> tuple[list[tuple[str, bytes]], dict[str, Any]]:
    expected_root = f"ChatMaker-Core-{version}-{_PLATFORM}"
    payload: list[tuple[str, bytes]] = []
    try:
        with zipfile.ZipFile(core_archive) as archive:
            files = [item for item in archive.infolist() if not item.is_dir()]
            if not files:
                raise EnvironmentBundleError("core_archive_invalid")
            for item in files:
                path = PurePosixPath(item.filename)
                if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != expected_root:
                    raise EnvironmentBundleError("core_archive_invalid")
                relative = PurePosixPath(*path.parts[1:])
                if not relative.parts:
                    raise EnvironmentBundleError("core_archive_invalid")
                payload.append((f"core/{relative.as_posix()}", archive.read(item)))
    except (OSError, zipfile.BadZipFile) as exc:
        raise EnvironmentBundleError("core_archive_invalid") from exc
    return payload, {
        "filename": core_archive.name,
        "size": core_archive.stat().st_size,
        "sha256": _sha256(core_archive),
    }


def build_environment_bundle(
    *,
    source_root: Path,
    core_archive: Path,
    python_archive: Path,
    output_dir: Path,
    version: str,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    core_archive = core_archive.resolve()
    python_archive = python_archive.resolve()
    output_dir = output_dir.resolve()
    if not _VERSION.fullmatch(version):
        raise EnvironmentBundleError("environment_version_invalid")
    installer = source_root / "scripts/install_environment_bundle.ps1"
    if not installer.is_file():
        raise EnvironmentBundleError("environment_installer_missing")
    python = _python_artifact(source_root, python_archive)
    core_files, core = _core_payload(core_archive, version)
    environment_manifest = {
        "schema_version": 1,
        "environment_version": version,
        "platform_tag": _PLATFORM,
        "contents": {"core": "offline-wheelhouse", "python": "portable", "node": "not-included"},
        "core": core,
        "python": python,
    }
    package_name = f"ChatMaker-Environment-{version}-{_PLATFORM}"
    payload = [
        ("install.ps1", installer.read_bytes()),
        ("environment-manifest.json", _canonical_json(environment_manifest)),
        (f"cache/{python_archive.name}", python_archive.read_bytes()),
        *core_files,
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{package_name}.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, data in sorted(payload, key=lambda item: item[0]):
            archive.writestr(
                _zip_info(f"{package_name}/{relative}"),
                data,
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    digest = _sha256(archive_path)
    checksum = output_dir / f"{archive_path.name}.sha256"
    checksum.write_text(f"{digest}  {archive_path.name}\n", encoding="ascii", newline="\n")
    release_manifest = output_dir / f"{archive_path.name}.manifest.json"
    release_manifest.write_bytes(
        _canonical_json(
            {
                "schema_version": 1,
                "environment_version": version,
                "platform_tag": _PLATFORM,
                "archive": {
                    "filename": archive_path.name,
                    "size": archive_path.stat().st_size,
                    "sha256": digest,
                },
                "python": python,
                "core": core,
            }
        )
    )
    return {
        "success": True,
        "archive": str(archive_path),
        "checksum_file": str(checksum),
        "release_manifest": str(release_manifest),
        "sha256": digest,
        "size_bytes": archive_path.stat().st_size,
        "file_count": len(payload),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the offline Windows ChatMaker environment ZIP.")
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--core-archive", type=Path, required=True)
    parser.add_argument("--python-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        result = build_environment_bundle(
            source_root=args.source_root,
            core_archive=args.core_archive,
            python_archive=args.python_archive,
            output_dir=args.output,
            version=args.version,
        )
    except Exception as exc:
        result = {"success": False, "error": type(exc).__name__, "detail": str(exc)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

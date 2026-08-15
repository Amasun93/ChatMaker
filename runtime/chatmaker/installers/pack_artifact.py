"""Deterministic building and safe validation of passive ``.cmpack`` ZIPs."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Mapping

import jsonschema


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_SCHEMA_PATH = _REPO_ROOT / "packs" / "schemas" / "pack-manifest.schema.json"
_PAYLOAD_PATTERN = re.compile(
    r"^llmwiki/(?:index\.yaml|sections/[a-z0-9][a-z0-9-]*\.md)$"
)
_SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}

DEFAULT_MAX_FILES = 66
DEFAULT_MAX_SINGLE_FILE_BYTES = 65_536
DEFAULT_MAX_TOTAL_BYTES = 65 * 65_536 + 65_536
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_ZIP_MODE = stat.S_IFREG | 0o644
_WINDOWS_REPARSE_POINT = 0x400


class PackArtifactError(Exception):
    """Stable pack validation failure."""

    def __init__(self, code: str, *, reason: str, path: str | None = None) -> None:
        self.code = code
        self.reason = reason
        self.path = path
        detail = f"{code}: {reason}"
        if path is not None:
            detail += f": {path}"
        super().__init__(detail)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "reason": self.reason}
        if self.path is not None:
            result["path"] = self.path
        return result


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _utf8_path_key(path: str) -> bytes:
    return path.encode("utf-8")


def _version(value: str, *, field: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or _SEMVER_PATTERN.fullmatch(value) is None:
        raise PackArtifactError("pack_incompatible", reason=f"invalid_{field}")
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def validate_archive_path(path: str) -> str:
    """Validate a ZIP name using portable POSIX and strict Windows semantics."""

    if not isinstance(path, str) or not path:
        raise PackArtifactError("pack_archive_unsafe", reason="empty_path")
    try:
        path.encode("ascii")
    except UnicodeEncodeError as exc:
        raise PackArtifactError(
            "pack_archive_unsafe", reason="non_ascii_path", path=path
        ) from exc
    if path.startswith(("/", "\\")):
        raise PackArtifactError("pack_archive_unsafe", reason="absolute_or_unc_path", path=path)
    if "\\" in path:
        raise PackArtifactError("pack_archive_unsafe", reason="backslash_path", path=path)
    if re.match(r"^[A-Za-z]:", path):
        raise PackArtifactError("pack_archive_unsafe", reason="drive_relative_path", path=path)
    if ":" in path:
        raise PackArtifactError("pack_archive_unsafe", reason="alternate_data_stream", path=path)
    pure = PurePosixPath(path)
    if (
        pure.is_absolute()
        or pure.as_posix() != path
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise PackArtifactError("pack_archive_unsafe", reason="path_traversal", path=path)
    for part in pure.parts:
        if part.endswith((".", " ")):
            raise PackArtifactError(
                "pack_archive_unsafe", reason="trailing_dot_or_space", path=path
            )
        device_stem = part.split(".", 1)[0].upper()
        if device_stem in _RESERVED_WINDOWS_NAMES:
            raise PackArtifactError(
                "pack_archive_unsafe", reason="reserved_device_name", path=path
            )
    return path


def _manifest_schema() -> dict[str, Any]:
    try:
        value = json.loads(_MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackArtifactError("pack_manifest_invalid", reason="schema_unavailable") from exc
    if not isinstance(value, dict):
        raise PackArtifactError("pack_manifest_invalid", reason="schema_unavailable")
    return value


def _validate_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise PackArtifactError("pack_manifest_invalid", reason="manifest_not_object")
    try:
        jsonschema.Draft202012Validator(_manifest_schema()).validate(manifest)
    except jsonschema.ValidationError as exc:
        raise PackArtifactError("pack_manifest_invalid", reason="schema_validation_failed") from exc
    seen: set[str] = set()
    for item in manifest["files"]:
        path = item["path"]
        if path in seen:
            raise PackArtifactError(
                "pack_manifest_invalid", reason="duplicate_path", path=path
            )
        seen.add(path)
    return manifest


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, _ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = _ZIP_MODE << 16
    info.extra = b""
    info.comment = b""
    return info


def _source_files(source_dir: Path) -> list[tuple[str, bytes]]:
    if not source_dir.is_dir():
        raise PackArtifactError("pack_content_invalid", reason="source_directory_missing")
    files: list[tuple[str, bytes]] = []
    try:
        paths = sorted(
            (path for path in source_dir.rglob("*") if path.is_file()),
            key=lambda item: _utf8_path_key(item.relative_to(source_dir).as_posix()),
        )
    except OSError as exc:
        raise PackArtifactError("pack_content_invalid", reason="source_read_failed") from exc
    for path in paths:
        if path.is_symlink():
            raise PackArtifactError("pack_content_invalid", reason="source_symlink")
        relative = path.relative_to(source_dir).as_posix()
        validate_archive_path(relative)
        if _PAYLOAD_PATTERN.fullmatch(relative) is None:
            raise PackArtifactError(
                "pack_content_invalid", reason="source_path_not_allowed", path=relative
            )
        try:
            data = path.read_bytes()
            data.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise PackArtifactError(
                "pack_content_invalid", reason="source_bytes_invalid", path=relative
            ) from exc
        if not data or len(data) > DEFAULT_MAX_SINGLE_FILE_BYTES:
            raise PackArtifactError(
                "pack_content_invalid", reason="source_size_invalid", path=relative
            )
        files.append((relative, data))
    names = [path for path, _ in files]
    if names.count("llmwiki/index.yaml") != 1 or len(files) < 2 or len(files) > 65:
        raise PackArtifactError("pack_content_invalid", reason="source_layout_invalid")
    return files


def build_pack(
    source_dir: Path | str,
    output_path: Path | str,
    *,
    pack_id: str,
    pack_version: str,
    board_id: str,
    core_minimum: str,
    core_maximum_exclusive: str,
) -> dict[str, Any]:
    """Build one deterministic passive knowledge pack without rewriting payloads."""

    try:
        files = _source_files(Path(source_dir))
        manifest = {
            "schema_version": "1.0",
            "format_version": 1,
            "pack_id": pack_id,
            "pack_version": pack_version,
            "pack_type": "knowledge",
            "board_id": board_id,
            "compatibility": {
                "core": {
                    "minimum": core_minimum,
                    "maximum_exclusive": core_maximum_exclusive,
                },
                "llmwiki_index_schema": ["1.0"],
            },
            "files": [
                {
                    "path": path,
                    "length": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                for path, data in files
            ],
        }
        manifest = _validate_manifest(manifest)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.comment = b""
            archive.writestr(_zip_info("pack-manifest.json"), _canonical_json(manifest))
            for path, data in files:
                archive.writestr(_zip_info(path), data)
        return manifest
    except PackArtifactError:
        raise
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackArtifactError("pack_content_invalid", reason="pack_build_failed") from exc


def _open_archive(source: Path | str | bytes) -> tuple[zipfile.ZipFile, BinaryIO | None]:
    if isinstance(source, bytes):
        buffer = io.BytesIO(source)
        return zipfile.ZipFile(buffer, "r"), buffer
    return zipfile.ZipFile(Path(source), "r"), None


def _validate_entry_metadata(info: zipfile.ZipInfo) -> None:
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise PackArtifactError(
            "pack_archive_unsafe", reason="symlink_entry", path=info.filename
        )
    if info.is_dir() or info.filename.endswith("/"):
        raise PackArtifactError(
            "pack_archive_unsafe", reason="directory_entry", path=info.filename
        )
    if (
        info.compress_type != zipfile.ZIP_STORED
        or info.date_time != _ZIP_TIMESTAMP
        or info.create_system != 3
        or mode != _ZIP_MODE
        or info.extra != b""
        or info.comment != b""
    ):
        raise PackArtifactError(
            "pack_archive_unsafe", reason="noncanonical_zip_metadata", path=info.filename
        )


def _validate_compatibility(
    manifest: Mapping[str, Any],
    *,
    core_version: str,
    pack_manifest_schema: str,
    llmwiki_index_schema: str,
) -> None:
    current = _version(core_version, field="core_version")
    compatibility = manifest["compatibility"]
    minimum = _version(compatibility["core"]["minimum"], field="core_minimum")
    maximum = _version(
        compatibility["core"]["maximum_exclusive"], field="core_maximum_exclusive"
    )
    if not minimum <= current < maximum:
        raise PackArtifactError("pack_incompatible", reason="core_version_out_of_range")
    if pack_manifest_schema != manifest["schema_version"]:
        raise PackArtifactError("pack_incompatible", reason="manifest_schema_unsupported")
    if llmwiki_index_schema not in compatibility["llmwiki_index_schema"]:
        raise PackArtifactError("pack_incompatible", reason="llmwiki_schema_unsupported")


def validate_pack_archive(
    source: Path | str | bytes,
    *,
    core_version: str,
    pack_manifest_schema: str = "1.0",
    llmwiki_index_schema: str = "1.0",
    max_files: int = DEFAULT_MAX_FILES,
    max_single_file_bytes: int = DEFAULT_MAX_SINGLE_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> dict[str, Any]:
    """Validate the entire archive before any extraction is permitted."""

    archive: zipfile.ZipFile | None = None
    buffer: BinaryIO | None = None
    try:
        archive, buffer = _open_archive(source)
        infos = archive.infolist()
        if not infos or len(infos) > max_files:
            raise PackArtifactError("pack_archive_unsafe", reason="file_count_limit")
        if archive.comment != b"":
            raise PackArtifactError("pack_archive_unsafe", reason="archive_comment")
        total = 0
        seen_aliases: set[str] = set()
        for info in infos:
            validate_archive_path(info.filename)
            _validate_entry_metadata(info)
            alias = info.filename.casefold()
            if alias in seen_aliases:
                raise PackArtifactError(
                    "pack_archive_unsafe", reason="duplicate_or_alias_path", path=info.filename
                )
            seen_aliases.add(alias)
            if info.filename != "pack-manifest.json" and not info.filename.startswith("llmwiki/"):
                raise PackArtifactError(
                    "pack_archive_unsafe", reason="canonical_record_injection", path=info.filename
                )
            if info.file_size > max_single_file_bytes:
                raise PackArtifactError(
                    "pack_archive_unsafe", reason="single_file_size_limit", path=info.filename
                )
            total += info.file_size
            if total > max_total_bytes:
                raise PackArtifactError("pack_archive_unsafe", reason="total_size_limit")
        names = [info.filename for info in infos]
        if names[0] != "pack-manifest.json" or names.count("pack-manifest.json") != 1:
            raise PackArtifactError("pack_manifest_invalid", reason="manifest_not_first")
        try:
            manifest_bytes = archive.read("pack-manifest.json")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackArtifactError("pack_manifest_invalid", reason="manifest_json_invalid") from exc
        if _canonical_json(manifest) != manifest_bytes:
            raise PackArtifactError("pack_manifest_invalid", reason="manifest_not_canonical")
        manifest = _validate_manifest(manifest)
        expected_payload = [item["path"] for item in manifest["files"]]
        expected_order = ["pack-manifest.json", *sorted(expected_payload, key=_utf8_path_key)]
        if names != expected_order:
            raise PackArtifactError("pack_manifest_invalid", reason="archive_entries_mismatch")
        info_by_name = {info.filename: info for info in infos}
        for item in manifest["files"]:
            path = item["path"]
            if _PAYLOAD_PATTERN.fullmatch(path) is None:
                raise PackArtifactError(
                    "pack_manifest_invalid", reason="payload_path_not_allowed", path=path
                )
            data = archive.read(info_by_name[path])
            try:
                data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise PackArtifactError(
                    "pack_content_invalid", reason="payload_not_utf8", path=path
                ) from exc
            if len(data) != item["length"]:
                raise PackArtifactError(
                    "pack_content_invalid", reason="payload_length_mismatch", path=path
                )
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise PackArtifactError(
                    "pack_content_invalid", reason="payload_hash_mismatch", path=path
                )
        _validate_compatibility(
            manifest,
            core_version=core_version,
            pack_manifest_schema=pack_manifest_schema,
            llmwiki_index_schema=llmwiki_index_schema,
        )
        return manifest
    except PackArtifactError:
        raise
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError) as exc:
        raise PackArtifactError("pack_archive_unsafe", reason="invalid_zip") from exc
    except Exception as exc:
        raise PackArtifactError("pack_content_invalid", reason="archive_validation_failed") from exc
    finally:
        if archive is not None:
            archive.close()
        if buffer is not None:
            buffer.close()


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise PackArtifactError("pack_archive_unsafe", reason="staging_path_unreadable") from exc
    return bool(attributes & _WINDOWS_REPARSE_POINT)


def _assert_safe_staging_root(root: Path) -> None:
    for path in (root, *root.parents):
        if _is_link_or_reparse(path):
            raise PackArtifactError("pack_archive_unsafe", reason="staging_link_or_reparse")


def _safe_staging_files(root: Path) -> list[Path]:
    _assert_safe_staging_root(root)
    files: list[Path] = []
    try:
        for path in root.rglob("*"):
            if _is_link_or_reparse(path):
                raise PackArtifactError(
                    "pack_archive_unsafe",
                    reason="staging_link_or_reparse",
                    path=path.relative_to(root).as_posix(),
                )
            if path.is_file():
                files.append(path)
    except OSError as exc:
        raise PackArtifactError("pack_content_invalid", reason="staging_read_failed") from exc
    return files


def validate_staging(staging_dir: Path | str, manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    root = Path(staging_dir)
    if not root.is_dir():
        raise PackArtifactError("pack_content_invalid", reason="staging_missing")
    manifest = _validate_manifest(dict(manifest))
    files = _safe_staging_files(root)
    actual = sorted(path.relative_to(root).as_posix() for path in files)
    expected = sorted(["pack-manifest.json", *(item["path"] for item in manifest["files"])])
    if actual != expected:
        raise PackArtifactError("pack_content_invalid", reason="staging_entries_mismatch")
    try:
        manifest_path = root / "pack-manifest.json"
        if manifest_path.read_bytes() != _canonical_json(manifest):
            raise PackArtifactError("pack_content_invalid", reason="staging_manifest_mismatch")
        for item in manifest["files"]:
            data = (root / PurePosixPath(item["path"])).read_bytes()
            if (
                len(data) != item["length"]
                or hashlib.sha256(data).hexdigest() != item["sha256"]
            ):
                raise PackArtifactError(
                    "pack_content_invalid",
                    reason="staging_payload_mismatch",
                    path=item["path"],
                )
    except OSError as exc:
        raise PackArtifactError("pack_content_invalid", reason="staging_read_failed") from exc
    return manifest


def extract_validated_pack(
    source: Path | str | bytes,
    staging_dir: Path | str,
    *,
    core_version: str,
    pack_manifest_schema: str = "1.0",
    llmwiki_index_schema: str = "1.0",
    max_files: int = DEFAULT_MAX_FILES,
    max_single_file_bytes: int = DEFAULT_MAX_SINGLE_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> dict[str, Any]:
    try:
        archive_bytes = source if isinstance(source, bytes) else Path(source).read_bytes()
    except OSError as exc:
        raise PackArtifactError("pack_archive_unsafe", reason="archive_read_failed") from exc
    manifest = validate_pack_archive(
        archive_bytes,
        core_version=core_version,
        pack_manifest_schema=pack_manifest_schema,
        llmwiki_index_schema=llmwiki_index_schema,
        max_files=max_files,
        max_single_file_bytes=max_single_file_bytes,
        max_total_bytes=max_total_bytes,
    )
    destination = Path(staging_dir)
    try:
        _assert_safe_staging_root(destination)
        if destination.exists():
            if not destination.is_dir():
                raise PackArtifactError(
                    "pack_content_invalid", reason="staging_not_directory"
                )
            if any(destination.iterdir()):
                raise PackArtifactError("pack_content_invalid", reason="staging_not_empty")
        destination.mkdir(parents=True, exist_ok=True)
        _assert_safe_staging_root(destination)
    except PackArtifactError:
        raise
    except OSError as exc:
        raise PackArtifactError("pack_content_invalid", reason="staging_preflight_failed") from exc
    archive: zipfile.ZipFile | None = None
    buffer: BinaryIO | None = None
    try:
        archive, buffer = _open_archive(archive_bytes)
        for info in archive.infolist():
            target = destination.joinpath(*PurePosixPath(info.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackArtifactError("pack_content_invalid", reason="staging_extract_failed") from exc
    finally:
        if archive is not None:
            archive.close()
        if buffer is not None:
            buffer.close()
    validate_staging(destination, manifest)
    return manifest


__all__ = [
    "DEFAULT_MAX_FILES",
    "DEFAULT_MAX_SINGLE_FILE_BYTES",
    "DEFAULT_MAX_TOTAL_BYTES",
    "PackArtifactError",
    "build_pack",
    "extract_validated_pack",
    "validate_archive_path",
    "validate_pack_archive",
    "validate_staging",
]

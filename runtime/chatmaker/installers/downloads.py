"""Hash-locked domestic-first downloads for optional ChatMaker runtimes."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


SOURCE_REGISTRY = Path(__file__).with_name("runtime_sources.json")


class DownloadError(RuntimeError):
    """Raised only after every pinned source has failed."""


@dataclass(frozen=True)
class DownloadReceipt:
    changed: bool
    source_id: str
    source_kind: str
    source_host: str
    attempted_source_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed": self.changed,
            "source_id": self.source_id,
            "source_kind": self.source_kind,
            "source_host": self.source_host,
            "attempted_source_ids": list(self.attempted_source_ids),
        }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_runtime_sources(path: Path = SOURCE_REGISTRY) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DownloadError("runtime_source_registry_unreadable") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or value.get("policy") != "domestic-first"
    ):
        raise DownloadError("runtime_source_registry_invalid")
    return value


def runtime_artifact(kind: str, platform_tag: str = "windows-amd64") -> dict[str, Any]:
    registry = load_runtime_sources()
    group = registry.get(kind)
    item = group.get(platform_tag) if isinstance(group, dict) else None
    if not isinstance(item, dict):
        raise DownloadError("runtime_artifact_not_registered")
    _validate_artifact(item)
    return item


def package_sources(kind: str) -> list[dict[str, str]]:
    registry = load_runtime_sources()
    rows = registry.get(kind)
    if not isinstance(rows, list) or not rows:
        raise DownloadError("package_source_not_registered")
    result: list[dict[str, str]] = []
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {"id", "kind", "url"}
            or not all(isinstance(row[key], str) and row[key] for key in row)
        ):
            raise DownloadError("runtime_source_registry_invalid")
        result.append(dict(row))
    return result


def _validate_artifact(item: Mapping[str, Any]) -> None:
    sources = item.get("sources")
    if (
        not isinstance(item.get("filename"), str)
        or not item["filename"]
        or not isinstance(item.get("size"), int)
        or item["size"] <= 0
        or not isinstance(item.get("sha256"), str)
        or len(item["sha256"]) != 64
        or not isinstance(sources, list)
        or not sources
    ):
        raise DownloadError("runtime_artifact_invalid")
    for source in sources:
        if (
            not isinstance(source, dict)
            or set(source) != {"id", "kind", "url"}
            or not all(isinstance(source[key], str) and source[key] for key in source)
            or urlsplit(source["url"]).scheme != "https"
        ):
            raise DownloadError("runtime_artifact_invalid")


def _candidate_sources(item: Mapping[str, Any]) -> list[dict[str, str]]:
    _validate_artifact(item)
    result: list[dict[str, str]] = []
    custom = os.environ.get("CHATMAKER_DOWNLOAD_MIRROR_BASE", "").strip().rstrip("/")
    if custom:
        parsed = urlsplit(custom)
        if parsed.scheme != "https" or not parsed.netloc:
            raise DownloadError("custom_mirror_must_use_https")
        result.append(
            {
                "id": "configured-domestic-mirror",
                "kind": "domestic_mirror",
                "url": f"{custom}/{item['filename']}",
            }
        )
    result.extend(dict(source) for source in item["sources"])
    return result


def _fetch(url: str, destination: Path, *, timeout: int, max_bytes: int) -> None:
    request = Request(url, headers={"User-Agent": "ChatMaker-runtime/1"})
    with urlopen(request, timeout=timeout) as response, destination.open("xb") as output:
        total = 0
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > max_bytes:
                raise DownloadError("download_exceeds_pinned_size")
            output.write(block)


def download_locked(
    item: Mapping[str, Any],
    destination: Path,
    *,
    timeout: int = 300,
    fetcher: Callable[..., None] = _fetch,
) -> DownloadReceipt:
    """Try domestic mirrors first and accept bytes only after exact verification."""
    _validate_artifact(item)
    destination = Path(destination)
    if (
        destination.is_file()
        and destination.stat().st_size == item["size"]
        and sha256(destination) == item["sha256"]
    ):
        return DownloadReceipt(False, "local-cache", "verified_cache", "local", ())
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    attempted: list[str] = []
    errors: list[str] = []
    for source in _candidate_sources(item):
        attempted.append(source["id"])
        temporary.unlink(missing_ok=True)
        try:
            fetcher(
                source["url"],
                temporary,
                timeout=timeout,
                max_bytes=int(item["size"]),
            )
            if (
                not temporary.is_file()
                or temporary.stat().st_size != item["size"]
                or sha256(temporary) != item["sha256"]
            ):
                raise DownloadError("download_identity_mismatch")
            os.replace(temporary, destination)
            return DownloadReceipt(
                True,
                source["id"],
                source["kind"],
                urlsplit(source["url"]).netloc,
                tuple(attempted),
            )
        except Exception as exc:  # each source is independently disposable
            errors.append(f"{source['id']}:{type(exc).__name__}")
            temporary.unlink(missing_ok=True)
    raise DownloadError("all_pinned_sources_failed:" + ",".join(errors))


def legacy_artifact(item: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize an existing toolchain item for the shared downloader."""
    normalized = dict(item)
    if "sources" not in normalized:
        url = normalized.get("url")
        if not isinstance(url, str) or not url:
            raise DownloadError("runtime_artifact_invalid")
        normalized["sources"] = [
            {
                "id": str(normalized.get("source_id", "official-source")),
                "kind": str(normalized.get("source_kind", "official_fallback")),
                "url": url,
            }
        ]
    return normalized

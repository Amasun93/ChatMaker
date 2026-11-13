"""Hash-locked domestic-first downloads for optional ChatMaker runtimes."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from time import monotonic
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener

from chatmaker.progress import emit
from .locks import exclusive_file


SOURCE_REGISTRY = Path(__file__).with_name("runtime_sources.json")
DOWNLOAD_TIMEOUT = 25
SLOW_DOWNLOAD_WINDOW = 20
SLOW_DOWNLOAD_ETA = 300
FALLBACK_DOWNLOAD_TIMEOUT = 12
_unreachable_hosts: ContextVar[set[str] | None] = ContextVar('chatmaker_unreachable_download_hosts', default=None)


class DownloadError(RuntimeError):
    """A pinned download or its source policy could not be satisfied."""


class DownloadTooSlow(DownloadError):
    """A transfer is making progress, but another source is worth trying."""


@contextmanager
def download_session():
    """Remember connection failures while one request prepares its components."""
    if _unreachable_hosts.get() is not None:
        yield
        return
    token = _unreachable_hosts.set(set())
    try:
        yield
    finally:
        _unreachable_hosts.reset(token)


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
        or Path(item["filename"]).name != item["filename"]
        or '\\' in item["filename"] or ':' in item["filename"]
        or not isinstance(item.get("size"), int)
        or item["size"] <= 0
        or not isinstance(item.get("sha256"), str)
        or len(item["sha256"]) != 64
        or re.fullmatch(r'[0-9a-fA-F]{64}', item["sha256"]) is None
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
    sources = [dict(source) for source in item["sources"]]
    # A classroom or school network can explicitly refuse overseas fallbacks.
    # This prevents a long GitHub timeout after the domestic route was already
    # selected, while retaining the normal domestic-first + official-fallback
    # behavior for developers who did not opt into the stricter policy.
    if os.environ.get("CHATMAKER_DOWNLOAD_POLICY", "").strip().casefold() in {
        "domestic-only",
        "domestic_only",
    }:
        sources = [
            source
            for source in sources
            if source.get("kind") in {"domestic_mirror", "domestic_official", "verified_cache"}
        ]
        if not result and not sources:
            raise DownloadError("domestic_source_not_configured")
    result.extend(sources)
    unreachable = _unreachable_hosts.get()
    if unreachable:
        result.sort(key=lambda source: urlsplit(source['url']).netloc in unreachable)
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


class _PolicyRedirect(HTTPRedirectHandler):
    def __init__(self, allowed_hosts=None):
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != 'https' or parsed.username or parsed.password:
            raise DownloadError('download_redirect_not_https')
        if self.allowed_hosts is not None and parsed.hostname not in self.allowed_hosts:
            raise DownloadError('download_redirect_blocked_by_policy')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_url(request, *, timeout, allowed_hosts=None):
    return build_opener(_PolicyRedirect(allowed_hosts)).open(request, timeout=timeout)


def _write_json(path: Path, value) -> None:
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2), encoding='utf-8')
    temporary.replace(path)


def _fetch_resumable(item, source, temporary, *, timeout, allowed_hosts, allow_slow_switch=False):
    metadata_path = temporary.with_name(temporary.name + '.json')
    try:
        metadata = json.loads(metadata_path.read_text('utf-8'))
    except (OSError, ValueError):
        metadata = {}
    if not isinstance(metadata, dict) or metadata.get('sha256') != item['sha256'] or metadata.get('size') != item['size']:
        temporary.unlink(missing_ok=True)
        metadata = {}
    offset = temporary.stat().st_size if temporary.exists() else 0
    if offset >= item['size']:
        if offset == item['size'] and sha256(temporary) == item['sha256']:
            return
        temporary.unlink()
        offset = 0
    headers = {'User-Agent': 'ChatMaker-runtime/1', 'Accept-Encoding': 'identity'}
    if offset:
        headers['Range'] = f'bytes={offset}-'
        if metadata.get('source_url') == source['url'] and metadata.get('etag'):
            headers['If-Range'] = metadata['etag']
    received = 0
    with _open_url(Request(source['url'], headers=headers), timeout=timeout, allowed_hosts=allowed_hosts) as response:
        status = response.status
        if status == 206:
            expected = f"bytes {offset}-{item['size'] - 1}/{item['size']}"
            if response.headers.get('Content-Range') != expected:
                raise DownloadError('download_range_mismatch')
        elif status == 200:
            offset = 0  # If Range was ignored or If-Range changed, replace, don't append.
        else:
            raise DownloadError(f'download_http_status:{status}')
        length = response.headers.get('Content-Length')
        if length is not None and int(length) != item['size'] - offset:
            raise DownloadError('download_content_length_mismatch')
        _write_json(metadata_path, {'sha256': item['sha256'], 'size': item['size'],
                    'source_url': source['url'], 'etag': response.headers.get('ETag')})
        emit('download_start', component=item['filename'], source=source['id'],
             total_bytes=item['size'], resume_from=offset)
        started = monotonic()
        sampled_at = started
        sampled_bytes = 0
        last_event = started
        with temporary.open('ab' if offset else 'wb') as output:
            while True:
                block = response.read1(128 * 1024)
                if not block:
                    break
                received += len(block)
                if offset + received > item['size']:
                    raise DownloadError('download_exceeds_pinned_size')
                output.write(block)
                now = monotonic()
                remaining = item['size'] - offset - received
                if now - last_event >= 0.5 or not remaining:
                    speed = received / (now - started) if now > started else 0
                    emit('download_progress', component=item['filename'], source=source['id'],
                         downloaded=offset + received, total_bytes=item['size'], received_bytes=received,
                         percent=100 * (offset + received) / item['size'], speed_bps=speed,
                         eta_seconds=remaining / speed if speed else None)
                    last_event = now
                window = now - sampled_at
                if allow_slow_switch and window >= SLOW_DOWNLOAD_WINDOW:
                    rate = (received - sampled_bytes) / window
                    if remaining > rate * SLOW_DOWNLOAD_ETA:
                        raise DownloadTooSlow('download_too_slow')
                    sampled_at, sampled_bytes = now, received
        if offset + received != item['size']:
            raise DownloadError('download_interrupted')


def download_locked(
    item: Mapping[str, Any],
    destination: Path,
    *,
    timeout: int = DOWNLOAD_TIMEOUT,
    fetcher: Callable[..., None] | None = None,
    retry_slow_sources: bool = True,
) -> DownloadReceipt:
    """Resume one exact artifact; final bytes require size and SHA-256 verification."""
    _validate_artifact(item)
    destination = Path(destination)
    with exclusive_file(destination.with_name(destination.name + '.lock')):
        return _download_locked(item, destination, timeout=timeout, fetcher=fetcher,
                                retry_slow_sources=retry_slow_sources)


def _download_locked(item, destination, *, timeout, fetcher, retry_slow_sources):
    if (
        destination.is_file()
        and destination.stat().st_size == item["size"]
        and sha256(destination) == item["sha256"]
    ):
        emit('download_cached', component=item['filename'], source='local-cache', verified=True)
        return DownloadReceipt(False, "local-cache", "verified_cache", "local", ())
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    attempted: list[str] = []
    errors: list[str] = []
    deferred = False
    sources = _candidate_sources(item)
    unreachable = _unreachable_hosts.get()
    strict = os.environ.get('CHATMAKER_DOWNLOAD_POLICY', '').strip().casefold() in {'domestic-only', 'domestic_only'}
    allowed = {urlsplit(s['url']).hostname for s in sources} if strict else None
    if strict and 'registry.npmmirror.com' in allowed:
        allowed.update({'cdn.npmmirror.com', 'npmmirror.com'})
    if strict and any(urlsplit(s['url']).hostname == 'gitee.com' and '/releases/download/' in urlsplit(s['url']).path
                      for s in sources):
        allowed.add('foruda.gitee.com')
    # Try another endpoint before settling for a slow but functioning transfer.
    # Revisit a deferred source only after the other listed sources fail.
    pending = [(source, True) for source in sources]
    previous_reason = None
    for source, may_defer in pending:
        has_alternative = len(attempted) + 1 < len(pending)
        attempted.append(source["id"])
        if len(attempted) > 1:
            emit('download_switch_source', component=item['filename'], source=source['id'], previous=attempted[-2],
                 reason=previous_reason,
                 message=f"正在尝试备用下载源 {source['id']}")
        attempts = 1 if fetcher is not None else 3
        for attempt in range(attempts):
            try:
                if fetcher is not None:
                    temporary.unlink(missing_ok=True)
                    fetcher(source['url'], temporary, timeout=timeout, max_bytes=int(item['size']))
                else:
                    can_switch = has_alternative or not retry_slow_sources
                    _fetch_resumable(item, source, temporary,
                                     timeout=min(timeout, FALLBACK_DOWNLOAD_TIMEOUT) if can_switch else timeout,
                                     allowed_hosts=allowed,
                                     allow_slow_switch=may_defer and can_switch)
                emit('stage', component=item['filename'], stage='verify', message='校验下载文件')
                if (not temporary.is_file() or temporary.stat().st_size != item['size']
                        or sha256(temporary) != item['sha256']):
                    temporary.unlink(missing_ok=True)
                    raise DownloadError('download_identity_mismatch')
                os.replace(temporary, destination)
                if unreachable is not None:
                    unreachable.discard(urlsplit(source['url']).netloc)
                temporary.with_name(temporary.name + '.json').unlink(missing_ok=True)
                receipt = DownloadReceipt(True, source['id'], source['kind'], urlsplit(source['url']).netloc, tuple(attempted))
                _write_json(destination.with_name(destination.name + '.receipt.json'),
                            {**receipt.to_dict(), 'sha256': item['sha256'], 'size': item['size']})
                emit('download_done', component=item['filename'], source=source['id'], verified=True)
                return receipt
            except Exception as exc:
                previous_reason = str(exc) if isinstance(exc, DownloadError) else type(exc).__name__
                errors.append(f"{source['id']}:{type(exc).__name__}:{exc}")
                if fetcher is not None:
                    temporary.unlink(missing_ok=True)
                if isinstance(exc, DownloadTooSlow):
                    deferred = True
                    if retry_slow_sources:
                        pending.append((source, False))
                    break
                connection_failed = isinstance(exc, (URLError, TimeoutError)) and not isinstance(exc, HTTPError)
                if connection_failed and unreachable is not None:
                    unreachable.add(urlsplit(source['url']).netloc)
                if isinstance(exc, HTTPError) and exc.code in {401, 403, 404, 410}:
                    break
                if connection_failed and (has_alternative or not retry_slow_sources):
                    break
                if has_alternative and (previous_reason in {'download_identity_mismatch', 'download_content_length_mismatch'}
                                        or isinstance(exc, HTTPError) and exc.code in {429, 500, 502, 503, 504}):
                    break
                if attempt + 1 < attempts:
                    emit('download_retry', component=item['filename'], source=source['id'], attempt=attempt + 1,
                         error=type(exc).__name__)
    error = DownloadTooSlow if deferred and not retry_slow_sources else DownloadError
    raise error("all_pinned_sources_failed:" + ",".join(errors))


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

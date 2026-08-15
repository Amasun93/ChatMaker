"""Layered, provenance-preserving access to ChatMaker resources."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Protocol, Sequence


DEFAULT_USER_ROOT = Path.home() / ".chatmaker"
DEFAULT_BUILTIN_ROOT = (
    Path(__file__).resolve().parents[2] / "packs" / "llmwiki" / "builtin"
)


class ActiveResourceProvider(Protocol):
    def resource_snapshot(
        self, pack_id: str
    ) -> tuple[tuple[Path, str] | None, str]: ...

    def active_resource_root(self, pack_id: str) -> tuple[Path, str] | None: ...

    def generation_token(self) -> str: ...


@dataclass(frozen=True)
class ResolvedResource:
    """A resource path plus the provenance that made it authoritative."""

    path: Path
    provenance: dict[str, Any]
    generation: str
    expected_length: int | None = None
    expected_sha256: str | None = None

    def read_bytes(self) -> bytes:
        data = self.path.read_bytes()
        if self.expected_length is not None and len(data) != self.expected_length:
            raise RuntimeError("resource length does not match verified manifest")
        if self.expected_sha256 is not None:
            digest = hashlib.sha256(data).hexdigest()
            if digest != self.expected_sha256:
                raise RuntimeError("resource digest does not match verified manifest")
        return data

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.path.read_text(encoding=encoding)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": dict(self.provenance),
            "generation": self.generation,
        }


def _relative_resource(value: str | PurePosixPath) -> PurePosixPath:
    raw = str(value)
    if not raw or "\\" in raw:
        raise ValueError("resource path must be a non-empty POSIX relative path")
    path = PurePosixPath(raw)
    if path.is_absolute() or path.as_posix() != raw or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise ValueError("resource path must stay inside its resource layer")
    return path


def _safe_file(root: Path, *parts: str) -> Path | None:
    try:
        resolved_root = root.resolve(strict=False)
        candidate = root.joinpath(*parts)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(resolved_root)
        if not resolved.is_file():
            return None
        return resolved
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None


def _path_roots(
    *,
    override_paths: Sequence[Path | str] | None,
    environ: Mapping[str, str],
) -> list[Path]:
    if override_paths is not None:
        candidates = [Path(item).expanduser() for item in override_paths]
    else:
        raw = environ.get("CHATMAKER_PACKS_PATH", "")
        candidates = [Path(item).expanduser() for item in raw.split(os.pathsep) if item]
    roots: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate.resolve(strict=False)))
        if key not in seen:
            roots.append(candidate)
            seen.add(key)
    return roots


def resource_generation_token(user_root: Path | str = DEFAULT_USER_ROOT) -> str:
    """Return a token that changes whenever durable active-state bytes change."""

    active_path = Path(user_root).expanduser() / "state" / "active.json"
    try:
        raw = active_path.read_bytes()
    except FileNotFoundError:
        raw = b""
    except OSError as exc:
        raise RuntimeError("active generation state is unreadable") from exc
    generation = 0
    if raw:
        try:
            value = json.loads(raw.decode("utf-8"))
            candidate = value.get("generation") if isinstance(value, dict) else None
            if isinstance(candidate, int) and candidate >= 0:
                generation = candidate
        except (UnicodeDecodeError, json.JSONDecodeError):
            generation = 0
    return f"{generation}:{hashlib.sha256(raw).hexdigest()}"


class ResourceResolver:
    """Resolve overrides, verified official data, then built-in core data."""

    def __init__(
        self,
        *,
        user_root: Path | str = DEFAULT_USER_ROOT,
        builtin_root: Path | str = DEFAULT_BUILTIN_ROOT,
        manager: ActiveResourceProvider | None = None,
        override_paths: Sequence[Path | str] | None = None,
        environ: Mapping[str, str] | None = None,
        core_version: str = "0.1.0",
    ) -> None:
        self.user_root = Path(user_root).expanduser()
        self.builtin_root = Path(builtin_root)
        self.manager = manager
        self.core_version = core_version
        self._explicit_roots = _path_roots(
            override_paths=override_paths,
            environ=os.environ if environ is None else environ,
        )

    def generation_token(self) -> str:
        if self.manager is not None:
            return self.manager.generation_token()
        return resource_generation_token(self.user_root)

    def _override(self, relative: PurePosixPath, pack_id: str | None) -> ResolvedResource | None:
        roots = [*self._explicit_roots, self.user_root / "overrides"]
        for root in roots:
            layouts: list[tuple[str, ...]] = []
            if pack_id is not None:
                layouts.append((pack_id, *relative.parts))
            layouts.append(tuple(relative.parts))
            for parts in layouts:
                candidate = _safe_file(root, *parts)
                if candidate is not None:
                    return ResolvedResource(
                        path=candidate,
                        provenance={
                            "kind": "local_override",
                            "path": PurePosixPath(*parts).as_posix(),
                        },
                        generation=self.generation_token(),
                    )
        return None

    def resolve(
        self,
        relative_path: str | PurePosixPath,
        *,
        pack_id: str | None = None,
    ) -> ResolvedResource:
        relative = _relative_resource(relative_path)
        override = self._override(relative, pack_id)
        if override is not None:
            return override

        snapshot_generation: str | None = None
        if pack_id is not None and self.manager is not None:
            resource_record = getattr(self.manager, "resource_record", None)
            if callable(resource_record):
                record, snapshot_generation = resource_record(pack_id, relative.as_posix())
                if record is not None:
                    return ResolvedResource(
                        path=Path(record["path"]),
                        provenance={
                            "kind": "official_pack",
                            "pack_id": pack_id,
                            "version": record["version"],
                        },
                        generation=snapshot_generation,
                        expected_length=record["length"],
                        expected_sha256=record["sha256"],
                    )
            active, snapshot_generation = self.manager.resource_snapshot(pack_id)
            if active is not None:
                active_root, version = active
                candidate = _safe_file(active_root, *relative.parts)
                if candidate is not None:
                    return ResolvedResource(
                        path=candidate,
                        provenance={
                            "kind": "official_pack",
                            "pack_id": pack_id,
                            "version": version,
                        },
                        generation=snapshot_generation,
                    )

        builtin_layouts: list[tuple[str, ...]] = []
        if pack_id is not None:
            builtin_layouts.append((pack_id, *relative.parts))
        builtin_layouts.append(tuple(relative.parts))
        for parts in builtin_layouts:
            candidate = _safe_file(self.builtin_root, *parts)
            if candidate is not None:
                return ResolvedResource(
                    path=candidate,
                    provenance={
                        "kind": "builtin_core",
                        "core_version": self.core_version,
                    },
                    generation=snapshot_generation or self.generation_token(),
                )
        raise FileNotFoundError(relative.as_posix())


def resolve_resource(
    relative_path: str | PurePosixPath,
    *,
    pack_id: str | None = None,
    user_root: Path | str = DEFAULT_USER_ROOT,
    builtin_root: Path | str = DEFAULT_BUILTIN_ROOT,
    manager: ActiveResourceProvider | None = None,
    override_paths: Sequence[Path | str] | None = None,
    environ: Mapping[str, str] | None = None,
    core_version: str = "0.1.0",
) -> ResolvedResource:
    return ResourceResolver(
        user_root=user_root,
        builtin_root=builtin_root,
        manager=manager,
        override_paths=override_paths,
        environ=environ,
        core_version=core_version,
    ).resolve(relative_path, pack_id=pack_id)


__all__ = [
    "DEFAULT_BUILTIN_ROOT",
    "DEFAULT_USER_ROOT",
    "ResolvedResource",
    "ResourceResolver",
    "resolve_resource",
    "resource_generation_token",
]

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any


SKILL_NAMES = ("chatmaker", "chatduino", "chatweb")


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _activate_staging(staging: Path, target: Path) -> None:
    try:
        os.replace(staging, target)
    except PermissionError:
        if target.exists() or target.is_symlink():
            raise
        shutil.copytree(staging, target, symlinks=True)
        _remove_path(staging)


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=path.parent, prefix="chatmaker-", suffix=".tmp"
    ) as temporary:
        json.dump(value, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_name = temporary.name
    os.replace(temporary_name, path)


def install_bundle(
    host_home: Path,
    source_skills: Path,
    manifest_name: str,
) -> dict[str, Any]:
    host_home = Path(host_home).expanduser().resolve()
    source_skills = Path(source_skills).expanduser().resolve()
    skills_root = host_home / "skills"
    manifest = host_home / manifest_name
    if manifest.exists():
        raise FileExistsError(
            f"existing ChatMaker install manifest must be uninstalled first: {manifest}"
        )
    for name in SKILL_NAMES:
        source = source_skills / name
        if not (source / "SKILL.md").is_file():
            raise FileNotFoundError(f"missing source Skill: {source}")

    stamp = str(time.time_ns())
    backup_root = host_home / "chatmaker-backups" / stamp
    skills_root.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str | None]] = []
    pending: dict[str, Any] | None = None
    staging_paths: list[Path] = []
    try:
        for name in SKILL_NAMES:
            source = source_skills / name
            target = skills_root / name
            backup: Path | None = None
            if target.exists() or target.is_symlink():
                if not target.is_dir():
                    raise ValueError(f"Skill target is not a directory: {target}")
                backup = backup_root / name
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(target, backup, symlinks=True)

            pending = {"name": name, "target": target, "backup": backup}
            staging = skills_root / f".chatmaker-{name}-{stamp}.tmp"
            staging_paths.append(staging)
            shutil.copytree(source, staging, symlinks=True)
            _remove_path(target)
            _activate_staging(staging, target)
            entries.append(
                {"name": name, "target": str(target), "backup": str(backup) if backup else None}
            )
            pending = None
    except Exception:
        rollback = []
        if pending is not None:
            rollback.append(pending)
        rollback.extend(
            {
                "name": entry["name"],
                "target": Path(str(entry["target"])),
                "backup": Path(str(entry["backup"])) if entry["backup"] else None,
            }
            for entry in reversed(entries)
        )
        for entry in rollback:
            target = Path(entry["target"])
            _remove_path(target)
            backup = entry["backup"]
            if backup is not None and Path(backup).is_dir():
                shutil.copytree(Path(backup), target, symlinks=True)
        for staging in staging_paths:
            _remove_path(staging)
        raise

    _write_json_atomic(
        manifest,
        {"schema_version": "1.0", "installed_at": stamp, "entries": entries},
    )
    return {
        "success": True,
        "host_home": str(host_home),
        "manifest": str(manifest),
        "installed_skills": list(SKILL_NAMES),
        "backed_up_skills": [entry["name"] for entry in entries if entry["backup"]],
    }


def uninstall_bundle(host_home: Path, manifest_name: str) -> dict[str, Any]:
    host_home = Path(host_home).expanduser().resolve()
    skills_root = (host_home / "skills").resolve()
    manifest = host_home / manifest_name
    if not manifest.is_file():
        raise FileNotFoundError(f"install manifest not found: {manifest}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    restored: list[str] = []
    removed: list[str] = []
    for entry in data.get("entries", []):
        name = str(entry["name"])
        target = Path(entry["target"]).resolve()
        if target.parent != skills_root or target.name != name:
            raise ValueError(f"unsafe Skill target in manifest: {target}")
        _remove_path(target)
        backup_value = entry.get("backup")
        if backup_value:
            backup = Path(backup_value).resolve()
            if not backup.is_dir():
                raise FileNotFoundError(f"Skill backup not found: {backup}")
            shutil.copytree(backup, target, symlinks=True)
            restored.append(name)
        else:
            removed.append(name)
    manifest.unlink()
    return {"success": True, "restored_skills": restored, "removed_skills": removed}


def doctor_bundle(host_home: Path) -> dict[str, Any]:
    host_home = Path(host_home).expanduser().resolve()
    skills = {
        name: {
            "path": str(host_home / "skills" / name),
            "ready": (host_home / "skills" / name / "SKILL.md").is_file(),
        }
        for name in SKILL_NAMES
    }
    return {
        "success": all(item["ready"] for item in skills.values()),
        "host_home": str(host_home),
        "skills": skills,
    }

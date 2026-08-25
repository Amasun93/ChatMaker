"""Assemble the one-entry ChatMaker Skill bundle for an AI host.

This developer utility never discovers host directories. The caller supplies
an explicit output path, which keeps installation authority outside ChatMaker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPECIALISTS = ("chatduino", "chatweb", "chatcad")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_map(root: Path) -> dict[Path, Path]:
    skills = root.resolve() / "skills"
    mapping: dict[Path, Path] = {}
    sources = [(skills / "chatmaker", Path())]
    sources.extend((skills / name, Path("internal_skills") / name) for name in SPECIALISTS)
    for source, prefix in sources:
        if not source.is_dir() or source.is_symlink():
            raise ValueError(f"skill_source_missing_or_unsafe:{source}")
        for path in sorted(source.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"skill_source_symlink_rejected:{path}")
            if path.is_file():
                relative = prefix / path.relative_to(source)
                if relative in mapping:
                    raise ValueError(f"skill_bundle_path_collision:{relative.as_posix()}")
                mapping[relative] = path
    return mapping


def bundle_manifest(path: Path) -> dict[str, str]:
    return {
        file.relative_to(path).as_posix(): _sha256(file)
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def build_bundle(root: Path, output: Path) -> dict[str, Any]:
    mapping = source_map(root)
    destination = output.expanduser().resolve()
    source_roots = {path.parents[len(path.relative_to(root.resolve()).parts) - 1] for path in mapping.values()}
    if any(destination == source or destination.is_relative_to(source) for source in source_roots):
        raise ValueError("skill_bundle_output_overlaps_source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    backup = destination.with_name(f".{destination.name}.previous")
    try:
        for relative, source in mapping.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        required = [staging / "SKILL.md"] + [
            staging / "internal_skills" / name / "SKILL.md" for name in SPECIALISTS
        ]
        if not all(path.is_file() for path in required):
            raise ValueError("skill_bundle_incomplete")
        manifest = bundle_manifest(staging)
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            destination.replace(backup)
        staging.replace(destination)
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if not destination.exists() and backup.exists():
            backup.replace(destination)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return {
        "success": True,
        "output": str(destination),
        "file_count": len(manifest),
        "manifest": manifest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the single-entry ChatMaker Skill bundle.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build_bundle(args.root, args.output)
    except Exception as exc:
        result = {"success": False, "error": type(exc).__name__, "detail": str(exc)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

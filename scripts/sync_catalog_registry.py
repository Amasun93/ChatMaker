#!/usr/bin/env python3
"""Generate the runtime registry from canonical board and component records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


class CatalogRegistryError(RuntimeError):
    pass


def _mapping(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CatalogRegistryError(f"record_unreadable:{path.as_posix()}") from exc
    if not isinstance(value, dict):
        raise CatalogRegistryError(f"record_not_mapping:{path.as_posix()}")
    return value


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _knowledge_registration(root: Path, board_id: str) -> dict[str, str] | None:
    index_path = root / "knowledge" / "boards" / f"{board_id}.yaml"
    if not index_path.is_file():
        return None
    index = _mapping(index_path)
    if index.get("board_id") != board_id:
        raise CatalogRegistryError(f"knowledge_board_mismatch:{board_id}")
    sections = index.get("sections")
    if not isinstance(sections, list) or not sections:
        raise CatalogRegistryError(f"knowledge_sections_missing:{board_id}")
    pack_ids = {
        section.get("pack_id") for section in sections if isinstance(section, dict)
    }
    if len(pack_ids) != 1 or None in pack_ids:
        raise CatalogRegistryError(f"knowledge_pack_identity_ambiguous:{board_id}")
    manifest_path = root / "knowledge_sources" / "manifests" / f"{board_id}.yaml"
    manifest = _mapping(manifest_path)
    if manifest.get("board_id") != board_id or not isinstance(manifest.get("id"), str):
        raise CatalogRegistryError(f"knowledge_source_identity_invalid:{board_id}")
    return {
        "index_path": _relative(root, index_path),
        "pack_id": str(next(iter(pack_ids))),
        "source_ref": str(manifest["id"]),
    }


def build_registry(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    boards: dict[str, Any] = {}
    for path in sorted((root / "packs" / "boards").glob("*.yaml")):
        record = _mapping(path)
        board_id = record.get("id")
        if record.get("kind") != "board" or not isinstance(board_id, str):
            raise CatalogRegistryError(f"board_identity_invalid:{path.name}")
        if board_id in boards:
            raise CatalogRegistryError(f"duplicate_board:{board_id}")
        chatmaker = record.get("chatmaker")
        mechanics = record.get("mechanics")
        if not isinstance(chatmaker, dict) or not isinstance(mechanics, dict):
            raise CatalogRegistryError(f"board_registration_missing:{board_id}")
        profile_path = mechanics.get("profile_path")
        if profile_path is not None:
            profile = root / str(profile_path)
            if not profile.is_file():
                raise CatalogRegistryError(f"mechanical_profile_missing:{board_id}")
            try:
                profile_value = json.loads(profile.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise CatalogRegistryError(f"mechanical_profile_invalid:{board_id}") from exc
            if not isinstance(profile_value, dict) or profile_value.get("board_id") != board_id:
                raise CatalogRegistryError(f"mechanical_profile_board_mismatch:{board_id}")
        boards[board_id] = {
            "record_path": _relative(root, path),
            "runtime_cli": chatmaker.get("runtime_cli"),
            "runtime_module": chatmaker.get("runtime_module"),
            "identification": chatmaker.get("identification"),
            "mechanics": mechanics,
            "knowledge": _knowledge_registration(root, board_id),
        }

    components: dict[str, Any] = {}
    for path in sorted((root / "packs" / "components").glob("*.yaml")):
        record = _mapping(path)
        component_id = record.get("id")
        if record.get("kind") != "component" or not isinstance(component_id, str):
            raise CatalogRegistryError(f"component_identity_invalid:{path.name}")
        if component_id in components:
            raise CatalogRegistryError(f"duplicate_component:{component_id}")
        mechanical_path = root / "knowledge" / "mechanical" / "components" / f"{component_id}.json"
        components[component_id] = {
            "record_path": _relative(root, path),
            "mechanical_profile": (
                _relative(root, mechanical_path) if mechanical_path.is_file() else None
            ),
        }
    return {"schema_version": "1.0", "boards": boards, "components": components}


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = args.root / "runtime" / "chatmaker" / "catalog_registry.json"
    try:
        expected = canonical_bytes(build_registry(args.root))
        if args.check:
            if not output.is_file() or output.read_bytes() != expected:
                raise CatalogRegistryError("catalog_registry_out_of_date")
        else:
            output.write_bytes(expected)
    except (CatalogRegistryError, OSError) as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"success": True, "output": str(output), "checked": args.check}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

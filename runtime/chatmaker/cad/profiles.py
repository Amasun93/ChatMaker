from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def project_root() -> Path:
    configured = os.environ.get("CHATMAKER_PROJECT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def profile_root() -> Path:
    return project_root() / "knowledge" / "mechanical" / "boards"


def component_profile_root() -> Path:
    return project_root() / "knowledge" / "mechanical" / "components"


def component_profile_schema_path() -> Path:
    return project_root() / "knowledge" / "mechanical" / "schemas" / "component-profile.schema.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("kind") != "mechanical-profile":
        raise ValueError("invalid_mechanical_profile")
    outline = value.get("outline")
    mounting = value.get("mounting")
    if not isinstance(outline, dict) or not isinstance(mounting, dict):
        raise ValueError("invalid_mechanical_profile")
    for field in ("width", "depth"):
        number = outline.get(field)
        if not isinstance(number, (int, float)) or isinstance(number, bool) or number <= 0:
            raise ValueError("invalid_mechanical_profile")
    holes = mounting.get("holes")
    if not isinstance(holes, list):
        raise ValueError("invalid_mechanical_profile")
    for hole in holes:
        if not isinstance(hole, dict) or any(
            not isinstance(hole.get(key), (int, float)) or isinstance(hole.get(key), bool)
            for key in ("x", "y", "diameter")
        ):
            raise ValueError("invalid_mechanical_profile")
    return value


def list_profiles() -> dict[str, Any]:
    profiles = []
    for path in sorted(profile_root().glob("*.json")):
        value = _load(path)
        profiles.append(
            {
                "board_id": value["board_id"],
                "name": value["name"],
                "revision": value["revision"],
                "physical_fit": value["verification"]["physical_fit"],
            }
        )
    return {"success": True, "action": "list-profiles", "profiles": profiles}


def get_profile(board_id: str) -> dict[str, Any]:
    if not board_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in board_id):
        return {"success": False, "error": "invalid_board_id", "board_id": board_id}
    path = profile_root() / f"{board_id}.json"
    if not path.is_file():
        return {"success": False, "error": "mechanical_profile_not_found", "board_id": board_id}
    value = _load(path)
    return {"success": True, "action": "profile", "profile": value, "source_path": path.relative_to(project_root()).as_posix()}


def _component_id_is_safe(component_id: str) -> bool:
    return bool(component_id) and all(
        character in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in component_id
    )


def _component_path(component_id: str) -> Path | None:
    if not _component_id_is_safe(component_id):
        return None
    root = component_profile_root().resolve()
    candidate = (root / f"{component_id}.json").resolve()
    if candidate.parent != root:
        return None
    return candidate


def _load_component(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(component_profile_schema_path().read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.path),
    )
    if errors:
        raise ValueError(f"invalid_component_mechanical_profile: {errors[0].message}")
    if value["component_id"] != path.stem:
        raise ValueError("invalid_component_mechanical_profile: component_id does not match filename")
    mounting = value["mounting"]
    if mounting["status"] == "source_reviewed":
        if (
            not isinstance(mounting["pattern_x"], (int, float))
            or not isinstance(mounting["pattern_y"], (int, float))
            or len(mounting["holes"]) != 4
        ):
            raise ValueError(
                "invalid_component_mechanical_profile: reviewed mounting requires two pitches and four holes"
            )
    elif mounting["pattern_x"] is not None or mounting["pattern_y"] is not None or mounting["holes"]:
        raise ValueError(
            "invalid_component_mechanical_profile: unreviewed mounting must omit pitches and holes"
        )
    if value["default_mount_surface"] not in value["mount_surfaces"]:
        raise ValueError(
            "invalid_component_mechanical_profile: default mount surface is unsupported"
        )

    registry = json.loads(
        (project_root() / "knowledge" / "mechanical" / "source-registry.json").read_text(
            encoding="utf-8"
        )
    )
    sources = {
        item.get("id"): item
        for item in registry.get("sources", [])
        if isinstance(item, dict)
    }
    for source_id in value["source_ids"]:
        source = sources.get(source_id)
        digest = source.get("artifact_sha256", "") if source else ""
        if (
            source is None
            or not source.get("evidence_level")
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(
                f"invalid_component_mechanical_profile: unregistered source {source_id}"
            )

    def require_finite(item: Any) -> None:
        if isinstance(item, bool):
            return
        if isinstance(item, (int, float)) and not math.isfinite(float(item)):
            raise ValueError("invalid_component_mechanical_profile: non-finite number")
        if isinstance(item, dict):
            for child in item.values():
                require_finite(child)
        elif isinstance(item, list):
            for child in item:
                require_finite(child)

    require_finite(value)
    return value


def get_component_profile(component_id: str) -> dict[str, Any]:
    path = _component_path(component_id)
    if path is None:
        return {"success": False, "error": "invalid_component_id", "component_id": component_id}
    if not path.is_file():
        return {
            "success": False,
            "error": "component_mechanical_profile_not_found",
            "component_id": component_id,
        }
    try:
        value = _load_component(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "success": False,
            "error": "invalid_component_mechanical_profile",
            "component_id": component_id,
            "detail": str(exc),
        }
    return {
        "success": True,
        "action": "component-profile",
        "profile": value,
        "source_path": path.relative_to(project_root()).as_posix(),
    }


def list_component_profiles() -> dict[str, Any]:
    profiles: list[dict[str, Any]] = []
    root = component_profile_root()
    if not root.is_dir():
        return {"success": False, "error": "component_mechanical_profile_directory_missing"}
    for path in sorted(root.glob("*.json")):
        try:
            profiles.append(_load_component(path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {
                "success": False,
                "error": "invalid_component_mechanical_profile",
                "component_id": path.stem,
                "detail": str(exc),
            }
    return {
        "success": True,
        "action": "list-component-profiles",
        "count": len(profiles),
        "profiles": profiles,
    }


def validate_component_profiles() -> dict[str, Any]:
    root = component_profile_root()
    errors: list[str] = []
    count = 0
    if not component_profile_schema_path().is_file():
        errors.append("missing component mechanical profile schema")
    if not root.is_dir():
        errors.append("missing component mechanical profile directory")
    else:
        for path in sorted(root.glob("*.json")):
            count += 1
            safe_path = _component_path(path.stem)
            if safe_path is None or safe_path != path.resolve():
                errors.append(f"{path.name}: unsafe component profile path")
                continue
            try:
                _load_component(path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{path.name}: {exc}")
    return {"ok": not errors, "count": count, "errors": errors}

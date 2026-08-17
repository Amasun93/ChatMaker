from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def project_root() -> Path:
    configured = os.environ.get("CHATMAKER_PROJECT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def profile_root() -> Path:
    return project_root() / "knowledge" / "mechanical" / "boards"


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

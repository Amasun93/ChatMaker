from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .profiles import project_root


_STABLE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def fabrication_root() -> Path:
    return project_root() / "knowledge" / "fabrication"


def _valid_id(value: str) -> bool:
    return bool(_STABLE_ID.fullmatch(value))


def _load_card(kind: str, stable_id: str) -> tuple[dict[str, Any], Path]:
    if kind not in {"equipment", "materials"} or not _valid_id(stable_id):
        raise ValueError("invalid_fabrication_profile_id")
    path = fabrication_root() / kind / f"{stable_id}.json"
    if not path.is_file():
        raise FileNotFoundError(stable_id)
    value = json.loads(path.read_text(encoding="utf-8"))
    expected_kind = "fabrication-equipment-profile" if kind == "equipment" else "fabrication-material-profile"
    expected_id = "equipment_id" if kind == "equipment" else "material_id"
    if not isinstance(value, dict) or value.get("kind") != expected_kind or value.get(expected_id) != stable_id:
        raise ValueError("invalid_fabrication_profile")
    return value, path


def _validate_equipment(value: dict[str, Any]) -> None:
    layers = value.get("layer_rules")
    if not isinstance(layers, list) or len(layers) < 2:
        raise ValueError("invalid_fabrication_profile")
    process_ids: set[str] = set()
    colors: set[str] = set()
    for layer in layers:
        if not isinstance(layer, dict):
            raise ValueError("invalid_fabrication_profile")
        process_id = layer.get("process_id")
        color = layer.get("color_hex")
        if not isinstance(process_id, str) or not _valid_id(process_id):
            raise ValueError("invalid_fabrication_profile")
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-f]{6}", color):
            raise ValueError("invalid_fabrication_profile")
        if process_id in process_ids or color in colors:
            raise ValueError("invalid_fabrication_profile")
        process_ids.add(process_id)
        colors.add(color)
    order = value.get("process_order")
    if not isinstance(order, dict) or order.get("cut_layer_must_be_last") is not True:
        raise ValueError("invalid_fabrication_profile")
    if order.get("cut_process_id") not in process_ids:
        raise ValueError("invalid_fabrication_profile")


def _validate_material(value: dict[str, Any]) -> None:
    thickness = value.get("default_thickness_mm")
    if not isinstance(thickness, (int, float)) or isinstance(thickness, bool) or thickness <= 0:
        raise ValueError("invalid_fabrication_profile")
    parameters = value.get("machine_parameters")
    if not isinstance(parameters, dict) or parameters.get("status") != "calibration-required":
        raise ValueError("invalid_fabrication_profile")


def list_fabrication_profiles() -> dict[str, Any]:
    path = fabrication_root() / "index.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("invalid_fabrication_index")
    return {"success": True, "action": "list-fabrication-profiles", **value}


def get_fabrication_profile(
    equipment_id: str = "lasermaker-generic",
    material_id: str = "wood-sheet-3mm",
) -> dict[str, Any]:
    try:
        equipment, equipment_path = _load_card("equipment", equipment_id)
        material, material_path = _load_card("materials", material_id)
        _validate_equipment(equipment)
        _validate_material(material)
    except FileNotFoundError:
        return {
            "success": False,
            "error": "fabrication_profile_not_found",
            "equipment_id": equipment_id,
            "material_id": material_id,
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"success": False, "error": "invalid_fabrication_profile", "detail": str(exc)}
    return {
        "success": True,
        "action": "fabrication-profile",
        "equipment": equipment,
        "material": material,
        "source_paths": [
            equipment_path.relative_to(project_root()).as_posix(),
            material_path.relative_to(project_root()).as_posix(),
        ],
    }

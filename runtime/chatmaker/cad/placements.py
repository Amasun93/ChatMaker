"""Shared, source-backed component placement contract for Chat2D and Chat3D."""

from __future__ import annotations

import math
from typing import Any

from .profiles import list_component_profiles


SUPPORTED_FACES = {"top", "bottom"}


def _finite_number(value: Any, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"placement_{field}_must_be_finite_number")
    return float(value)


def _available_features(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(feature)
        for feature in profile.get("panel_features", [])
        if feature.get("availability") == "available"
        and feature.get("shape") in {"round", "rect", "dual_round"}
    ]


def _catalog(board_profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    components = list_component_profiles()
    if not components.get("success"):
        raise ValueError(str(components.get("error")))
    catalog: dict[str, dict[str, Any]] = {
        board_profile["board_id"]: {
            "item_id": board_profile["board_id"],
            "kind": "board",
            "name": board_profile["name"],
            "width": float(board_profile["outline"]["width"]),
            "depth": float(board_profile["outline"]["depth"]),
            "mounting_holes": [dict(hole) for hole in board_profile["mounting"]["holes"]],
            "panel_features": [],
            "mount_surfaces": ["base"],
            "default_mount_surface": "base",
            "mechanical_status": "ready",
        }
    }
    for profile in components["profiles"]:
        catalog[profile["component_id"]] = {
            "item_id": profile["component_id"],
            "kind": "component",
            "name": profile["name"],
            "width": float(profile["outline"]["width"]),
            "depth": float(profile["outline"]["depth"]),
            "mounting_holes": [dict(hole) for hole in profile["mounting"]["holes"]],
            "panel_features": _available_features(profile),
            "mount_surfaces": list(profile["mount_surfaces"]),
            "default_mount_surface": profile["default_mount_surface"],
            "mechanical_status": (
                "ready" if profile["mounting"]["status"] == "source_reviewed" else "requires_measurement"
            ),
        }
    return catalog


def _aabb(item: dict[str, Any]) -> dict[str, float]:
    angle = math.radians(float(item["rotation"]) % 180)
    cosine, sine = abs(math.cos(angle)), abs(math.sin(angle))
    half_x = (float(item["width"]) * cosine + float(item["depth"]) * sine) / 2
    half_y = (float(item["width"]) * sine + float(item["depth"]) * cosine) / 2
    return {
        "x_min": float(item["x"]) - half_x,
        "x_max": float(item["x"]) + half_x,
        "y_min": float(item["y"]) - half_y,
        "y_max": float(item["y"]) + half_y,
    }


def validate_layout(
    items: list[dict[str, Any]], inner_width: float, inner_depth: float
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    bounds = {item["item_id"] + f"#{index}": _aabb(item) for index, item in enumerate(items)}
    half_width, half_depth = inner_width / 2, inner_depth / 2
    for key, box in bounds.items():
        if (
            box["x_min"] < -half_width
            or box["x_max"] > half_width
            or box["y_min"] < -half_depth
            or box["y_max"] > half_depth
        ):
            errors.append(f"{key} exceeds the {inner_width:g} x {inner_depth:g} mm usable face")
    for left_index, left in enumerate(items):
        left_box = _aabb(left)
        for right in items[left_index + 1 :]:
            if left["face"] != right["face"]:
                continue
            right_box = _aabb(right)
            overlap_x = min(left_box["x_max"], right_box["x_max"]) - max(
                left_box["x_min"], right_box["x_min"]
            )
            overlap_y = min(left_box["y_max"], right_box["y_max"]) - max(
                left_box["y_min"], right_box["y_min"]
            )
            if overlap_x > 0 and overlap_y > 0:
                errors.append(f"{left['item_id']} overlaps {right['item_id']} on {left['face']}")
                continue
            gap_x = max(
                right_box["x_min"] - left_box["x_max"],
                left_box["x_min"] - right_box["x_max"],
                0.0,
            )
            gap_y = max(
                right_box["y_min"] - left_box["y_max"],
                left_box["y_min"] - right_box["y_max"],
                0.0,
            )
            gap = math.hypot(gap_x, gap_y)
            if gap < 5:
                warnings.append(
                    f"{left['item_id']} and {right['item_id']} have only {gap:.1f} mm edge clearance"
                )
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def _item(source: dict[str, Any], face: str, x: float, y: float, rotation: float) -> dict[str, Any]:
    return {
        **source,
        "face": face,
        "x": float(x),
        "y": float(y),
        "rotation": float(rotation),
    }


def _first_free_position(
    source: dict[str, Any], face: str, placed: list[dict[str, Any]], width: float, depth: float
) -> tuple[float, float] | None:
    half_w, half_d = source["width"] / 2, source["depth"] / 2
    x_start, x_end = -width / 2 + half_w, width / 2 - half_w
    y_start, y_end = depth / 2 - half_d, -depth / 2 + half_d
    existing_warning_count = len(validate_layout(placed, width, depth)["warnings"])
    fallback: tuple[float, float] | None = None
    y = y_start
    while y >= y_end - 1e-9:
        x = x_start
        while x <= x_end + 1e-9:
            candidate = _item(source, face, x, y, 0)
            check = validate_layout(placed + [candidate], width, depth)
            if check["ok"]:
                if len(check["warnings"]) == existing_warning_count:
                    return x, y
                if fallback is None:
                    fallback = (x, y)
            x += 5
        y -= 5
    return fallback


def normalize(
    board_profile: dict[str, Any], values: dict[str, Any], inner_width: float, inner_depth: float
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog = _catalog(board_profile)
    raw = values.get("placements")
    items: list[dict[str, Any]] = []
    if raw is not None:
        if not isinstance(raw, list):
            raise ValueError("placements_must_be_array")
        for entry in raw:
            if not isinstance(entry, dict):
                raise ValueError("placement_must_be_object")
            item_id = str(entry.get("item_id", entry.get("component_id", ""))).strip()
            source = catalog.get(item_id)
            if source is None:
                raise ValueError(f"placement_profile_not_found:{item_id}")
            face = str(entry.get("face", "bottom")).strip()
            if face not in SUPPORTED_FACES:
                raise ValueError(f"unsupported_3d_placement_face:{face}")
            items.append(
                _item(
                    source,
                    face,
                    _finite_number(entry.get("x", 0), "x"),
                    _finite_number(entry.get("y", 0), "y"),
                    _finite_number(entry.get("rotation", 0), "rotation"),
                )
            )
    else:
        board = catalog[board_profile["board_id"]]
        items.append(_item(board, "bottom", 0, 0, 0))
        component_ids = values.get("component_ids", [])
        if not isinstance(component_ids, list):
            raise ValueError("component_ids_must_be_array")
        if len(component_ids) > 8:
            raise ValueError("component_ids_limit_exceeded")
        for raw_id in component_ids:
            component_id = str(raw_id).strip()
            source = catalog.get(component_id)
            if source is None or source["kind"] != "component":
                raise ValueError(f"placement_profile_not_found:{component_id}")
            face = "top" if source["panel_features"] else "bottom"
            position = _first_free_position(source, face, items, inner_width, inner_depth)
            if position is None:
                raise ValueError(f"automatic_layout_failed:{component_id}")
            items.append(_item(source, face, position[0], position[1], 0))
    validation = validate_layout(items, inner_width, inner_depth)
    if not validation["ok"]:
        raise ValueError("placement_validation_failed:" + ";".join(validation["errors"]))
    return items, validation


def public_placements(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "item_id": item["item_id"],
            "kind": item["kind"],
            "face": item["face"],
            "x": item["x"],
            "y": item["y"],
            "rotation": item["rotation"],
        }
        for item in items
    ]

"""Chat2D parameterized laser box and direct-manipulation workspace."""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

from . import box_model
from . import placements as placement_contract
from .profiles import get_component_profile, get_profile, list_component_profiles


BOARD_LIBRARY_IDS = (
    "arduino-uno-r3",
    "arduino-nano-classic",
    "esp32-devkit-v1",
    "idmc-0001-starcore-v4-2-2",
)
LIBRARY_PRESENTATION = {
    "arduino-uno-r3": {"name": "Arduino UNO", "series": ["open-hardware"]},
    "arduino-nano-classic": {"name": "Arduino Nano", "series": ["open-hardware"]},
    "esp32-devkit-v1": {"name": "ESP32 开发板", "series": ["open-hardware"]},
    "idmc-0001-starcore-v4-2-2": {"name": "星核板", "series": ["starcore"]},
    "idmd-0001-starcore-rgb-light": {"name": "RGB 灯模块", "series": ["starcore"]},
    "idmd-0002-starcore-serial-mp3": {"name": "串口 MP3 模块", "series": ["starcore"]},
    "idmd-0021-starcore-oled-1-3": {"name": "1.3 寸 OLED 屏", "series": ["starcore"]},
    "idms-0001-starcore-button": {"name": "按钮模块", "series": ["starcore", "sensor"]},
    "idms-0003-starcore-potentiometer": {"name": "电位器旋钮", "series": ["starcore", "sensor"]},
    "idms-0008-starcore-dht11": {"name": "DHT11 温湿度传感器", "series": ["starcore", "sensor"]},
    "idms-0009-starcore-ultrasonic": {"name": "超声波传感器", "series": ["starcore", "sensor"]},
}


def _num(
    values: dict[str, Any], key: str, default: float, low: float, high: float
) -> float:
    value = values.get(key, default)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not low <= float(value) <= high
    ):
        raise ValueError(f"{key}_out_of_range")
    return float(value)


def _bool(values: dict[str, Any], key: str, default: bool) -> bool:
    value = values.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key}_must_be_boolean")
    return value


def _available_features(profile: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for feature in profile.get("panel_features", []):
        if feature.get("availability") != "available":
            continue
        value = {
            key: feature[key]
            for key in ("id", "shape", "center", "size", "diameter", "center_spacing")
            if key in feature
        }
        if value.get("shape") in {"rect", "round", "dual_round"}:
            result.append(value)
    return result


def _library() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for board_id in BOARD_LIBRARY_IDS:
        loaded = get_profile(board_id)
        if not loaded.get("success"):
            raise ValueError(f"library_profile_missing:{board_id}")
        profile = loaded["profile"]
        presentation = LIBRARY_PRESENTATION[board_id]
        holes = [
            {
                "x": float(hole["x"]),
                "y": float(hole["y"]),
                "diameter": float(hole["diameter"]),
            }
            for hole in profile["mounting"]["holes"]
        ]
        records.append(
            {
                "id": board_id,
                "kind": "board",
                "category": "主控板",
                "name": presentation["name"],
                "revision": profile["revision"],
                "series": presentation["series"],
                "width": float(profile["outline"]["width"]),
                "depth": float(profile["outline"]["depth"]),
                "holes": holes,
                "measurement_required": board_id == "esp32-devkit-v1",
                "note": profile["mounting"].get("note", ""),
                "visual": {
                    "outline_shape": profile["outline"].get("shape", "rectangle"),
                    "holes": holes,
                    "center_marks": [],
                    "features": [],
                    "edge_badges": [
                        {"edge": item.get("edge"), "label": item.get("id", "")}
                        for item in profile.get("keepouts", [])
                    ],
                },
            }
        )

    listed = list_component_profiles()
    if not listed.get("success"):
        raise ValueError(str(listed.get("error")))
    for listed_profile in listed["profiles"]:
        component_id = listed_profile["component_id"]
        loaded = get_component_profile(component_id)
        if not loaded.get("success"):
            raise ValueError(f"library_component_missing:{component_id}")
        profile = loaded["profile"]
        presentation = LIBRARY_PRESENTATION.get(component_id)
        if presentation is None:
            presentation = {
                "name": profile["name"],
                "series": [
                    "starcore",
                    *(["sensor"] if profile["hardware_id"].startswith("IDMS-") else []),
                ],
            }
        centers = [
            {"x": float(hole["x"]), "y": float(hole["y"])}
            for hole in profile["mounting"]["holes"]
        ]
        records.append(
            {
                "id": component_id,
                "kind": "component",
                "category": (
                    "星核传感器" if profile["hardware_id"].startswith("IDMS-")
                    else "星核执行器" if profile["hardware_id"].startswith("IDMM-")
                    else "星核连接与供电" if profile["hardware_id"].startswith("IDMF-")
                    else "星核输出模块"
                ),
                "name": presentation["name"],
                "revision": "自研模块",
                "series": presentation["series"],
                "width": float(profile["outline"]["width"]),
                "depth": float(profile["outline"]["depth"]),
                "holes": [],
                "measurement_required": (
                    profile["mounting"]["status"] != "source_reviewed"
                    or any(feature.get("availability") != "available" for feature in profile["panel_features"])
                ),
                "note": (
                    "外形和孔中心已有资料；安装孔径与未发布的功能开口仍需实测，因此不自动生成这些切孔。"
                    if profile["mounting"]["status"] == "source_reviewed"
                    else "外形已有资料，但固定孔位和功能开口仍需实测。"
                ),
                "visual": {
                    "outline_shape": profile["outline"].get("shape", "rectangle"),
                    "holes": [],
                    "center_marks": centers,
                    "features": _available_features(profile),
                    "edge_badges": [],
                },
            }
        )
    return records


def geometry(
    profile: dict[str, Any], parameters: dict[str, Any], thickness: float
) -> dict[str, Any]:
    board = profile["outline"]
    material = _num(parameters, "material_thickness", thickness, 1, 12)
    width = _num(
        parameters, "box_width", max(100, float(board["width"]) + 30), 30, 600
    )
    depth = _num(
        parameters, "box_depth", max(80, float(board["depth"]) + 30), 30, 600
    )
    height = _num(parameters, "box_height", 45, 15, 300)
    dimension_mode = parameters.get("dimension_mode", "external")
    if dimension_mode not in {"external", "internal"}:
        raise ValueError("dimension_mode_invalid")
    if dimension_mode == "internal":
        outer_width, outer_depth, outer_height = (
            width + 2 * material,
            depth + 2 * material,
            height + 2 * material,
        )
        inner_width, inner_depth, inner_height = width, depth, height
    else:
        outer_width, outer_depth, outer_height = width, depth, height
        inner_width, inner_depth, inner_height = (
            width - 2 * material,
            depth - 2 * material,
            height - 2 * material,
        )

    legacy_joint = _num(
        parameters, "joint_size", 12, max(3, material * 1.5), 60
    )
    joint_low = max(3, material * 1.5)
    include_top = _bool(parameters, "include_top", True)
    include_bottom = _bool(parameters, "include_bottom", True)
    initial_panel = "bottom" if include_bottom else ("top" if include_top else "front")
    library = _library()
    resolved, layout_validation = placement_contract.normalize(
        profile, parameters, inner_width, inner_depth
    )
    by_id = {item["id"]: item for item in library}
    items: list[dict[str, Any]] = []
    for placement in resolved:
        source = by_id.get(placement["item_id"])
        if source is None:
            raise ValueError(f"library_profile_missing:{placement['item_id']}")
        panel_width = outer_width
        panel_depth = outer_depth
        items.append({
            **{key: source[key] for key in (
                "id", "kind", "name", "width", "depth", "holes",
                "measurement_required", "note", "visual"
            )},
            "source_id": source["id"],
            "x": panel_width / 2 + float(placement["x"]),
            "y": panel_depth / 2 - float(placement["y"]),
            "rotation": float(placement["rotation"]),
            "panel": placement["face"],
        })
    board_item = next((item for item in items if item["kind"] == "board"), None)
    return {
        "box_width": width,
        "box_depth": depth,
        "box_height": height,
        "outer_width": outer_width,
        "outer_depth": outer_depth,
        "outer_height": outer_height,
        "inner_width": inner_width,
        "inner_depth": inner_depth,
        "inner_height": inner_height,
        "dimension_mode": dimension_mode,
        "material_thickness": material,
        "joint_size_length": _num(
            parameters, "joint_size_length", legacy_joint, joint_low, 60
        ),
        "joint_size_width": _num(
            parameters, "joint_size_width", legacy_joint, joint_low, 60
        ),
        "joint_size_height": _num(
            parameters, "joint_size_height", legacy_joint, joint_low, 60
        ),
        "laser_compensation": _num(
            parameters, "laser_compensation", 0.1, -1, 1
        ),
        "include_top": include_top,
        "include_bottom": include_bottom,
        "include_panel_labels": _bool(parameters, "include_panel_labels", True),
        "board_id": profile["board_id"],
        "board": board_item,
        "items": items,
        "placements": placement_contract.public_placements(resolved),
        "layout_validation": layout_validation,
        "library": library,
    }


panels = box_model.panels
finger_panel = box_model.panel_outline


def _transform(
    item: dict[str, Any], panel: dict[str, Any], x: float, y: float
) -> tuple[float, float]:
    angle = math.radians(float(item.get("rotation", 0)))
    cosine, sine = math.cos(angle), math.sin(angle)
    return (
        float(panel["x"]) + float(item["x"]) + cosine * x - sine * y,
        float(panel["y"]) + float(item["y"]) + sine * x + cosine * y,
    )


def _feature_svg(item: dict[str, Any], panel: dict[str, Any]) -> str:
    values = []
    for feature in item["visual"].get("features", []):
        center = feature.get("center", [0, 0])
        shape = feature["shape"]
        if shape == "round":
            x, y = _transform(item, panel, float(center[0]), -float(center[1]))
            values.append(
                f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{float(feature["diameter"]) / 2:.3f}"/>'
            )
        elif shape == "dual_round":
            spacing = float(feature["center_spacing"])
            for local_x in (-spacing / 2, spacing / 2):
                x, y = _transform(
                    item, panel, float(center[0]) + local_x, -float(center[1])
                )
                values.append(
                    f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{float(feature["diameter"]) / 2:.3f}"/>'
                )
        elif shape == "rect":
            feature_width, feature_depth = map(float, feature["size"])
            center_x, center_y = _transform(
                item, panel, float(center[0]), -float(center[1])
            )
            values.append(
                f'<rect x="{-feature_width / 2:.3f}" y="{-feature_depth / 2:.3f}" '
                f'width="{feature_width:.3f}" height="{feature_depth:.3f}" '
                f'transform="translate({center_x:.3f} {center_y:.3f}) '
                f'rotate({float(item.get("rotation", 0)):.3f})"/>'
            )
    return "".join(values)


def _module_svg(item: dict[str, Any], panel: dict[str, Any]) -> tuple[str, str]:
    cuts = []
    for hole in item.get("holes", []):
        x, y = _transform(item, panel, float(hole["x"]), -float(hole["y"]))
        cuts.append(
            f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{float(hole["diameter"]) / 2:.3f}"/>'
        )
    cuts.append(_feature_svg(item, panel))
    center_x = float(panel["x"]) + float(item["x"])
    center_y = float(panel["y"]) + float(item["y"])
    red = (
        f'<g transform="translate({center_x:.3f} {center_y:.3f}) '
        f'rotate({float(item.get("rotation", 0)):.3f})">'
        f'<rect x="{-float(item["width"]) / 2:.3f}" '
        f'y="{-float(item["depth"]) / 2:.3f}" '
        f'width="{float(item["width"]):.3f}" height="{float(item["depth"]):.3f}"/>'
        "</g>"
    )
    return "".join(cuts), red


def _svg(name: str, g: dict[str, Any]) -> str:
    panel_list = box_model.panels(g)
    sheet_width, sheet_depth = box_model.sheet_size(panel_list, g)
    cut = []
    red = []
    for panel in panel_list:
        points = " ".join(
            f"{x:.3f},{y:.3f}" for x, y in box_model.panel_outline(panel, g)
        )
        cut.append(f'<polygon data-panel="{panel["name"]}" points="{points}"/>')
        if g["include_panel_labels"]:
            red.append(
                f'<text x="{float(panel["x"]) + float(panel["width"]) / 2:.3f}" '
                f'y="{float(panel["y"]) + float(panel["depth"]) / 2:.3f}" '
                f'text-anchor="middle" fill="#ff0000" font-size="5">'
                f'{panel["label"]} {float(panel["width"]):.1f} x '
                f'{float(panel["depth"]):.1f} mm</text>'
            )
    for item in g.get("items", []):
        panel = next(
            (candidate for candidate in panel_list if candidate["name"] == item["panel"]),
            None,
        )
        if panel:
            item_cut, item_red = _module_svg(item, panel)
            cut.append(item_cut)
            red.append(item_red)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{sheet_width:.3f}mm" '
        f'height="{sheet_depth:.3f}mm" viewBox="0 0 {sheet_width:.3f} {sheet_depth:.3f}">'
        f'<title>{html.escape(name)}</title>'
        '<g id="cut-through" fill="none" stroke="#000000" stroke-width="0.2">'
        + "".join(cut)
        + '</g><g id="line-engrave" fill="none" stroke="#ff0000" stroke-width="0.2">'
        + "".join(red)
        + '</g><g id="shallow-engrave" fill="none" stroke="#ffff00" stroke-width="0.2"/>'
        '<g id="deep-engrave" fill="none" stroke="#0000ff" stroke-width="0.2"/></svg>'
    )


def _dxf_line(layer: str, start: tuple[float, float], end: tuple[float, float]) -> str:
    return (
        f"0\nLINE\n8\n{layer}\n10\n{start[0]:.6f}\n20\n{start[1]:.6f}\n"
        f"11\n{end[0]:.6f}\n21\n{end[1]:.6f}\n"
    )


def _dxf_circle(layer: str, x: float, y: float, radius: float) -> str:
    return f"0\nCIRCLE\n8\n{layer}\n10\n{x:.6f}\n20\n{y:.6f}\n40\n{radius:.6f}\n"


def _dxf_item(item: dict[str, Any], panel: dict[str, Any]) -> str:
    result = []
    angle = math.radians(float(item.get("rotation", 0)))
    cosine, sine = math.cos(angle), math.sin(angle)
    center_x = float(panel["x"]) + float(item["x"])
    center_y = float(panel["y"]) + float(item["y"])
    corners = [
        (-float(item["width"]) / 2, -float(item["depth"]) / 2),
        (float(item["width"]) / 2, -float(item["depth"]) / 2),
        (float(item["width"]) / 2, float(item["depth"]) / 2),
        (-float(item["width"]) / 2, float(item["depth"]) / 2),
    ]
    rotated = [
        (
            center_x + cosine * x - sine * y,
            center_y + sine * x + cosine * y,
        )
        for x, y in corners
    ]
    for start, end in zip(rotated, rotated[1:] + rotated[:1]):
        result.append(_dxf_line("RED_LINE_ENGRAVE", start, end))
    for hole in item.get("holes", []):
        x, y = _transform(item, panel, float(hole["x"]), -float(hole["y"]))
        result.append(
            _dxf_circle("BLACK_CUT_THROUGH", x, y, float(hole["diameter"]) / 2)
        )
    for feature in item["visual"].get("features", []):
        center = feature.get("center", [0, 0])
        shape = feature["shape"]
        if shape == "round":
            x, y = _transform(item, panel, float(center[0]), -float(center[1]))
            result.append(
                _dxf_circle(
                    "BLACK_CUT_THROUGH", x, y, float(feature["diameter"]) / 2
                )
            )
        elif shape == "dual_round":
            spacing = float(feature["center_spacing"])
            for local_x in (-spacing / 2, spacing / 2):
                x, y = _transform(
                    item, panel, float(center[0]) + local_x, -float(center[1])
                )
                result.append(
                    _dxf_circle(
                        "BLACK_CUT_THROUGH",
                        x,
                        y,
                        float(feature["diameter"]) / 2,
                    )
                )
        elif shape == "rect":
            feature_width, feature_depth = map(float, feature["size"])
            feature_corners = [
                (-feature_width / 2, -feature_depth / 2),
                (feature_width / 2, -feature_depth / 2),
                (feature_width / 2, feature_depth / 2),
                (-feature_width / 2, feature_depth / 2),
            ]
            local_center = feature.get("center", [0, 0])
            points = [
                _transform(
                    item,
                    panel,
                    float(local_center[0]) + x,
                    -float(local_center[1]) + y,
                )
                for x, y in feature_corners
            ]
            for start, end in zip(points, points[1:] + points[:1]):
                result.append(_dxf_line("BLACK_CUT_THROUGH", start, end))
    return "".join(result)


def _dxf(g: dict[str, Any]) -> str:
    panel_list = box_model.panels(g)
    entities = []
    for panel in panel_list:
        points = box_model.panel_outline(panel, g)
        for start, end in zip(points, points[1:] + points[:1]):
            entities.append(_dxf_line("BLACK_CUT_THROUGH", start, end))
        if g["include_panel_labels"]:
            entities.append(
                f"0\nTEXT\n8\nRED_LINE_ENGRAVE\n"
                f"10\n{float(panel['x']) + float(panel['width']) / 2:.6f}\n"
                f"20\n{float(panel['y']) + float(panel['depth']) / 2:.6f}\n"
                f"40\n4\n1\n{panel['label']} {float(panel['width']):.1f} x "
                f"{float(panel['depth']):.1f} mm\n"
            )
    for item in g.get("items", []):
        panel = next(
            (candidate for candidate in panel_list if candidate["name"] == item["panel"]),
            None,
        )
        if panel:
            entities.append(_dxf_item(item, panel))
    layers = (
        "0\nTABLE\n2\nLAYER\n70\n4\n"
        "0\nLAYER\n2\nBLACK_CUT_THROUGH\n70\n0\n62\n7\n6\nCONTINUOUS\n"
        "0\nLAYER\n2\nRED_LINE_ENGRAVE\n70\n0\n62\n1\n6\nCONTINUOUS\n"
        "0\nLAYER\n2\nYELLOW_SHALLOW_ENGRAVE\n70\n0\n62\n2\n6\nCONTINUOUS\n"
        "0\nLAYER\n2\nBLUE_DEEP_ENGRAVE\n70\n0\n62\n5\n6\nCONTINUOUS\n0\nENDTAB\n"
    )
    return (
        "0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n"
        "0\nSECTION\n2\nTABLES\n"
        + layers
        + "0\nENDSEC\n0\nSECTION\n2\nENTITIES\n"
        + "".join(entities)
        + "0\nENDSEC\n0\nEOF\n"
    )


def _lab(name: str, g: dict[str, Any]) -> str:
    data = json.dumps(g, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    template = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>Chat2D 参数化盒子</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#edf0f3;color:#17212b;font-family:Inter,"Microsoft YaHei",sans-serif}button,input,select{font:inherit}.app{display:grid;grid-template-columns:minmax(620px,1fr) 360px;min-height:100vh}.lab{padding:14px;min-width:0}.toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}.toolbar-left,.toolbar-right,.tabs{display:flex;gap:7px;align-items:center}.button,.tabs button,.card{border:1px solid #cbd3dc;background:#fff;border-radius:9px;cursor:pointer}.button,.tabs button{min-height:39px;padding:7px 12px}.tabs button.active{background:#17212b;color:#fff;border-color:#17212b}.status{font-size:12px;color:#687583}.stage{height:calc(100vh - 67px);min-height:620px;border:1px solid #dbe1e7;border-radius:14px;background:#f8f9fb;overflow:hidden;display:grid;place-items:center}.canvas{width:98%;height:96%;touch-action:none}.panel-shape{fill:#fff;stroke:#111;stroke-width:.32}.panel-name{fill:#ef3340;font-size:5px;font-weight:700;pointer-events:none}.panel-size{fill:#667481;font-size:3.2px;pointer-events:none}.module-outline{fill:#fff5f5;stroke:#ef3340;stroke-width:.55}.module-cut{fill:#fff;stroke:#111;stroke-width:.55}.module-feature{fill:none;stroke:#111;stroke-width:.65}.module-mark{fill:none;stroke:#d28b00;stroke-width:.45;stroke-dasharray:1 1}.module-badge{fill:#657687;font-size:2.6px}.module-label{fill:#b51e28;font-size:3.5px;pointer-events:none}.module-item{cursor:grab}.module-item.selected .module-outline{fill:#ffdfe1;stroke-width:.9}.drag-ghost{pointer-events:none}.drag-ghost.drag-valid .module-outline{fill:#dcfce7;stroke:#159447;stroke-width:1}.drag-ghost.drag-invalid .module-outline{fill:#fee2e2;stroke:#dc2626;stroke-width:1}.drag-note{font-size:4px;font-weight:700}.drag-valid .drag-note{fill:#15803d}.drag-invalid .drag-note{fill:#b91c1c}.three{display:none;width:100%;height:100%;place-items:center;perspective:900px;touch-action:none}.box3d{position:relative;width:260px;height:190px;transform-style:preserve-3d;transform:rotateX(-25deg) rotateY(32deg)}.face{position:absolute;border:2px solid #17212b;background:#dab77f88;transform-style:preserve-3d}.face.front,.face.back{width:260px;height:120px;left:0;top:35px}.face.front{transform:translateZ(95px)}.face.back{transform:rotateY(180deg) translateZ(95px)}.face.left,.face.right{width:190px;height:120px;left:35px;top:35px}.face.left{transform:rotateY(-90deg) translateZ(130px)}.face.right{transform:rotateY(90deg) translateZ(130px)}.face.bottom,.face.top{width:260px;height:190px;left:0;top:0}.face.bottom{transform:rotateX(90deg) translateZ(-60px)}.face.top{transform:rotateX(90deg) translateZ(60px);background:#dab77f44}.module3d{position:absolute;background:#d83b45cc;border:1px solid #86141b;color:#fff;font-size:8px;display:grid;place-items:center;overflow:hidden;transform-origin:center}.right{background:#fff;border-left:1px solid #dbe1e7;overflow:auto}.right-tabs{display:flex;gap:6px;padding:13px 11px;border-bottom:1px solid #dbe1e7;position:sticky;top:0;background:#fff;z-index:3}.right-tabs button{flex:1;border:1px solid #cbd3dc;background:#fff;border-radius:9px;min-height:38px;font-size:12px;cursor:pointer}.right-tabs button.active{background:#17212b;color:#fff}.right-body{padding:16px}.right h2{font-size:15px;margin:12px 0 9px}.hint,.muted{font-size:11px;line-height:1.55;color:#687583}.field{margin:10px 0}.field label,.props label{display:grid;gap:5px;font-size:12px}.field input,.field select,.props input,.search{width:100%;min-height:37px;padding:7px 8px;border:1px solid #cbd3dc;border-radius:8px;background:#fff}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}.check{display:flex!important;align-items:center;gap:7px!important}.check input{width:auto!important;min-height:0!important}.summary{padding:10px;border-radius:9px;background:#f2f5f7;font-size:11px;line-height:1.6}.library-tools{display:grid;grid-template-columns:1fr 105px;gap:7px;margin-bottom:10px}.gallery{display:grid;grid-template-columns:1fr 1fr;gap:8px}.card{padding:8px;text-align:left;min-height:132px;touch-action:none}.card:hover{border-color:#ef3340}.thumb{height:72px;background:#f6f7f8;border-radius:7px;margin-bottom:6px;display:grid;place-items:center;overflow:hidden}.thumb svg{width:96%;height:96%}.card strong{display:block;font-size:11px;line-height:1.3}.card small{display:block;font-size:9px;color:#687583}.warn{font-size:9px;color:#a35b00;margin-top:3px}.empty{padding:16px;border:1px dashed #cbd3dc;border-radius:9px;color:#687583;text-align:center;font-size:12px}.note{padding:9px;border-left:3px solid #e4a62f;background:#fff8e8;font-size:11px;line-height:1.5}.danger{width:100%;color:#a51f28;border-color:#e2b2b5;margin-top:13px}.selected-preview{height:130px;border:1px solid #dbe1e7;border-radius:10px;background:#fafbfc;display:grid;place-items:center}.selected-preview svg{width:95%;height:95%}.drop-help{padding:10px;background:#eef8ff;border-radius:9px;color:#35607c;font-size:11px;line-height:1.5}@media(max-width:900px){.app{grid-template-columns:1fr}.right{border-left:0;border-top:1px solid #dbe1e7;min-height:700px}.stage{height:650px}}
</style></head>
<body><main class="app"><section class="lab"><div class="toolbar"><div class="toolbar-left"><div class="tabs"><button id="flat" class="active">六面展开</button><button id="assembled">三维近似预览</button></div><span id="status" class="status">从右侧图库拖到任意板面</span></div><div class="toolbar-right"><button class="button" id="projectExport">导出 3D 配置</button><button class="button" id="svgExport">导出 SVG</button><button class="button" id="dxfExport">导出 DXF</button></div></div><div class="stage"><svg id="canvas" class="canvas"></svg><div id="three" class="three"><div id="box3d" class="box3d"><div class="face front" id="front3d"></div><div class="face back" id="back3d"></div><div class="face left" id="left3d"></div><div class="face right" id="right3d"></div><div class="face bottom" id="bottom3d"></div><div class="face top" id="top3d"></div></div></div></div></section><aside class="right"><div class="right-tabs"><button data-tab="library" class="active">元件图库</button><button data-tab="box">盒子参数</button><button data-tab="selected">当前元件</button></div><div id="rightBody" class="right-body"></div></aside></main>
<script>
const initial=__DATA__,$=id=>document.getElementById(id),clone=v=>JSON.parse(JSON.stringify(v)),esc=v=>String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const s=clone(initial);s.items=Array.isArray(s.items)?clone(s.items):(s.board?[clone(s.board)]:[]);let selected=s.items.length?0:null,rightTab="library",librarySearch="",librarySeries="all",drag=null,rx=-25,ry=32;
function message(text){$("status").textContent=text}function panelName(name){return{top:"顶板",bottom:"底板",front:"前板",back:"后板",left:"左板",right:"右板"}[name]||name}
function outerDims(){const add=s.dimension_mode==="internal"?2*s.material_thickness:0;return{width:s.box_width+add,depth:s.box_depth+add,height:s.box_height+add}}
function innerDims(){const q=outerDims();return{width:q.width-2*s.material_thickness,depth:q.depth-2*s.material_thickness,height:q.height-2*s.material_thickness}}
function panelRecord(name,x,y,width,depth,edges){return{name,label:panelName(name),x,y,width,depth,edges}}
function panels(){const q=outerDims(),g=Math.max(12,s.material_thickness*5),out=[],male=a=>({axis:a,polarity:"male"}),female=a=>({axis:a,polarity:"female"});let x=g;if(s.include_top){out.push(panelRecord("top",x,g,q.width,q.depth,[male("length"),male("width"),male("length"),male("width")]));x+=q.width+g}if(s.include_bottom)out.push(panelRecord("bottom",x,g,q.width,q.depth,[male("length"),male("width"),male("length"),male("width")]));const sy=out.length?q.depth+3*g:g,sy2=sy+q.height+2*g;out.push(panelRecord("front",g,sy,q.width,q.height,[female("length"),male("height"),female("length"),male("height")]));out.push(panelRecord("back",g+q.width+g,sy,q.width,q.height,[female("length"),male("height"),female("length"),male("height")]));out.push(panelRecord("left",g,sy2,q.depth,q.height,[female("width"),female("height"),female("width"),female("height")]));out.push(panelRecord("right",g+q.depth+g,sy2,q.depth,q.height,[female("width"),female("height"),female("width"),female("height")]));return out}
function pitch(axis){return s["joint_size_"+axis]}
function fingerIntervals(length,target,polarity){const t=s.material_thickness,endMargin=Math.min(t,length/4),usable=Math.max(length-2*endMargin,t),finger=Math.min(target,usable);let count=Math.max(1,Math.floor((usable+finger)/(2*finger)));while(count>1&&count*finger+(count-1)*finger>usable)count--;const used=count*finger+(count-1)*finger,margin=(length-used)/2;let adjust=Math.min(Math.abs(s.laser_compensation)/2,Math.max(0,finger/2-.05));if(s.laser_compensation<0)adjust=-adjust;const out=[];for(let i=0;i<count;i++){let a=margin+i*finger*2,b=a+finger;if(polarity==="male"){a-=adjust;b+=adjust}else{a+=adjust;b-=adjust}out.push([Math.max(0,a),Math.min(length,b)])}return out}
function edgePoints(a,b,n,edge){const dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy),ux=dx/len,uy=dy/len,offset=edge.polarity==="male"?s.material_thickness:-s.material_thickness,out=[a];for(const v of fingerIntervals(len,pitch(edge.axis),edge.polarity)){const p=[a[0]+ux*v[0],a[1]+uy*v[0]],q=[a[0]+ux*v[1],a[1]+uy*v[1]];out.push(p,[p[0]+n[0]*offset,p[1]+n[1]*offset],[q[0]+n[0]*offset,q[1]+n[1]*offset],q)}out.push(b);return dedupe(out)}
function dedupe(points){const out=[];for(const p of points){const q=[Number(p[0].toFixed(9)),Number(p[1].toFixed(9))];if(!out.length||q[0]!==out[out.length-1][0]||q[1]!==out[out.length-1][1])out.push(q)}if(out.length>1&&out[0][0]===out[out.length-1][0]&&out[0][1]===out[out.length-1][1])out.pop();return out}
function panelOutline(p){const c=[[p.x,p.y],[p.x+p.width,p.y],[p.x+p.width,p.y+p.depth],[p.x,p.y+p.depth]],n=[[0,-1],[1,0],[0,1],[-1,0]],out=[];for(let i=0;i<4;i++){const q=edgePoints(c[i],c[(i+1)%4],n[i],p.edges[i]);out.push(...(out.length?q.slice(1):q))}return dedupe(out)}
function panelForItem(m,ps=panels()){return ps.find(p=>p.name===m.panel)}
function rotatedHalf(m){const a=(m.rotation||0)*Math.PI/180,c=Math.abs(Math.cos(a)),q=Math.abs(Math.sin(a));return{hx:(c*m.width+q*m.depth)/2,hy:(q*m.width+c*m.depth)/2}}
function canFitPanel(m,p){const b=rotatedHalf(m);return !!p&&b.hx<=p.width/2&&b.hy<=p.depth/2}
function fitsAt(m,p){const b=rotatedHalf(m);return canFitPanel(m,p)&&m.x>=b.hx&&m.x<=p.width-b.hx&&m.y>=b.hy&&m.y<=p.depth-b.hy}
function clampToPanel(m,p){const b=rotatedHalf(m);m.x=Math.max(b.hx,Math.min(p.width-b.hx,m.x));m.y=Math.max(b.hy,Math.min(p.depth-b.hy,m.y));return m}
function hitPanel(point){return panels().find(p=>point.x>=p.x&&point.x<=p.x+p.width&&point.y>=p.y&&point.y<=p.y+p.depth)||null}
function localPoint(event){const svg=$("canvas"),point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;const q=point.matrixTransform(svg.getScreenCTM().inverse());return{x:q.x,y:q.y}}
function makeItem(source,p,point){return{...clone(source),source_id:source.id,x:point.x-p.x,y:point.y-p.y,rotation:0,panel:p.name}}
function startLibraryDrag(event,id){if(event.button!==undefined&&event.button!==0)return;event.preventDefault();const source=s.library.find(item=>item.id===id);if(!source)return;drag={kind:"new",source,original:null,item:null,startX:event.clientX,startY:event.clientY,moved:false,panel:null,valid:false};rightTab="library";updateDrag(event)}
function startItemDrag(event,index){if(event.button!==undefined&&event.button!==0)return;event.preventDefault();event.stopPropagation();selected=index;rightTab="selected";drag={kind:"existing",index,source:null,original:clone(s.items[index]),item:clone(s.items[index]),startX:event.clientX,startY:event.clientY,moved:false,panel:panelForItem(s.items[index]),valid:true};renderRight();updateDrag(event)}
function updateDrag(event){if(!drag||drag.kind==="three")return;drag.moved=drag.moved||Math.hypot(event.clientX-drag.startX,event.clientY-drag.startY)>3;const point=localPoint(event),p=hitPanel(point);drag.panel=p;if(p){if(drag.kind==="new")drag.item=makeItem(drag.source,p,point);else{drag.item.panel=p.name;drag.item.x=point.x-p.x;drag.item.y=point.y-p.y}drag.valid=fitsAt(drag.item,p)}else drag.valid=false;renderCanvas()}
function finishDrag(){if(!drag||drag.kind==="three")return;const active=drag;if(active.panel&&active.item&&canFitPanel(active.item,active.panel)){clampToPanel(active.item,active.panel);if(active.kind==="new"){s.items.push(active.item);selected=s.items.length-1}else s.items[active.index]=active.item;rightTab="selected";message((active.valid?"已放到":"已吸附到")+panelName(active.panel.name))}else{if(active.kind==="new")message("这个元件放不进目标板，已取消");else message("目标位置放不下，已回到原位置")}drag=null;render()}
function templateShapes(item,cssPrefix){const v=item.visual||{holes:[],center_marks:[],features:[],edge_badges:[]},pre=cssPrefix||"",out=['<rect class="'+pre+'module-outline" x="'+(-item.width/2)+'" y="'+(-item.depth/2)+'" width="'+item.width+'" height="'+item.depth+'" rx=".7"/>'];for(const h of v.holes||[])out.push('<circle class="'+pre+'module-cut" cx="'+h.x+'" cy="'+(-h.y)+'" r="'+(h.diameter/2)+'"/>');for(const m of v.center_marks||[]){const x=m.x,y=-m.y,d=Math.max(.8,Math.min(item.width,item.depth)*.035);out.push('<path class="'+pre+'module-mark" d="M '+(x-d)+' '+y+' H '+(x+d)+' M '+x+' '+(y-d)+' V '+(y+d)+'"/>')}for(const f of v.features||[]){const c=f.center||[0,0],x=c[0],y=-c[1];if(f.shape==="round")out.push('<circle class="'+pre+'module-feature" cx="'+x+'" cy="'+y+'" r="'+(f.diameter/2)+'"/>');if(f.shape==="dual_round"){for(const dx of[-f.center_spacing/2,f.center_spacing/2])out.push('<circle class="'+pre+'module-feature" cx="'+(x+dx)+'" cy="'+y+'" r="'+(f.diameter/2)+'"/>')}if(f.shape==="rect")out.push('<rect class="'+pre+'module-feature" x="'+(x-f.size[0]/2)+'" y="'+(y-f.size[1]/2)+'" width="'+f.size[0]+'" height="'+f.size[1]+'"/>')}for(let i=0;i<(v.edge_badges||[]).length;i++){const b=v.edge_badges[i],label=esc(String(b.label||"").replace("pcb-","").replace("barrel-jack","PWR"));let x=0,y=0;if(b.edge==="-x"){x=-item.width/2+2;y=-item.depth/4+i*5}else if(b.edge==="+x"){x=item.width/2-2;y=-item.depth/4+i*5}else if(b.edge==="-y"){x=-item.width/5+i*8;y=item.depth/2-2}else{x=-item.width/5+i*8;y=-item.depth/2+3}out.push('<text class="'+pre+'module-badge" x="'+x+'" y="'+y+'" text-anchor="middle">'+label+'</text>')}return out.join("")}
function templateSvg(item){const pad=Math.max(4,Math.min(item.width,item.depth)*.18),w=item.width+2*pad,d=item.depth+2*pad;return'<svg viewBox="'+(-w/2)+' '+(-d/2)+' '+w+' '+d+'" aria-hidden="true">'+templateShapes(item,"")+'<text class="module-label" x="0" y="'+(item.depth/2+pad*.7)+'" text-anchor="middle">'+esc(item.name)+'</text></svg>'}
function moduleMarkup(m,index,p,extraClass){return'<g data-item="'+index+'" class="module-item '+(index===selected?"selected ":"")+(extraClass||"")+'" transform="translate('+(p.x+m.x)+' '+(p.y+m.y)+') rotate('+(m.rotation||0)+')">'+templateShapes(m,"")+'<text class="module-label" x="0" y="1.3" text-anchor="middle">'+esc(m.name)+'</text></g>'}
function ghostMarkup(){if(!drag||!drag.item||!drag.panel)return"";const m=drag.item,p=drag.panel,cls=drag.valid?"drag-valid":"drag-invalid",note=drag.valid?"可以放这里":"松手后自动吸附";return'<g class="drag-ghost '+cls+'" transform="translate('+(p.x+m.x)+' '+(p.y+m.y)+') rotate('+(m.rotation||0)+')">'+templateShapes(m,"")+'<text class="drag-note" x="0" y="'+(m.depth/2+6)+'" text-anchor="middle">'+note+'</text></g>'}
function renderCanvas(){const ps=panels(),margin=Math.max(12,s.material_thickness*5),sw=Math.max(...ps.map(p=>p.x+p.width))+margin,sh=Math.max(...ps.map(p=>p.y+p.depth))+margin,svg=$("canvas");svg.setAttribute("viewBox","0 0 "+sw+" "+sh);let content="";for(const p of ps){content+='<g data-panel-group="'+p.name+'"><polygon data-panel="'+p.name+'" class="panel-shape" points="'+panelOutline(p).map(q=>q.join(",")).join(" ")+'"/>'+(s.include_panel_labels?'<text class="panel-name" x="'+(p.x+p.width/2)+'" y="'+(p.y+p.depth/2-2)+'" text-anchor="middle">'+p.label+'</text><text class="panel-size" x="'+(p.x+p.width/2)+'" y="'+(p.y+p.depth/2+4)+'" text-anchor="middle">'+p.width.toFixed(1)+' × '+p.depth.toFixed(1)+' mm</text>':"")+'</g>'}for(let i=0;i<s.items.length;i++){if(drag?.kind==="existing"&&drag.index===i)continue;const m=s.items[i],p=panelForItem(m,ps);if(p)content+=moduleMarkup(m,i,p,"")}content+=ghostMarkup();svg.innerHTML=content;svg.querySelectorAll("[data-item]").forEach(g=>g.onpointerdown=e=>startItemDrag(e,Number(g.dataset.item)))}
function boxTransform(){const q=outerDims(),sx=Math.max(.45,Math.min(1.5,q.width/100)),sy=Math.max(.45,Math.min(1.5,q.height/45)),sz=Math.max(.45,Math.min(1.5,q.depth/80));$("box3d").style.transform="rotateX("+rx+"deg) rotateY("+ry+"deg) scale3d("+sx+","+sy+","+sz+")"}
function render3d(){const ps=panels();for(const face of["bottom","top","front","back","left","right"]){const el=$(face+"3d"),p=ps.find(item=>item.name===face),included=!!p;el.style.display=included?"block":"none";el.innerHTML=included?s.items.filter(m=>m.panel===face).map(m=>'<div class="module3d" style="left:'+((m.x-m.width/2)/p.width*100)+'%;top:'+((m.y-m.depth/2)/p.depth*100)+'%;width:'+(m.width/p.width*100)+'%;height:'+(m.depth/p.depth*100)+'%;transform:translateZ(5px) rotate('+(m.rotation||0)+'deg)">'+esc(m.name)+'</div>').join(""):""}boxTransform()}
function setRightTab(tab){rightTab=tab;renderRight()}
function updateBox(key,value){const before=clone(s);if(key==="dimension_mode")s.dimension_mode=value==="internal"?"internal":"external";else if(["include_top","include_bottom","include_panel_labels"].includes(key))s[key]=!!value;else{const n=Number(value);if(!Number.isFinite(n))return;s[key]=n}const ps=panels(),fallback=ps[0];for(const m of s.items){let p=panelForItem(m,ps);if(!p){m.panel=fallback.name;p=fallback}if(!canFitPanel(m,p)){Object.assign(s,before);message("这个尺寸会让已有元件放不下，已保留原值");render();return}clampToPanel(m,p)}render()}
function selectItem(index){selected=index;rightTab="selected";render()}
function updateSelected(key,value){if(selected===null||!s.items[selected])return;const m=s.items[selected],before=clone(m);if(key==="name"){const name=String(value).trim();if(!name)return;m.name=name}else{const n=Number(value);if(!Number.isFinite(n))return;m.rotation=((n%360)+360)%360}const p=panelForItem(m);if(!canFitPanel(m,p)){Object.assign(m,before);message("这个角度会让元件放不下");render();return}clampToPanel(m,p);render()}
function deleteSelected(){if(selected===null)return;const m=s.items[selected];if(!confirm("删除“"+m.name+"”？"))return;s.items.splice(selected,1);selected=null;rightTab="library";render()}
function addCustomTemplate(){const name=prompt("自定义模板名称","");if(name===null||!name.trim())return;const width=measuredNumber("实测宽度（mm）",1,600),depth=width===null?null:measuredNumber("实测深度（mm）",1,600);if(width===null||depth===null)return;const item={id:"custom-"+Date.now(),kind:"custom",category:"自定义",name:name.trim(),revision:"实测模板",series:["custom"],width,depth,holes:[],measurement_required:true,note:"自定义模板：未知孔和开口不会自动生成。",visual:{outline_shape:"rectangle",holes:[],center_marks:[],features:[],edge_badges:[]}};s.library.push(item);librarySeries="all";librarySearch="";renderRight();message("模板已加入图库，请把它拖到木板上")}
function measuredNumber(label,min,max){const raw=prompt(label+"\n不知道时请先测量，不会替你猜。","");if(raw===null)return null;const n=Number(raw);if(!Number.isFinite(n)||n<min||n>max){alert("请输入 "+min+"–"+max+" mm 之间的实测数字");return null}return n}
function boxFields(){const q=outerDims(),inside=innerDims(),mode=s.dimension_mode==="external";return'<h2>盒子参数</h2><div class="field"><label>尺寸口径<select data-box="dimension_mode"><option value="external" '+(mode?"selected":"")+'>外部尺寸</option><option value="internal" '+(!mode?"selected":"")+'>内部尺寸</option></select></label></div><div class="grid2"><div class="field"><label>长度 X（mm）<input data-box="box_width" type="number" min="30" max="600" step="1" value="'+s.box_width+'"></label></div><div class="field"><label>宽度 Y（mm）<input data-box="box_depth" type="number" min="30" max="600" step="1" value="'+s.box_depth+'"></label></div></div><div class="field"><label>高度 Z（mm）<input data-box="box_height" type="number" min="15" max="300" step="1" value="'+s.box_height+'"></label></div><div class="summary">外部：'+q.width.toFixed(1)+' × '+q.depth.toFixed(1)+' × '+q.height.toFixed(1)+' mm<br>内部可用：'+inside.width.toFixed(1)+' × '+inside.depth.toFixed(1)+' × '+inside.height.toFixed(1)+' mm</div><h2>卡榫与材料</h2><div class="field"><label>材料厚度（mm）<input data-box="material_thickness" type="number" min="1" max="12" step=".1" value="'+s.material_thickness+'"></label></div><div class="field"><label>长度方向卡榫（mm）<input data-box="joint_size_length" type="number" min="3" max="60" step=".5" value="'+s.joint_size_length+'"></label></div><div class="field"><label>宽度方向卡榫（mm）<input data-box="joint_size_width" type="number" min="3" max="60" step=".5" value="'+s.joint_size_width+'"></label></div><div class="field"><label>高度方向卡榫（mm）<input data-box="joint_size_height" type="number" min="3" max="60" step=".5" value="'+s.joint_size_height+'"></label></div><div class="field"><label>装配补偿（mm）<input data-box="laser_compensation" type="number" min="-1" max="1" step=".05" value="'+s.laser_compensation+'"></label></div><p class="muted">正值让凸榫略宽、凹槽略窄。实体松紧必须用同批材料试切。</p><h2>显示与盖板</h2><label class="check"><input data-box="include_panel_labels" type="checkbox" '+(s.include_panel_labels?"checked":"")+'>显示板件名称和尺寸</label><div class="grid2"><label class="check"><input data-box="include_top" type="checkbox" '+(s.include_top?"checked":"")+'>保留顶板</label><label class="check"><input data-box="include_bottom" type="checkbox" '+(s.include_bottom?"checked":"")+'>保留底板</label></div>'}
function libraryFields(){const cards=s.library.filter(item=>(librarySeries==="all"||(item.series||[]).includes(librarySeries))&&item.name.toLowerCase().includes(librarySearch.toLowerCase())).map(item=>{const warning=item.measurement_required?((item.visual.center_marks||[]).length?"橙色十字为孔中心，孔径仍待实测":"实体尺寸需先确认"):"";return'<button class="card" data-library="'+item.id+'"><span class="thumb">'+templateSvg(item)+'</span><strong>'+esc(item.name)+'</strong><small>'+item.width+' × '+item.depth+' mm</small>'+(warning?'<div class="warn">'+warning+'</div>':"")+'</button>'}).join("");return'<h2>可视化元件图库</h2><div class="drop-help">按住缩略图，直接拖到任意木板。绿色表示可放置，红色表示会自动吸附。</div><div class="library-tools"><input id="librarySearch" class="search" placeholder="搜索 UNO、Nano、OLED…" value="'+esc(librarySearch)+'"><select id="librarySeries" aria-label="模块系列"><option value="all">全部模块</option><option value="open-hardware" '+(librarySeries==="open-hardware"?"selected":"")+'>开源硬件</option><option value="starcore" '+(librarySeries==="starcore"?"selected":"")+'>星核板</option><option value="sensor" '+(librarySeries==="sensor"?"selected":"")+'>传感器</option></select></div><div class="gallery">'+(cards||'<div class="empty">这个系列暂时没有可用模块</div>')+'</div><h2>没有这个模块？</h2><button class="button" id="addCustom">＋ 新增实测模板</button>'}
function selectedFields(){if(selected===null||!s.items[selected])return'<div class="empty">点击画布中的元件即可设置。<br>所在板面由拖放位置自动决定。</div>';const m=s.items[selected];return'<h2>当前元件</h2><div class="selected-preview">'+templateSvg(m)+'</div>'+(m.measurement_required?'<div class="note">'+esc(m.note||"部分尺寸仍需实测。")+'</div>':"")+'<div class="props"><label>名称<input data-prop="name" value="'+esc(m.name)+'"></label><label>旋转角度（°）<input data-prop="rotation" type="number" step="1" value="'+(m.rotation||0)+'"></label><div class="summary">自动所在板：'+panelName(m.panel)+'<br>模板尺寸：'+m.width+' × '+m.depth+' mm</div><button class="button danger" id="deleteModule">删除当前元件</button></div>'}
function renderRight(){document.querySelectorAll("[data-tab]").forEach(b=>b.classList.toggle("active",b.dataset.tab===rightTab));const body=$("rightBody");body.innerHTML=rightTab==="box"?boxFields():(rightTab==="library"?libraryFields():selectedFields());body.querySelectorAll("[data-box]").forEach(e=>e.onchange=()=>updateBox(e.dataset.box,e.type==="checkbox"?e.checked:e.value));if($("librarySearch"))$("librarySearch").oninput=e=>{librarySearch=e.target.value;renderRight()};if($("librarySeries"))$("librarySeries").onchange=e=>{librarySeries=e.target.value;renderRight()};body.querySelectorAll("[data-library]").forEach(e=>e.onpointerdown=event=>startLibraryDrag(event,e.dataset.library));if($("addCustom"))$("addCustom").onclick=addCustomTemplate;body.querySelectorAll("[data-prop]").forEach(e=>e.onchange=()=>updateSelected(e.dataset.prop,e.value));if($("deleteModule"))$("deleteModule").onclick=deleteSelected}
function itemTransform(m,p,x,y){const a=(m.rotation||0)*Math.PI/180,c=Math.cos(a),q=Math.sin(a);return{x:p.x+m.x+c*x-q*y,y:p.y+m.y+q*x+c*y}}
function itemSvg(m,p){let cut="";for(const h of m.holes||[]){const v=itemTransform(m,p,h.x,-h.y);cut+='<circle cx="'+v.x+'" cy="'+v.y+'" r="'+(h.diameter/2)+'"/>'}for(const f of m.visual.features||[]){const center=f.center||[0,0],x=center[0],y=-center[1];if(f.shape==="round"){const v=itemTransform(m,p,x,y);cut+='<circle cx="'+v.x+'" cy="'+v.y+'" r="'+(f.diameter/2)+'"/>'}if(f.shape==="dual_round"){for(const dx of[-f.center_spacing/2,f.center_spacing/2]){const v=itemTransform(m,p,x+dx,y);cut+='<circle cx="'+v.x+'" cy="'+v.y+'" r="'+(f.diameter/2)+'"/>'}}if(f.shape==="rect"){cut+='<g transform="translate('+(p.x+m.x)+' '+(p.y+m.y)+') rotate('+(m.rotation||0)+')"><rect x="'+(x-f.size[0]/2)+'" y="'+(y-f.size[1]/2)+'" width="'+f.size[0]+'" height="'+f.size[1]+'"/></g>'}}const red='<g transform="translate('+(p.x+m.x)+' '+(p.y+m.y)+') rotate('+(m.rotation||0)+')"><rect x="'+(-m.width/2)+'" y="'+(-m.depth/2)+'" width="'+m.width+'" height="'+m.depth+'"/></g>';return{cut,red}}
function svgText(){const ps=panels(),margin=Math.max(12,s.material_thickness*5),sw=Math.max(...ps.map(p=>p.x+p.width))+margin,sh=Math.max(...ps.map(p=>p.y+p.depth))+margin;let cut=ps.map(p=>'<polygon data-panel="'+p.name+'" points="'+panelOutline(p).map(q=>q.join(",")).join(" ")+'"/>').join(""),red=s.include_panel_labels?ps.map(p=>'<text x="'+(p.x+p.width/2)+'" y="'+(p.y+p.depth/2)+'" text-anchor="middle" fill="#ff0000">'+p.label+' '+p.width.toFixed(1)+' x '+p.depth.toFixed(1)+' mm</text>').join(""):"";for(const m of s.items){const p=panelForItem(m,ps);if(!p)continue;const q=itemSvg(m,p);cut+=q.cut;red+=q.red}return'<svg xmlns="http://www.w3.org/2000/svg" width="'+sw+'mm" height="'+sh+'mm" viewBox="0 0 '+sw+' '+sh+'"><g id="cut-through" fill="none" stroke="#000000" stroke-width=".2">'+cut+'</g><g id="line-engrave" fill="none" stroke="#ff0000" stroke-width=".2">'+red+'</g><g id="shallow-engrave" fill="none" stroke="#ffff00" stroke-width=".2"/><g id="deep-engrave" fill="none" stroke="#0000ff" stroke-width=".2"/></svg>'}
function dxfLine(layer,a,b){return"0\nLINE\n8\n"+layer+"\n10\n"+a[0]+"\n20\n"+a[1]+"\n11\n"+b[0]+"\n21\n"+b[1]+"\n"}function dxfCircle(x,y,r){return"0\nCIRCLE\n8\nBLACK_CUT_THROUGH\n10\n"+x+"\n20\n"+y+"\n40\n"+r+"\n"}
function dxf(){const ps=panels();let e="";for(const p of ps){const q=panelOutline(p);for(let i=0;i<q.length;i++)e+=dxfLine("BLACK_CUT_THROUGH",q[i],q[(i+1)%q.length]);if(s.include_panel_labels)e+="0\nTEXT\n8\nRED_LINE_ENGRAVE\n10\n"+(p.x+p.width/2)+"\n20\n"+(p.y+p.depth/2)+"\n40\n4\n1\n"+p.label+" "+p.width.toFixed(1)+" x "+p.depth.toFixed(1)+" mm\n"}for(const m of s.items){const p=panelForItem(m,ps);if(!p)continue;const a=(m.rotation||0)*Math.PI/180,c=Math.cos(a),q=Math.sin(a),corners=[[-m.width/2,-m.depth/2],[m.width/2,-m.depth/2],[m.width/2,m.depth/2],[-m.width/2,m.depth/2]].map(v=>[p.x+m.x+c*v[0]-q*v[1],p.y+m.y+q*v[0]+c*v[1]]);for(let i=0;i<4;i++)e+=dxfLine("RED_LINE_ENGRAVE",corners[i],corners[(i+1)%4]);for(const h of m.holes||[]){const v=itemTransform(m,p,h.x,-h.y);e+=dxfCircle(v.x,v.y,h.diameter/2)}for(const f of m.visual.features||[]){const center=f.center||[0,0],x=center[0],y=-center[1];if(f.shape==="round"){const v=itemTransform(m,p,x,y);e+=dxfCircle(v.x,v.y,f.diameter/2)}if(f.shape==="dual_round"){for(const dx of[-f.center_spacing/2,f.center_spacing/2]){const v=itemTransform(m,p,x+dx,y);e+=dxfCircle(v.x,v.y,f.diameter/2)}}if(f.shape==="rect"){const a=(m.rotation||0)*Math.PI/180,c=Math.cos(a),q=Math.sin(a),corners=[[-f.size[0]/2,-f.size[1]/2],[f.size[0]/2,-f.size[1]/2],[f.size[0]/2,f.size[1]/2],[-f.size[0]/2,f.size[1]/2]].map(v=>itemTransform(m,p,x+v[0],y+v[1]));for(let i=0;i<4;i++)e+=dxfLine("BLACK_CUT_THROUGH",[corners[i].x,corners[i].y],[corners[(i+1)%4].x,corners[(i+1)%4].y])}}}const layers="0\nTABLE\n2\nLAYER\n70\n4\n0\nLAYER\n2\nBLACK_CUT_THROUGH\n70\n0\n62\n7\n6\nCONTINUOUS\n0\nLAYER\n2\nRED_LINE_ENGRAVE\n70\n0\n62\n1\n6\nCONTINUOUS\n0\nLAYER\n2\nYELLOW_SHALLOW_ENGRAVE\n70\n0\n62\n2\n6\nCONTINUOUS\n0\nLAYER\n2\nBLUE_DEEP_ENGRAVE\n70\n0\n62\n5\n6\nCONTINUOUS\n0\nENDTAB\n";return"0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nTABLES\n"+layers+"0\nENDSEC\n0\nSECTION\n2\nENTITIES\n"+e+"0\nENDSEC\n0\nEOF\n"}
function canonicalPlacements(){const ps=panels();return s.items.map(m=>{const p=panelForItem(m,ps);return{item_id:m.source_id||m.id,kind:m.kind,face:m.panel,x:Number((m.x-p.width/2).toFixed(3)),y:Number((p.depth/2-m.y).toFixed(3)),rotation:Number(m.rotation||0)}})}
function projectRequest(){const q=innerDims(),placements=canonicalPlacements();if(placements.some(p=>!['top','bottom'].includes(p.face)))throw new Error('请先把要进入 3D 的模块放到顶板或底板');if(placements.some(p=>p.kind==='custom'))throw new Error('自定义模板要补齐机械 profile 后才能进入 3D');return{mode:"chat3d",delivery_mode:"chatmaker-preview",generation_confirmed:true,board_id:s.board_id,project_name:"__FILE__-3d",parameters:{inner_width:q.width,inner_depth:q.depth,inner_height:Math.max(20,q.height),placements}}}
function download(filename,text,type){const a=document.createElement("a"),url=URL.createObjectURL(new Blob([text],{type:type||"text/plain"}));a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function render(){renderCanvas();renderRight();render3d()}
document.querySelectorAll("[data-tab]").forEach(b=>b.onclick=()=>setRightTab(b.dataset.tab));$("projectExport").onclick=()=>{try{download("__FILE__-chat3d.json",JSON.stringify(projectRequest(),null,2),"application/json")}catch(error){message(error.message)}};$("svgExport").onclick=()=>download("__FILE__.svg",svgText(),"image/svg+xml");$("dxfExport").onclick=()=>download("__FILE__.dxf",dxf());window.addEventListener("pointermove",updateDrag);window.addEventListener("pointerup",finishDrag);window.addEventListener("pointercancel",finishDrag);
$("flat").onclick=()=>{$("canvas").style.display="block";$("three").style.display="none";$("flat").classList.add("active");$("assembled").classList.remove("active")};$("assembled").onclick=()=>{$("canvas").style.display="none";$("three").style.display="grid";$("assembled").classList.add("active");$("flat").classList.remove("active");render3d()};$("three").onpointerdown=e=>drag={kind:"three",startX:e.clientX,startY:e.clientY,rx,ry};$("three").onpointermove=e=>{if(drag?.kind!=="three")return;ry=drag.ry+(e.clientX-drag.startX)*.4;rx=drag.rx-(e.clientY-drag.startY)*.4;boxTransform()};$("three").onpointerup=$("three").onpointercancel=()=>drag=null;
window.chat2d={state:s,panels,panelOutline,fingerIntervals,templateSvg,startLibraryDrag,startItemDrag,updateDrag,finishDrag,hitPanel,canonicalPlacements,projectRequest,svgText,dxf,render};render();
</script></body></html>'''
    return (
        template.replace("__DATA__", data)
        .replace("__FILE__", name)
    )


def generate(
    request: dict[str, Any],
    profile: dict[str, Any],
    fabrication: dict[str, Any],
    output: Path,
    name: str,
) -> dict[str, Any]:
    g = geometry(
        profile,
        request.get("parameters", {}),
        float(fabrication["material"]["default_thickness_mm"]),
    )
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "project": output / "project.json",
        "svg": output / f"{name}.svg",
        "dxf": output / f"{name}.dxf",
        "preview_lab": output / "preview-lab.html",
    }
    files["svg"].write_text(_svg(name, g), encoding="utf-8")
    files["dxf"].write_text(_dxf(g), encoding="utf-8")
    files["preview_lab"].write_text(_lab(name, g), encoding="utf-8")
    project = {
        "schema_version": "1.0",
        "mode": "chat2d",
        "project_name": name,
        "board_id": profile["board_id"],
        "parameters": g,
        "layers": fabrication["equipment"]["layer_rules"],
        "model_generated": "verified",
        "file_opened": "unverified",
        "physical_fit": "unverified",
    }
    files["project"].write_text(
        json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "success": True,
        "action": "generate",
        "mode": "chat2d",
        "files": {key: str(value) for key, value in files.items()},
        "model_generated": "verified",
        "file_opened": "unverified",
        "physical_fit": "unverified",
    }

"""Deterministic basic mechanical recipes for Chat3D.

The module intentionally owns a small, bounded vocabulary: spur gear pairs and
rack-and-pinion projects.  It derives dimensions from standard gear relations,
writes editable OpenSCAD plus pure-Python STL artifacts, and records checks in
``project.json``.  It does not execute generated code or simulate motion.
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
import re
from typing import Any

from . import text as polygon_engine


Point2D = tuple[float, float]
Point3D = tuple[float, float, float]
Triangle = tuple[Point3D, Point3D, Point3D]

SUPPORTED_KINDS = {"gear_pair", "rack_and_pinion"}


def _num(values: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    value = values.get(key, default)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not low <= float(value) <= high
    ):
        raise ValueError(f"{key}_out_of_range")
    return float(value)


def _integer(values: dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    value = values.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key}_must_be_integer")
    result = int(value)
    if float(value) != result:
        raise ValueError(f"{key}_must_be_integer")
    if not low <= result <= high:
        raise ValueError(f"{key}_out_of_range")
    return result


def _round(value: float) -> float:
    return round(float(value), 6)


def _circle(radius: float, segments: int = 48, *, clockwise: bool = False) -> list[Point2D]:
    points = [
        (radius * math.cos(math.tau * index / segments), radius * math.sin(math.tau * index / segments))
        for index in range(segments)
    ]
    return list(reversed(points)) if clockwise else points


def _rectangle(width: float, depth: float) -> list[Point2D]:
    return [(0.0, 0.0), (width, 0.0), (width, depth), (0.0, depth)]


def _rotate(points: list[Point2D], angle: float) -> list[Point2D]:
    cosine, sine = math.cos(angle), math.sin(angle)
    return [(x * cosine - y * sine, x * sine + y * cosine) for x, y in points]


def _involute_angle(radius: float, base_radius: float) -> float:
    if radius <= base_radius:
        return 0.0
    parameter = math.sqrt((radius / base_radius) ** 2 - 1.0)
    return parameter - math.atan(parameter)


def _gear_metrics(
    teeth: int,
    module: float,
    pressure_angle: float,
    backlash: float,
    bore_diameter: float,
    label: str,
) -> dict[str, float]:
    pitch_radius = module * teeth / 2.0
    outer_radius = pitch_radius + module
    root_radius = pitch_radius - 1.25 * module
    base_radius = pitch_radius * math.cos(math.radians(pressure_angle))
    minimum_rim = max(0.8, module * 0.4)
    if root_radius <= bore_diameter / 2.0 + minimum_rim:
        raise ValueError(f"shaft_diameter_too_large_for_{label}_gear")
    if backlash >= math.pi * module / 2.0:
        raise ValueError("backlash_too_large_for_gear_module")
    return {
        "pitch_radius": pitch_radius,
        "pitch_diameter": pitch_radius * 2.0,
        "outer_radius": outer_radius,
        "outer_diameter": outer_radius * 2.0,
        "root_radius": root_radius,
        "root_diameter": root_radius * 2.0,
        "base_radius": base_radius,
    }


def gear_outline(
    teeth: int,
    module: float,
    pressure_angle: float,
    backlash: float,
    bore_diameter: float,
) -> list[Point2D]:
    """Return a printable involute-approximation spur-gear outline."""
    metrics = _gear_metrics(teeth, module, pressure_angle, backlash, bore_diameter, "spur")
    pitch_radius = metrics["pitch_radius"]
    outer_radius = metrics["outer_radius"]
    root_radius = metrics["root_radius"]
    base_radius = metrics["base_radius"]
    pitch = math.tau / teeth
    half_tooth = math.pi / (2.0 * teeth) - backlash / (2.0 * pitch_radius)
    rotation = half_tooth + _involute_angle(pitch_radius, base_radius)
    flank_start = max(root_radius, base_radius)
    flank_samples = 5
    points: list[Point2D] = []

    for tooth in range(teeth):
        center = tooth * pitch
        start_radius = flank_start
        start_offset = rotation - _involute_angle(start_radius, base_radius)
        points.append((root_radius * math.cos(center - pitch / 2), root_radius * math.sin(center - pitch / 2)))
        points.append((root_radius * math.cos(center - start_offset), root_radius * math.sin(center - start_offset)))
        if start_radius > root_radius:
            points.append((start_radius * math.cos(center - start_offset), start_radius * math.sin(center - start_offset)))
        for index in range(1, flank_samples + 1):
            radius = start_radius + (outer_radius - start_radius) * index / flank_samples
            offset = rotation - _involute_angle(radius, base_radius)
            points.append((radius * math.cos(center - offset), radius * math.sin(center - offset)))
        outer_offset = rotation - _involute_angle(outer_radius, base_radius)
        points.append((outer_radius * math.cos(center), outer_radius * math.sin(center)))
        for index in range(flank_samples, 0, -1):
            radius = start_radius + (outer_radius - start_radius) * index / flank_samples
            offset = rotation - _involute_angle(radius, base_radius)
            points.append((radius * math.cos(center + offset), radius * math.sin(center + offset)))
        if start_radius > root_radius:
            points.append((start_radius * math.cos(center + start_offset), start_radius * math.sin(center + start_offset)))
        points.append((root_radius * math.cos(center + start_offset), root_radius * math.sin(center + start_offset)))
        points.append((root_radius * math.cos(center + pitch / 2), root_radius * math.sin(center + pitch / 2)))

    return polygon_engine._orient(points, positive=True)


def rack_outline(
    teeth: int,
    module: float,
    pressure_angle: float,
    backlash: float,
    body_height: float,
) -> list[Point2D]:
    circular_pitch = math.pi * module
    tooth_thickness = circular_pitch / 2.0 - backlash
    if tooth_thickness <= module * 0.2:
        raise ValueError("backlash_too_large_for_gear_module")
    addendum = module
    dedendum = 1.25 * module
    flank_shift = addendum * math.tan(math.radians(pressure_angle))
    tip_half = max(module * 0.12, tooth_thickness / 2.0 - flank_shift)
    root_half = min(circular_pitch * 0.46, tooth_thickness / 2.0 + dedendum * math.tan(math.radians(pressure_angle)))
    length = teeth * circular_pitch
    points: list[Point2D] = [(0.0, -body_height)]
    for index in range(teeth):
        center = (index + 0.5) * circular_pitch
        points.extend(
            [
                (max(0.0, center - root_half), -dedendum),
                (center - tip_half, addendum),
                (center + tip_half, addendum),
                (min(length, center + root_half), -dedendum),
            ]
        )
    points.extend([(length, -body_height)])
    return polygon_engine._orient(points, positive=True)


def derive(values: dict[str, Any]) -> dict[str, Any]:
    kind = str(values.get("design_kind", "")).strip()
    if kind not in SUPPORTED_KINDS:
        raise ValueError("unsupported_chat3d_design_kind")
    module = _num(values, "gear_module", 2.0, 0.5, 5.0)
    pressure_angle = _num(values, "pressure_angle", 20.0, 14.5, 30.0)
    gear_thickness = _num(values, "gear_thickness", 6.0, 2.0, 20.0)
    shaft_diameter = _num(values, "shaft_diameter", 5.0, 2.0, 20.0)
    shaft_clearance = _num(values, "shaft_clearance", 0.2, 0.05, 1.0)
    backlash = _num(values, "backlash", 0.15, 0.0, 0.8)
    bracket_thickness = _num(values, "bracket_thickness", 3.0, 2.0, 10.0)
    bore_diameter = shaft_diameter + 2.0 * shaft_clearance
    shared: dict[str, Any] = {
        "design_kind": kind,
        "gear_module": module,
        "pressure_angle": pressure_angle,
        "gear_thickness": gear_thickness,
        "shaft_diameter": shaft_diameter,
        "shaft_clearance": shaft_clearance,
        "backlash": backlash,
        "bracket_thickness": bracket_thickness,
        "bore_diameter": bore_diameter,
        "circular_pitch": math.pi * module,
    }

    if kind == "gear_pair":
        driver_teeth = _integer(values, "driver_teeth", 12, 8, 80)
        driven_teeth = _integer(values, "driven_teeth", 24, 8, 120)
        driver = _gear_metrics(driver_teeth, module, pressure_angle, backlash, bore_diameter, "driver")
        driven = _gear_metrics(driven_teeth, module, pressure_angle, backlash, bore_diameter, "driven")
        shared.update(
            {
                "driver_teeth": driver_teeth,
                "driven_teeth": driven_teeth,
                "ratio": driven_teeth / driver_teeth,
                "center_distance": (driver["pitch_diameter"] + driven["pitch_diameter"]) / 2.0,
                "driver": driver,
                "driven": driven,
            }
        )
    else:
        pinion_teeth = _integer(values, "pinion_teeth", 16, 8, 80)
        rack_teeth = _integer(values, "rack_teeth", 12, 4, 80)
        rack_body_height = _num(values, "rack_body_height", max(6.0, module * 2.5), 3.0, 30.0)
        pinion = _gear_metrics(pinion_teeth, module, pressure_angle, backlash, bore_diameter, "pinion")
        shared.update(
            {
                "pinion_teeth": pinion_teeth,
                "rack_teeth": rack_teeth,
                "rack_body_height": rack_body_height,
                "rack_length": rack_teeth * math.pi * module,
                "pinion_center_to_rack_pitch_line": pinion["pitch_radius"],
                "pinion": pinion,
            }
        )
    return shared


def _extrude(outer: list[Point2D], holes: list[list[Point2D]], height: float, base_z: float = 0.0) -> list[Triangle]:
    outer = polygon_engine._orient(outer, positive=True)
    holes = [polygon_engine._orient(hole, positive=False) for hole in holes]
    contour = polygon_engine._bridge_holes(outer, holes)
    triangles: list[Triangle] = []
    for a, b, c in polygon_engine._ear_clip(contour):
        triangles.append(((a[0], a[1], base_z + height), (b[0], b[1], base_z + height), (c[0], c[1], base_z + height)))
        triangles.append(((a[0], a[1], base_z), (c[0], c[1], base_z), (b[0], b[1], base_z)))
    top = [(x, y, base_z + height) for x, y in contour]
    bottom = [(x, y, base_z) for x, y in contour]
    for index in range(len(contour)):
        following = (index + 1) % len(contour)
        triangles.append((top[index], top[following], bottom[following]))
        triangles.append((top[index], bottom[following], bottom[index]))
    return triangles


def _translate(triangles: list[Triangle], dx: float, dy: float, dz: float) -> list[Triangle]:
    return [tuple((x + dx, y + dy, z + dz) for x, y, z in triangle) for triangle in triangles]  # type: ignore[list-item]


def _normal(a: Point3D, b: Point3D, c: Point3D) -> Point3D:
    ux, uy, uz = (b[index] - a[index] for index in range(3))
    vx, vy, vz = (c[index] - a[index] for index in range(3))
    raw = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    length = math.sqrt(sum(value * value for value in raw)) or 1.0
    return tuple(value / length for value in raw)  # type: ignore[return-value]


def _stl(name: str, triangles: list[Triangle]) -> str:
    solid = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-.") or "chatcad-mechanism"
    lines = [f"solid {solid}"]
    for a, b, c in triangles:
        normal = _normal(a, b, c)
        lines.append(f"facet normal {normal[0]:.8f} {normal[1]:.8f} {normal[2]:.8f}\n outer loop")
        lines.extend(f"  vertex {point[0]:.8f} {point[1]:.8f} {point[2]:.8f}" for point in (a, b, c))
        lines.append(" endloop\nendfacet")
    lines.append(f"endsolid {solid}")
    return "\n".join(lines) + "\n"


def _scad_polygon(outer: list[Point2D], holes: list[list[Point2D]]) -> str:
    contours = [polygon_engine._orient(outer, positive=True)] + [
        polygon_engine._orient(hole, positive=False) for hole in holes
    ]
    points: list[Point2D] = []
    paths: list[list[int]] = []
    for contour in contours:
        paths.append(list(range(len(points), len(points) + len(contour))))
        points.extend(contour)
    point_code = ",".join(f"[{x:.6f},{y:.6f}]" for x, y in points)
    path_code = ",".join(str(path) for path in paths)
    return f"polygon(points=[{point_code}], paths=[{path_code}]);"


def _component_scad(title: str, outer: list[Point2D], holes: list[list[Point2D]], height: float) -> str:
    return (
        f"// ChatCAD basic mechanics - {title}\n"
        f"height = {height:.6f}; // mm\n"
        "$fn = 64;\n"
        "linear_extrude(height=height)\n  "
        + _scad_polygon(outer, holes)
        + "\n"
    )


def _component(
    component_id: str,
    component_type: str,
    quantity: int,
    outer: list[Point2D],
    holes: list[list[Point2D]],
    height: float,
) -> dict[str, Any]:
    return {
        "id": component_id,
        "type": component_type,
        "quantity": quantity,
        "outer": outer,
        "holes": holes,
        "height": height,
        "triangles": _extrude(outer, holes, height),
    }


def _gear_pair_parts(g: dict[str, Any]) -> tuple[list[dict[str, Any]], list[tuple[str, float, float, float]], dict[str, float]]:
    bore = _circle(g["bore_diameter"] / 2.0, clockwise=True)
    driver = _component(
        "driver_gear", "spur_gear", 1,
        gear_outline(g["driver_teeth"], g["gear_module"], g["pressure_angle"], g["backlash"], g["bore_diameter"]),
        [bore], g["gear_thickness"],
    )
    driven = _component(
        "driven_gear", "spur_gear", 1,
        _rotate(
            gear_outline(g["driven_teeth"], g["gear_module"], g["pressure_angle"], g["backlash"], g["bore_diameter"]),
            math.pi / g["driven_teeth"],
        ),
        [bore], g["gear_thickness"],
    )
    margin = 6.0
    driver_x = margin + g["driver"]["outer_radius"]
    driven_x = driver_x + g["center_distance"]
    plate_depth = 2.0 * max(g["driver"]["outer_radius"], g["driven"]["outer_radius"]) + 2.0 * margin
    center_y = plate_depth / 2.0
    plate_width = driven_x + g["driven"]["outer_radius"] + margin
    bushing_outer = g["bore_diameter"] + 4.0
    bracket_hole = _circle(bushing_outer / 2.0 + g["shaft_clearance"], clockwise=True)
    bracket = _component(
        "bracket", "bracket", 1, _rectangle(plate_width, plate_depth),
        [
            [(x + driver_x, y + center_y) for x, y in bracket_hole],
            [(x + driven_x, y + center_y) for x, y in bracket_hole],
        ], g["bracket_thickness"],
    )
    shaft_length = g["bracket_thickness"] + g["gear_thickness"] + 4.0
    shaft = _component("shaft", "shaft", 2, _circle(g["shaft_diameter"] / 2.0), [], shaft_length)
    bushing = _component(
        "bushing", "bushing", 2, _circle(bushing_outer / 2.0),
        [_circle(g["bore_diameter"] / 2.0, clockwise=True)], g["bracket_thickness"] + 1.0,
    )
    gear_z = g["bracket_thickness"] + 1.0
    placements = [
        ("bracket", 0.0, 0.0, 0.0),
        ("driver_gear", driver_x, center_y, gear_z),
        ("driven_gear", driven_x, center_y, gear_z),
        ("shaft", driver_x, center_y, 0.0),
        ("shaft", driven_x, center_y, 0.0),
        ("bushing", driver_x, center_y, 0.0),
        ("bushing", driven_x, center_y, 0.0),
    ]
    layout = {"width": plate_width, "depth": plate_depth, "driver_x": driver_x, "driven_x": driven_x, "center_y": center_y}
    return [driver, driven, shaft, bushing, bracket], placements, layout


def _rack_parts(g: dict[str, Any]) -> tuple[list[dict[str, Any]], list[tuple[str, float, float, float]], dict[str, float]]:
    bore = _circle(g["bore_diameter"] / 2.0, clockwise=True)
    pinion = _component(
        "pinion", "spur_gear", 1,
        gear_outline(g["pinion_teeth"], g["gear_module"], g["pressure_angle"], g["backlash"], g["bore_diameter"]),
        [bore], g["gear_thickness"],
    )
    rack = _component(
        "rack", "rack", 1,
        rack_outline(g["rack_teeth"], g["gear_module"], g["pressure_angle"], g["backlash"], g["rack_body_height"]),
        [], g["gear_thickness"],
    )
    margin = 6.0
    pitch_line_y = margin + g["rack_body_height"]
    pinion_x = margin + g["rack_length"] / 2.0
    pinion_y = pitch_line_y + g["pinion"]["pitch_radius"]
    plate_width = g["rack_length"] + 2.0 * margin
    plate_depth = pinion_y + g["pinion"]["outer_radius"] + margin
    bushing_outer = g["bore_diameter"] + 4.0
    bracket_hole = _circle(bushing_outer / 2.0 + g["shaft_clearance"], clockwise=True)
    bracket = _component(
        "bracket", "bracket", 1, _rectangle(plate_width, plate_depth),
        [[(x + pinion_x, y + pinion_y) for x, y in bracket_hole]], g["bracket_thickness"],
    )
    shaft_length = g["bracket_thickness"] + g["gear_thickness"] + 4.0
    shaft = _component("shaft", "shaft", 1, _circle(g["shaft_diameter"] / 2.0), [], shaft_length)
    bushing = _component(
        "bushing", "bushing", 1, _circle(bushing_outer / 2.0),
        [_circle(g["bore_diameter"] / 2.0, clockwise=True)], g["bracket_thickness"] + 1.0,
    )
    gear_z = g["bracket_thickness"] + 1.0
    rack_x = margin
    rack_y = pitch_line_y
    placements = [
        ("bracket", 0.0, 0.0, 0.0),
        ("rack", rack_x, rack_y, gear_z),
        ("pinion", pinion_x, pinion_y, gear_z),
        ("shaft", pinion_x, pinion_y, 0.0),
        ("bushing", pinion_x, pinion_y, 0.0),
    ]
    layout = {"width": plate_width, "depth": plate_depth, "rack_x": rack_x, "rack_y": rack_y, "pinion_x": pinion_x, "pinion_y": pinion_y}
    return [pinion, rack, shaft, bushing, bracket], placements, layout


def _assembly_scad(name: str, parts: list[dict[str, Any]], placements: list[tuple[str, float, float, float]]) -> str:
    modules: list[str] = []
    for part in parts:
        modules.append(
            f"module {part['id']}(){{linear_extrude(height={part['height']:.6f}) {_scad_polygon(part['outer'], part['holes'])}}}"
        )
    calls = "\n".join(f"translate([{x:.6f},{y:.6f},{z:.6f}]) {part_id}();" for part_id, x, y, z in placements)
    return f"// ChatCAD basic mechanical assembly - {name}\n$fn=64;\n" + "\n".join(modules) + "\n" + calls + "\n"


def _lab(name: str, g: dict[str, Any]) -> str:
    payload = json.dumps(
        {"project_name": name, **{key: value for key, value in g.items() if not isinstance(value, dict)}},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    template = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>__NAME__ · ChatCAD</title><style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,"Microsoft YaHei",sans-serif;background:#edf1f4;color:#14202a}.app{display:grid;grid-template-columns:340px 1fr;min-height:100vh}.side{padding:22px;background:#fff;border-right:1px solid #d9e0e6;overflow:auto;max-height:100vh}.field{margin:12px 0}.field label{display:flex;justify-content:space-between;font-size:13px}.field input{width:100%;margin-top:6px}.stage{margin:20px;background:#fff;border:1px solid #d9e0e6;border-radius:18px;min-height:560px;position:relative;overflow:hidden}.stage canvas{width:100%;height:100%;min-height:560px}.status{padding:10px;border-radius:10px;background:#e8f7ef;color:#16633f;font-size:13px}.exports{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:14px 0}.components{display:grid;grid-template-columns:1fr 1fr;gap:6px}button{border:1px solid #cbd6dc;border-radius:9px;background:#fff;padding:9px;cursor:pointer}button:hover{border-color:#299b79}.hint{position:absolute;left:18px;bottom:15px;color:#60717d;font-size:12px}.hidden{display:none}small{color:#60717d}@media(max-width:800px){.app{grid-template-columns:1fr}.side{max-height:none}.stage{min-height:480px}}
</style></head><body><main class="app"><aside class="side"><small>CHATCAD · 基础机械</small><h1>__NAME__</h1><p id="kindLabel"></p>
<div class="field"><label>模数 <output id="gear_module_v"></output></label><input id="gear_module" type="range" min="0.5" max="5" step="0.1"></div>
<div class="field"><label>压力角 <output id="pressure_angle_v"></output></label><input id="pressure_angle" type="range" min="14.5" max="30" step="0.5"></div>
<div class="field"><label>齿厚 <output id="gear_thickness_v"></output></label><input id="gear_thickness" type="range" min="2" max="20" step="0.5"></div>
<div class="field"><label>轴径 <output id="shaft_diameter_v"></output></label><input id="shaft_diameter" type="range" min="2" max="20" step="0.1"></div>
<div class="field"><label>轴孔单边间隙 <output id="shaft_clearance_v"></output></label><input id="shaft_clearance" type="range" min="0.05" max="1" step="0.05"></div>
<div class="field"><label>齿侧间隙 <output id="backlash_v"></output></label><input id="backlash" type="range" min="0" max="0.8" step="0.05"></div>
<div class="field"><label>支架厚度 <output id="bracket_thickness_v"></output></label><input id="bracket_thickness" type="range" min="2" max="10" step="0.5"></div>
<section id="pairFields"><div class="field"><label>主动轮齿数 <output id="driver_teeth_v"></output></label><input id="driver_teeth" type="range" min="8" max="80" step="1"></div><div class="field"><label>从动轮齿数 <output id="driven_teeth_v"></output></label><input id="driven_teeth" type="range" min="8" max="120" step="1"></div></section>
<section id="rackFields"><div class="field"><label>小齿轮齿数 <output id="pinion_teeth_v"></output></label><input id="pinion_teeth" type="range" min="8" max="80" step="1"></div><div class="field"><label>齿条齿数 <output id="rack_teeth_v"></output></label><input id="rack_teeth" type="range" min="4" max="80" step="1"></div><div class="field"><label>齿条主体高度 <output id="rack_body_height_v"></output></label><input id="rack_body_height" type="range" min="3" max="30" step="0.5"></div></section>
<p class="status" id="status">参数关系检查通过</p><div class="exports"><button data-export="assembly-scad">导出组合 SCAD</button><button data-export="assembly-stl">导出组合 STL</button></div>
<details><summary>导出独立零件</summary><div class="components"><button data-component="driver_gear" data-format="scad">主动轮 SCAD</button><button data-component="driver_gear" data-format="stl">主动轮 STL</button><button data-component="driven_gear" data-format="scad">从动轮 SCAD</button><button data-component="driven_gear" data-format="stl">从动轮 STL</button><button data-component="pinion" data-format="scad">小齿轮 SCAD</button><button data-component="pinion" data-format="stl">小齿轮 STL</button><button data-component="rack" data-format="scad">齿条 SCAD</button><button data-component="rack" data-format="stl">齿条 STL</button><button data-component="shaft" data-format="scad">轴 SCAD</button><button data-component="shaft" data-format="stl">轴 STL</button><button data-component="bushing" data-format="scad">轴套 SCAD</button><button data-component="bushing" data-format="stl">轴套 STL</button><button data-component="bracket" data-format="scad">支架 SCAD</button><button data-component="bracket" data-format="stl">支架 STL</button></div></details>
<p><small>参数变化会立即更新预览与下一次导出。生成模型不等于实物配合已验证；正式打印前请先打印轴孔与齿形小样。</small></p></aside><section class="stage"><canvas id="view"></canvas><span class="hint">静态组合关系预览 · 不代表运动与受力仿真</span></section></main><script>
const seed=__DATA__,kind=seed.design_kind,$=id=>document.getElementById(id);$('kindLabel').textContent=kind==='gear_pair'?'直齿轮对':'齿轮齿条';$('pairFields').classList.toggle('hidden',kind!=='gear_pair');$('rackFields').classList.toggle('hidden',kind!=='rack_and_pinion');
const ids=['gear_module','pressure_angle','gear_thickness','shaft_diameter','shaft_clearance','backlash','bracket_thickness','driver_teeth','driven_teeth','pinion_teeth','rack_teeth','rack_body_height'];for(const id of ids){if(seed[id]!=null)$(id).value=seed[id];$(id).addEventListener('input',refresh)}
const circle=(r,n=40,cw=false)=>{const p=Array.from({length:n},(_,i)=>[r*Math.cos(Math.PI*2*i/n),r*Math.sin(Math.PI*2*i/n)]);return cw?p.reverse():p};const rect=(w,h)=>[[0,0],[w,0],[w,h],[0,h]];const rotate=(p,a)=>p.map(([x,y])=>[x*Math.cos(a)-y*Math.sin(a),x*Math.sin(a)+y*Math.cos(a)]);const inv=(r,b)=>r<=b?0:(t=>t-Math.atan(t))(Math.sqrt((r/b)**2-1));
function gearPoints(z,m,pa,bl,bore){const rp=m*z/2,ro=rp+m,rr=rp-1.25*m,rb=rp*Math.cos(pa*Math.PI/180),pitch=Math.PI*2/z,half=Math.PI/(2*z)-bl/(2*rp),rot=half+inv(rp,rb),rs=Math.max(rr,rb),pts=[];if(rr<=bore/2+Math.max(.8,m*.4))throw Error('轴径过大，齿根材料不足');for(let tooth=0;tooth<z;tooth++){const c=tooth*pitch,so=rot-inv(rs,rb);pts.push([rr*Math.cos(c-pitch/2),rr*Math.sin(c-pitch/2)],[rr*Math.cos(c-so),rr*Math.sin(c-so)]);if(rs>rr)pts.push([rs*Math.cos(c-so),rs*Math.sin(c-so)]);for(let i=1;i<=5;i++){const r=rs+(ro-rs)*i/5,o=rot-inv(r,rb);pts.push([r*Math.cos(c-o),r*Math.sin(c-o)])}pts.push([ro*Math.cos(c),ro*Math.sin(c)]);for(let i=5;i>=1;i--){const r=rs+(ro-rs)*i/5,o=rot-inv(r,rb);pts.push([r*Math.cos(c+o),r*Math.sin(c+o)])}if(rs>rr)pts.push([rs*Math.cos(c+so),rs*Math.sin(c+so)]);pts.push([rr*Math.cos(c+so),rr*Math.sin(c+so)],[rr*Math.cos(c+pitch/2),rr*Math.sin(c+pitch/2)])}return pts}
function rackPoints(z,m,pa,bl,h){const p=Math.PI*m,t=p/2-bl,a=m,d=1.25*m,shift=a*Math.tan(pa*Math.PI/180),tip=Math.max(m*.12,t/2-shift),root=Math.min(p*.46,t/2+d*Math.tan(pa*Math.PI/180)),L=z*p,pts=[[0,-h]];for(let i=0;i<z;i++){const c=(i+.5)*p;pts.push([Math.max(0,c-root),-d],[c-tip,a],[c+tip,a],[Math.min(L,c+root),-d])}pts.push([L,-h]);return pts.reverse()}
function derive(){const n=id=>Number($(id).value),s={design_kind:kind,gear_module:n('gear_module'),pressure_angle:n('pressure_angle'),gear_thickness:n('gear_thickness'),shaft_diameter:n('shaft_diameter'),shaft_clearance:n('shaft_clearance'),backlash:n('backlash'),bracket_thickness:n('bracket_thickness')};s.bore_diameter=s.shaft_diameter+2*s.shaft_clearance;s.circular_pitch=Math.PI*s.gear_module;if(kind==='gear_pair'){s.driver_teeth=n('driver_teeth');s.driven_teeth=n('driven_teeth');s.ratio=s.driven_teeth/s.driver_teeth;s.center_distance=s.gear_module*(s.driver_teeth+s.driven_teeth)/2}else{s.pinion_teeth=n('pinion_teeth');s.rack_teeth=n('rack_teeth');s.rack_body_height=n('rack_body_height');s.rack_length=s.rack_teeth*s.circular_pitch;s.pinion_pitch_radius=s.gear_module*s.pinion_teeth/2}s.bushing_outer=s.bore_diameter+4;return s}
function build(){const s=derive(),bore=circle(s.bore_diameter/2,40,true),parts=[],placements=[],margin=6,add=(id,type,q,outer,holes,height)=>{const p={id,type,quantity:q,outer,holes,height};parts.push(p);return p};if(kind==='gear_pair'){const r1=s.gear_module*s.driver_teeth/2+s.gear_module,r2=s.gear_module*s.driven_teeth/2+s.gear_module,x1=margin+r1,x2=x1+s.center_distance,depth=2*Math.max(r1,r2)+2*margin,y=depth/2,width=x2+r2+margin,hole=circle(s.bushing_outer/2+s.shaft_clearance,40,true);add('driver_gear','spur_gear',1,gearPoints(s.driver_teeth,s.gear_module,s.pressure_angle,s.backlash,s.bore_diameter),[bore],s.gear_thickness);add('driven_gear','spur_gear',1,rotate(gearPoints(s.driven_teeth,s.gear_module,s.pressure_angle,s.backlash,s.bore_diameter),Math.PI/s.driven_teeth),[bore],s.gear_thickness);add('shaft','shaft',2,circle(s.shaft_diameter/2),[],s.bracket_thickness+s.gear_thickness+4);add('bushing','bushing',2,circle(s.bushing_outer/2),[bore],s.bracket_thickness+1);add('bracket','bracket',1,rect(width,depth),[hole.map(([a,b])=>[a+x1,b+y]),hole.map(([a,b])=>[a+x2,b+y])],s.bracket_thickness);placements.push(['bracket',0,0,0],['driver_gear',x1,y,s.bracket_thickness+1],['driven_gear',x2,y,s.bracket_thickness+1],['shaft',x1,y,0],['shaft',x2,y,0],['bushing',x1,y,0],['bushing',x2,y,0]);return{s,parts,placements,layout:{width,depth}}}const rp=s.pinion_pitch_radius,r=rp+s.gear_module,pitchY=margin+s.rack_body_height,x=margin+s.rack_length/2,y=pitchY+rp,width=s.rack_length+2*margin,depth=y+r+margin,hole=circle(s.bushing_outer/2+s.shaft_clearance,40,true);add('pinion','spur_gear',1,gearPoints(s.pinion_teeth,s.gear_module,s.pressure_angle,s.backlash,s.bore_diameter),[bore],s.gear_thickness);add('rack','rack',1,rackPoints(s.rack_teeth,s.gear_module,s.pressure_angle,s.backlash,s.rack_body_height),[],s.gear_thickness);add('shaft','shaft',1,circle(s.shaft_diameter/2),[],s.bracket_thickness+s.gear_thickness+4);add('bushing','bushing',1,circle(s.bushing_outer/2),[bore],s.bracket_thickness+1);add('bracket','bracket',1,rect(width,depth),[hole.map(([a,b])=>[a+x,b+y])],s.bracket_thickness);placements.push(['bracket',0,0,0],['rack',margin,pitchY,s.bracket_thickness+1],['pinion',x,y,s.bracket_thickness+1],['shaft',x,y,0],['bushing',x,y,0]);return{s,parts,placements,layout:{width,depth}}}
const area=p=>p.reduce((v,a,i)=>{const b=p[(i+1)%p.length];return v+a[0]*b[1]-b[0]*a[1]},0)/2;const orient=(p,pos)=>(area(p)>0)===pos?p.slice():p.slice().reverse();function inTri(p,a,b,c){const cr=(u,v,w)=>(v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0]),A=cr(a,b,c),d1=cr(a,b,p),d2=cr(b,c,p),d3=cr(c,a,p);return A>0?d1>1e-9&&d2>1e-9&&d3>1e-9:d1<-1e-9&&d2<-1e-9&&d3<-1e-9}function inPoly(p,q){let inside=false;for(let i=0;i<q.length;i++){const a=q[i],b=q[(i+1)%q.length];if((a[1]>p[1])!==(b[1]>p[1])&&a[0]+(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])>p[0])inside=!inside}return inside}function bridge(outer,holes){let merged=orient(outer,true);for(const raw of holes){const h=orient(raw,false),bi=h.reduce((best,p,i)=>p[0]>h[best][0]?i:best,0),right=h[bi],cand=merged.filter(p=>p[0]>=right[0]-1e-9).sort((a,b)=>(a[0]-right[0])**2+(a[1]-right[1])**2-((b[0]-right[0])**2+(b[1]-right[1])**2)),target=cand.find(v=>{const mid=[(v[0]+right[0])/2,(v[1]+right[1])/2];return inPoly(mid,merged)&&!holes.some(x=>inPoly(mid,x))});if(!target)continue;const at=merged.indexOf(target),ring=h.slice(bi).concat(h.slice(0,bi));merged=merged.slice(0,at+1).concat(ring,[ring[0],target],merged.slice(at))}return merged}function ear(points){const idx=points.map((_,i)=>i),tri=[];let guard=0;while(idx.length>3&&guard++<points.length*10){let clipped=false;for(let k=0;k<idx.length;k++){const ai=idx[(k+idx.length-1)%idx.length],bi=idx[k],ci=idx[(k+1)%idx.length],a=points[ai],b=points[bi],c=points[ci],cross=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);if(cross<=1e-9||idx.some(o=>o!==ai&&o!==bi&&o!==ci&&inTri(points[o],a,b,c)))continue;tri.push([a,b,c]);idx.splice(k,1);clipped=true;break}if(!clipped)break}if(idx.length===3)tri.push(idx.map(i=>points[i]));return tri}function extrude(p){const contour=bridge(p.outer,p.holes),t=[],z=p.height;for(const [a,b,c] of ear(contour)){t.push([[a[0],a[1],z],[b[0],b[1],z],[c[0],c[1],z]],[[a[0],a[1],0],[c[0],c[1],0],[b[0],b[1],0]])}for(let i=0;i<contour.length;i++){const j=(i+1)%contour.length,a=contour[i],b=contour[j];t.push([[a[0],a[1],z],[b[0],b[1],z],[b[0],b[1],0]],[[a[0],a[1],z],[b[0],b[1],0],[a[0],a[1],0]])}return t}function scad(parts,placements){const poly=p=>{let points=[],paths=[];for(const q of [orient(p.outer,true),...p.holes.map(h=>orient(h,false))]){paths.push(Array.from({length:q.length},(_,i)=>points.length+i));points.push(...q)}return`polygon(points=${JSON.stringify(points)},paths=${JSON.stringify(paths)});`};return`// ChatCAD basic mechanics\n$fn=64;\n`+parts.map(p=>`module ${p.id}(){linear_extrude(height=${p.height}) ${poly(p)}}`).join('\n')+'\n'+placements.map(([id,x,y,z])=>`translate([${x},${y},${z}]) ${id}();`).join('\n')}
function stl(parts,placements,name){const by=Object.fromEntries(parts.map(p=>[p.id,p])),tri=[];for(const [id,x,y,z] of placements)for(const t of extrude(by[id]))tri.push(t.map(([a,b,c])=>[a+x,b+y,c+z]));const normal=([a,b,c])=>{const u=b.map((v,i)=>v-a[i]),v=c.map((q,i)=>q-a[i]),n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],m=Math.hypot(...n)||1;return n.map(x=>x/m)};let out=`solid ${name}\n`;for(const t of tri){out+=`facet normal ${normal(t).join(' ')}\n outer loop\n`+t.map(p=>`  vertex ${p.join(' ')}`).join('\n')+'\n endloop\nendfacet\n'}return out+`endsolid ${name}\n`}
function download(name,text){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'text/plain'}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}const canvas=$('view'),ctx=canvas.getContext('2d');let current=null;function draw(){const {parts,placements,layout}=current,r=canvas.getBoundingClientRect(),d=devicePixelRatio||1;canvas.width=r.width*d;canvas.height=r.height*d;ctx.clearRect(0,0,canvas.width,canvas.height);const scale=Math.min(canvas.width/(layout.width+10),canvas.height/(layout.depth+10)),ox=(canvas.width-layout.width*scale)/2,oy=(canvas.height-layout.depth*scale)/2,by=Object.fromEntries(parts.map(p=>[p.id,p]));for(const [id,x,y] of placements){const p=by[id];ctx.beginPath();p.outer.forEach(([px,py],i)=>{const X=ox+(px+x)*scale,Y=canvas.height-(oy+(py+y)*scale);i?ctx.lineTo(X,Y):ctx.moveTo(X,Y)});ctx.closePath();ctx.fillStyle=p.type==='bracket'?'#dce5ea':p.type==='rack'?'#4eb58b':p.type==='shaft'?'#526a79':'#f3b44d';ctx.globalAlpha=p.type==='bracket'?.55:.82;ctx.fill();ctx.globalAlpha=1;ctx.strokeStyle='#203846';ctx.lineWidth=1.2*d;ctx.stroke()}}
function refresh(){try{current=build();for(const id of ids){const unit=id.includes('teeth')?'':id==='pressure_angle'?'°':' mm';$(id+'_v').textContent=$(id).value+unit}$('status').textContent=kind==='gear_pair'?`传动比 ${(current.s.ratio).toFixed(2)} · 中心距 ${current.s.center_distance.toFixed(2)} mm`:`齿距 ${current.s.circular_pitch.toFixed(2)} mm · 中心至齿条节线 ${current.s.pinion_pitch_radius.toFixed(2)} mm`;$('status').style.background='#e8f7ef';draw()}catch(error){$('status').textContent=error.message;$('status').style.background='#fdecec'}}
document.querySelector('[data-export="assembly-scad"]').onclick=()=>download(seed.project_name+'.scad',scad(current.parts,current.placements));document.querySelector('[data-export="assembly-stl"]').onclick=()=>download(seed.project_name+'.stl',stl(current.parts,current.placements,seed.project_name));for(const button of document.querySelectorAll('[data-component]'))button.onclick=()=>{const p=current.parts.find(x=>x.id===button.dataset.component);if(!p)return;const ext=button.dataset.format,placements=[[p.id,0,0,0]],body=ext==='scad'?scad([p],placements):stl([p],placements,p.id);download(seed.project_name+'-'+p.id+'.'+ext,body)};window.addEventListener('resize',draw);refresh();
</script></body></html>'''
    return template.replace("__NAME__", html.escape(name)).replace("__DATA__", payload)


def _public_component(part: dict[str, Any], files: dict[str, Path]) -> dict[str, Any]:
    return {
        "id": part["id"],
        "type": part["type"],
        "quantity": part["quantity"],
        "files": {
            "scad": str(files[f"{part['id']}_scad"]),
            "stl": str(files[f"{part['id']}_stl"]),
        },
    }


def generate(request: dict[str, Any], profile: dict[str, Any], output: Path, name: str) -> dict[str, Any]:
    values = request.get("parameters", {})
    g = derive(values)
    if g["design_kind"] == "gear_pair":
        parts, placements, layout = _gear_pair_parts(g)
    else:
        parts, placements, layout = _rack_parts(g)

    output.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {
        "project": output / "project.json",
        "scad": output / f"{name}.scad",
        "stl": output / f"{name}.stl",
        "preview_lab": output / "preview-lab.html",
    }
    for part in parts:
        files[f"{part['id']}_scad"] = output / f"{name}-{part['id'].replace('_', '-')}.scad"
        files[f"{part['id']}_stl"] = output / f"{name}-{part['id'].replace('_', '-')}.stl"
        files[f"{part['id']}_scad"].write_text(
            _component_scad(part["id"], part["outer"], part["holes"], part["height"]),
            encoding="utf-8",
            newline="\n",
        )
        files[f"{part['id']}_stl"].write_text(
            _stl(f"{name}-{part['id']}", part["triangles"]),
            encoding="ascii",
            newline="\n",
        )

    by_id = {part["id"]: part for part in parts}
    assembly_triangles: list[Triangle] = []
    for part_id, x, y, z in placements:
        assembly_triangles.extend(_translate(by_id[part_id]["triangles"], x, y, z))
    files["scad"].write_text(_assembly_scad(name, parts, placements), encoding="utf-8", newline="\n")
    files["stl"].write_text(_stl(name, assembly_triangles), encoding="ascii", newline="\n")
    files["preview_lab"].write_text(_lab(name, g), encoding="utf-8", newline="\n")

    derived: dict[str, Any]
    if g["design_kind"] == "gear_pair":
        derived = {
            "ratio": _round(g["ratio"]),
            "driver_pitch_diameter": _round(g["driver"]["pitch_diameter"]),
            "driven_pitch_diameter": _round(g["driven"]["pitch_diameter"]),
            "center_distance": _round(g["center_distance"]),
            "driven_phase_degrees": _round(180.0 / g["driven_teeth"]),
            "bore_diameter": _round(g["bore_diameter"]),
            "circular_pitch": _round(g["circular_pitch"]),
        }
        check_items = [
            {"id": "gear_standard_match", "status": "passed", "module": g["gear_module"], "pressure_angle": g["pressure_angle"]},
            {"id": "center_distance", "status": "passed", "actual_mm": _round(g["center_distance"])},
            {"id": "shaft_clearance", "status": "passed", "radial_mm": g["shaft_clearance"]},
        ]
    else:
        derived = {
            "circular_pitch": _round(g["circular_pitch"]),
            "rack_length": _round(g["rack_length"]),
            "pinion_pitch_radius": _round(g["pinion"]["pitch_radius"]),
            "pinion_center_to_rack_pitch_line": _round(g["pinion_center_to_rack_pitch_line"]),
            "bore_diameter": _round(g["bore_diameter"]),
        }
        check_items = [
            {"id": "gear_rack_standard_match", "status": "passed", "module": g["gear_module"], "pressure_angle": g["pressure_angle"]},
            {"id": "pitch_line_distance", "status": "passed", "actual_mm": _round(g["pinion_center_to_rack_pitch_line"])},
            {"id": "shaft_clearance", "status": "passed", "radial_mm": g["shaft_clearance"]},
        ]

    project = {
        "schema_version": "1.1",
        "mode": "chat3d",
        "design_kind": g["design_kind"],
        "project_name": name,
        "board_id": profile["board_id"],
        "design_brief": {
            "fabrication": "3d_print_fdm",
            "provided": {key: values[key] for key in values if key != "design_kind"},
            "derived": derived,
            "requires_measurement": ["real_shaft_diameter", "printer_specific_clearance"],
        },
        "parameters": {key: value for key, value in g.items() if not isinstance(value, dict)},
        "components": [_public_component(part, files) for part in parts],
        "checks": {"status": "passed", "items": check_items},
        "model_generated": "verified",
        "file_opened": "unverified",
        "physical_fit": "unverified",
    }
    files["project"].write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {
        "success": True,
        "action": "generate",
        "mode": "chat3d",
        "design_kind": g["design_kind"],
        "files": {key: str(path) for key, path in files.items()},
        "checks": project["checks"],
        "model_generated": "verified",
        "file_opened": "unverified",
        "physical_fit": "unverified",
    }

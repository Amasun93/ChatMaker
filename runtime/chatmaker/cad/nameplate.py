"""MakerLab-native OpenSCAD for standalone nameplates."""

from __future__ import annotations

from typing import Any

MAKERLAB_CJK_FONT = "Noto Sans SC:style=Regular"


def _num(values: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    value = values.get(key, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not low <= float(value) <= high:
        raise ValueError(f"{key}_out_of_range")
    return float(value)


def _format(value: float) -> str:
    return f"{value:g}"


def _scad_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _scad(name: str, values: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    label = str(values.get("engrave_text", "")).strip()
    if not label:
        raise ValueError("nameplate_text_required")

    length = _num(values, "tag_length", 60, 30, 200)
    width = _num(values, "tag_width", 20, 12, 80)
    thickness = _num(values, "plate_thickness", 2, 1, 10)
    radius = _num(values, "corner_radius", 3, 0, 20)
    hole_diameter = _num(values, "hole_diameter", 4, 0.8, 10)
    hole_margin_x = _num(values, "hole_margin_x", 7, 0, 50)
    hole_margin_y = _num(values, "hole_margin_y", 7, 0, 50)
    text_size = _num(values, "text_size", 8, 3, 60)
    text_raise = _num(values, "text_depth", 1, 0.4, 5)
    text_x = _num(values, "text_x", 0, -100, 100)
    text_y = _num(values, "text_y", 0, -100, 100)
    safe_name = name.replace("\r", " ").replace("\n", " ")
    code = f'''// ChatMaker Chat3D nameplate - {safe_name}
// 中文字体设置：点击代码区底部带 T 的放大镜图标（字体），搜索并勾选 {MAKERLAB_CJK_FONT}，确认后再生成。
/* [尺寸] */
tag_length = {_format(length)}; // 名牌长度 mm
tag_width = {_format(width)}; // 名牌宽度 mm
plate_thickness = {_format(thickness)}; // 底板厚度 mm
corner_radius = {_format(radius)}; // 圆角半径 mm

/* [文字] */
cn_text = {_scad_string(label)}; // 中文内容，可直接修改
text_font = {_scad_string(MAKERLAB_CJK_FONT)}; // 必须先在 MakerLab 字体面板勾选
text_size = {_format(text_size)}; // 字高 mm
text_raise = {_format(text_raise)}; // 文字凸起高度 mm
text_x = {_format(text_x)}; // 文字 X 偏移 mm
text_y = {_format(text_y)}; // 文字 Y 偏移 mm

/* [钥匙孔] */
hole_diameter = {_format(hole_diameter)}; // 孔径 mm
hole_margin_x = {_format(hole_margin_x)}; // 孔中心距左边缘 mm
hole_margin_y = {_format(hole_margin_y)}; // 孔中心距上边缘 mm

/* [高级] */
$fn = 96;
effective_corner_radius = max(0, min(corner_radius, tag_width/2-0.5, tag_length/2-0.5));
hole_x = -(tag_length/2-hole_margin_x);
hole_y = tag_width/2-hole_margin_y;

module rounded_plate_2d() {{
  offset(r=effective_corner_radius)
    square([
      max(0.1, tag_length-2*effective_corner_radius),
      max(0.1, tag_width-2*effective_corner_radius)
    ], center=true);
}}

module plate() {{
  difference() {{
    linear_extrude(height=plate_thickness) rounded_plate_2d();
    translate([hole_x, hole_y, -0.1])
      cylinder(h=plate_thickness+0.2, d=hole_diameter);
  }}
}}

union() {{
  plate();
  translate([text_x, text_y, plate_thickness-0.2])
    linear_extrude(height=text_raise+0.2)
      text(cn_text, size=text_size, font=text_font,
           halign="center", valign="center");
}}
'''
    return code, {
        "tag_length": length,
        "tag_width": width,
        "plate_thickness": thickness,
        "corner_radius": radius,
        "hole_diameter": hole_diameter,
        "hole_margin_x": hole_margin_x,
        "hole_margin_y": hole_margin_y,
        "text_size": text_size,
        "text_depth": text_raise,
        "text_x": text_x,
        "text_y": text_y,
        "engrave_text": label,
    }


def generate(request: dict[str, Any], name: str) -> dict[str, Any]:
    delivery_mode = str(request.get("delivery_mode", "makerlab-code")).strip()
    if delivery_mode != "makerlab-code":
        return {
            "success": False,
            "error": "nameplate_requires_makerlab_code",
            "stage": "planning",
            "beginner_message": "当前名牌的可靠中文路线是 MakerLab OpenSCAD 代码。",
        }
    code, parameters = _scad(name, request.get("parameters", {}))
    return {
        "success": True,
        "action": "generate",
        "mode": "chat3d",
        "design_kind": "nameplate",
        "delivery_mode": delivery_mode,
        "scad_code": code,
        "files": {},
        "parameters": parameters,
        "text_rendering": {
            "strategy": "makerlab-native-font",
            "makerlab_font": MAKERLAB_CJK_FONT,
            "makerlab_font_selection_required": True,
            "text_content_editable_in_makerlab": True,
        },
        "scad_generated": "verified",
        "model_generated": "unverified",
        "file_opened": "unverified",
        "physical_fit": "unverified",
    }

"""MakerLab-native OpenSCAD for standalone nameplates."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from . import text as text_engine

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


def _polygon_text(values: dict[str, Any], parameters: dict[str, Any]) -> tuple[list[str], list[list[list[list[float]]]]]:
    raw_font = values.get("engrave_font")
    font = (str(raw_font).strip() or None) if raw_font else None
    size = float(parameters["text_size"])
    layout = text_engine.glyph_layout(str(parameters["engrave_text"]), size, font)
    offset = (-layout["width"] / 2, -size / 2)
    statements = text_engine.scad_polygons_from_layout(layout, offset)
    glyphs = [
        [
            [[x + offset[0], y + offset[1]] for x, y in contour]
            for contour in glyph["contours"]
        ]
        for glyph in layout["glyphs"]
    ]
    return statements, glyphs


def _polygon_scad(name: str, parameters: dict[str, Any], statements: list[str]) -> str:
    safe_name = name.replace("\r", " ").replace("\n", " ")
    safe_label = str(parameters["engrave_text"]).replace("\r", " ").replace("\n", " ")
    polygon_lines = "\n".join(f"  {statement}" for statement in statements)
    return f'''// ChatMaker Chat3D offline nameplate - {safe_name}
// 固化文字：{safe_label}。改字请回 ChatCAD 重新生成；尺寸与位置可在仿真界面调整。
/* [尺寸] */
tag_length = {_format(parameters["tag_length"])};
tag_width = {_format(parameters["tag_width"])};
plate_thickness = {_format(parameters["plate_thickness"])};
corner_radius = {_format(parameters["corner_radius"])};

/* [文字几何] */
text_raise = {_format(parameters["text_depth"])};
text_scale = 1.0;
text_x = {_format(parameters["text_x"])};
text_y = {_format(parameters["text_y"])};

/* [钥匙孔] */
hole_diameter = {_format(parameters["hole_diameter"])};
hole_margin_x = {_format(parameters["hole_margin_x"])};
hole_margin_y = {_format(parameters["hole_margin_y"])};

/* [高级] */
$fn = 96;
effective_corner_radius = max(0, min(corner_radius, tag_width/2-0.5, tag_length/2-0.5));
hole_x = -(tag_length/2-hole_margin_x);
hole_y = tag_width/2-hole_margin_y;

module rounded_plate_2d() {{
  offset(r=effective_corner_radius)
    square([max(0.1,tag_length-2*effective_corner_radius),
            max(0.1,tag_width-2*effective_corner_radius)], center=true);
}}
module plate() {{
  difference() {{
    linear_extrude(height=plate_thickness) rounded_plate_2d();
    translate([hole_x,hole_y,-0.1]) cylinder(h=plate_thickness+0.2,d=hole_diameter);
  }}
}}
module label_glyphs() {{
{polygon_lines}
}}
union() {{
  plate();
  translate([text_x,text_y,plate_thickness-0.2])
    linear_extrude(height=text_raise+0.2) scale(text_scale) label_glyphs();
}}
'''


def _preview_lab(name: str, parameters: dict[str, Any], glyphs: list[list[list[list[float]]]], statements: list[str]) -> str:
    payload = dict(parameters)
    payload["text_scale"] = 1.0
    payload["glyphs"] = glyphs
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    polygon_lines = "\n".join(f"  {statement}" for statement in statements)
    return r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ChatCAD 名牌仿真实验室</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef2f5;color:#15202b;font-family:Inter,"Microsoft YaHei",sans-serif}.app{display:grid;grid-template-columns:330px 1fr;min-height:100vh}.side{background:#fff;border-right:1px solid #d9e1e7;padding:22px;overflow:auto;max-height:100vh}.eyebrow{font-size:12px;color:#16765d}.fixed{padding:10px 12px;background:#eef8f4;border-radius:10px;font-size:13px}.field{margin:12px 0}.field label{display:flex;justify-content:space-between;font-size:13px}.field input{width:100%;margin-top:6px}.actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:18px}button{min-height:43px;border:1px solid #cbd5dd;border-radius:10px;background:#fff;cursor:pointer}.stage-wrap{padding:20px}.stage{height:calc(100vh - 40px);min-height:520px;border:1px solid #d9e1e7;border-radius:18px;background:#fff;position:relative;overflow:hidden}.stage canvas{width:100%;height:100%}.hint{position:absolute;left:18px;bottom:16px;color:#667784;font-size:12px}.status{font-size:12px;color:#16765d;min-height:18px;margin-top:8px}@media(max-width:780px){.app{grid-template-columns:1fr}.side{max-height:none}.stage{height:520px}}</style></head><body><main class="app"><aside class="side"><div class="eyebrow">CHATCAD · 无需 MakerWorld 登录</div><h1>__NAME__</h1><p class="fixed">文字：<strong>__LABEL__</strong><br>当前页面可调整尺寸、孔位和文字几何；要改文字内容，请回到 ChatCAD 重新生成。</p><div id="fields"></div><div class="actions"><button id="copy">复制 OpenSCAD</button><button id="download">下载 .scad</button></div><div class="status" id="status"></div></aside><section class="stage-wrap"><div class="stage"><canvas id="view"></canvas><span class="hint">这是参数仿真预览；导出后仍需切片和实物试打。</span></div></section></main><script>
const s=__DATA__,$=id=>document.getElementById(id),defs=[['tag_length','长度',30,200,1],['tag_width','宽度',12,80,1],['plate_thickness','底板厚度',1,10,.1],['corner_radius','圆角',0,20,.5],['hole_diameter','孔径',.8,10,.1],['hole_margin_x','孔距左边',0,50,.5],['hole_margin_y','孔距上边',0,50,.5],['text_depth','文字凸起',.4,5,.1],['text_scale','文字缩放',.4,2,.05],['text_x','文字左右',-100,100,.5],['text_y','文字上下',-100,100,.5]];
$('fields').innerHTML=defs.map(([k,n,min,max,step])=>`<div class="field"><label>${n}<output id="${k}v"></output></label><input id="${k}" type="range" min="${min}" max="${max}" step="${step}" value="${s[k]}"></div>`).join('');for(const[k]of defs)$(k).oninput=()=>{s[k]=Number($(k).value);draw()};
const c=$('view'),ctx=c.getContext('2d');function rr(x,y,w,h,r){r=Math.max(0,Math.min(r,w/2,h/2));ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath()}
function draw(){const b=c.getBoundingClientRect(),d=devicePixelRatio||1;c.width=b.width*d;c.height=b.height*d;const pad=70*d,scale=Math.min((c.width-2*pad)/s.tag_length,(c.height-2*pad)/s.tag_width),w=s.tag_length*scale,h=s.tag_width*scale,x=(c.width-w)/2,y=(c.height-h)/2,rad=s.corner_radius*scale,shadow=Math.max(3,s.plate_thickness*scale*.22);ctx.clearRect(0,0,c.width,c.height);ctx.fillStyle='#9aaab4';rr(x+shadow,y+shadow,w,h,rad);ctx.fill();ctx.fillStyle='#dce7ec';ctx.strokeStyle='#334956';ctx.lineWidth=2*d;rr(x,y,w,h,rad);ctx.fill();ctx.stroke();const hx=x+s.hole_margin_x*scale,hy=y+s.hole_margin_y*scale;ctx.beginPath();ctx.arc(hx,hy,s.hole_diameter*scale/2,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.stroke();ctx.save();ctx.translate(c.width/2+s.text_x*scale,c.height/2-s.text_y*scale);ctx.scale(scale*s.text_scale,-scale*s.text_scale);ctx.fillStyle='#2e5969';for(const glyph of s.glyphs){ctx.beginPath();for(const contour of glyph){if(!contour.length)continue;ctx.moveTo(contour[0][0],contour[0][1]);for(let i=1;i<contour.length;i++)ctx.lineTo(contour[i][0],contour[i][1]);ctx.closePath()}ctx.fill('evenodd')}ctx.restore();for(const[k]of defs)$(k+'v').value=Number(s[k]).toFixed(k==='text_scale'?2:1)}window.onresize=draw;
function scad(){return`// ChatMaker Chat3D offline nameplate\n// 固化文字：${s.engrave_text}。改字请回 ChatCAD 重新生成。\n/* [尺寸] */\ntag_length = ${s.tag_length};\ntag_width = ${s.tag_width};\nplate_thickness = ${s.plate_thickness};\ncorner_radius = ${s.corner_radius};\n/* [文字几何] */\ntext_raise = ${s.text_depth};\ntext_scale = ${s.text_scale};\ntext_x = ${s.text_x};\ntext_y = ${s.text_y};\n/* [钥匙孔] */\nhole_diameter = ${s.hole_diameter};\nhole_margin_x = ${s.hole_margin_x};\nhole_margin_y = ${s.hole_margin_y};\n$fn=96;\neffective_corner_radius=max(0,min(corner_radius,tag_width/2-0.5,tag_length/2-0.5));\nhole_x=-(tag_length/2-hole_margin_x);hole_y=tag_width/2-hole_margin_y;\nmodule rounded_plate_2d(){offset(r=effective_corner_radius)square([max(.1,tag_length-2*effective_corner_radius),max(.1,tag_width-2*effective_corner_radius)],center=true);}\nmodule plate(){difference(){linear_extrude(height=plate_thickness)rounded_plate_2d();translate([hole_x,hole_y,-.1])cylinder(h=plate_thickness+.2,d=hole_diameter);}}\nmodule label_glyphs(){\n__POLYGONS__\n}\nunion(){plate();translate([text_x,text_y,plate_thickness-.2])linear_extrude(height=text_raise+.2)scale(text_scale)label_glyphs();}\n`}
async function copyScad(){const value=scad();try{await navigator.clipboard.writeText(value)}catch(e){const t=document.createElement('textarea');t.value=value;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove()}$('status').textContent='OpenSCAD 代码已复制'}function dl(){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([scad()],{type:'text/plain'}));a.download='__FILE__.scad';a.click();$('status').textContent='OpenSCAD 文件已下载'}$('copy').onclick=copyScad;$('download').onclick=dl;draw();
</script></body></html>'''.replace("__NAME__", html.escape(name)).replace("__LABEL__", html.escape(str(parameters["engrave_text"]))).replace("__FILE__", name).replace("__DATA__", data).replace("__POLYGONS__", polygon_lines)


def generate(request: dict[str, Any], name: str, output: Path) -> dict[str, Any]:
    delivery_mode = str(request.get("delivery_mode", "makerlab-code")).strip()
    if delivery_mode not in {"makerlab-code", "chatmaker-preview"}:
        raise ValueError("unsupported_chat3d_delivery_mode")
    code, parameters = _scad(name, request.get("parameters", {}))
    if delivery_mode == "chatmaker-preview":
        statements, glyphs = _polygon_text(request.get("parameters", {}), parameters)
        code = _polygon_scad(name, parameters, statements)
        output.mkdir(parents=True, exist_ok=True)
        files = {
            "project": output / "project.json",
            "scad": output / f"{name}.scad",
            "preview_lab": output / "preview-lab.html",
        }
        files["scad"].write_text(code, encoding="utf-8", newline="\n")
        files["preview_lab"].write_text(_preview_lab(name, parameters, glyphs, statements), encoding="utf-8", newline="\n")
        project = {
            "schema_version": "1.0",
            "mode": "chat3d",
            "design_kind": "nameplate",
            "project_name": name,
            "parameters": parameters,
            "text_rendering": "glyph-outline-polygons",
            "model_generated": "unverified",
            "file_opened": "unverified",
            "physical_fit": "unverified",
        }
        files["project"].write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return {
            "success": True,
            "action": "generate",
            "mode": "chat3d",
            "design_kind": "nameplate",
            "delivery_mode": delivery_mode,
            "scad_code": code,
            "preview_lab": str(files["preview_lab"]),
            "files": {key: str(path) for key, path in files.items()},
            "parameters": parameters,
            "text_rendering": {
                "strategy": "glyph-outline-polygons",
                "makerlab_font_required": False,
                "text_content_editable_in_preview": False,
            },
            "scad_generated": "verified",
            "simulation_interface": "verified",
            "model_generated": "unverified",
            "file_opened": "unverified",
            "physical_fit": "unverified",
        }
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

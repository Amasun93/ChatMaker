from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

from .fabrication import get_fabrication_profile, list_fabrication_profiles
from .profiles import get_component_profile, get_profile, list_profiles


_PROJECT_NAME = re.compile(r"[^A-Za-z0-9\u4e00-\u9fff._-]+")


def _number(parameters: dict[str, Any], name: str, default: float, minimum: float, maximum: float) -> float:
    value = parameters.get(name, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name}_must_be_number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise ValueError(f"{name}_out_of_range")
    return result


def _geometry(
    profile: dict[str, Any],
    parameters: dict[str, Any],
    *,
    default_plate_thickness: float = 3.0,
) -> dict[str, Any]:
    outline = profile["outline"]
    holes = profile["mounting"]["holes"]
    clearance = _number(parameters, "clearance", 5.0, 1.0, 30.0)
    plate_thickness = _number(
        parameters, "plate_thickness", default_plate_thickness, 1.0, 10.0
    )
    standoff_height = _number(parameters, "standoff_height", 5.0, 0.0, 20.0)
    default_hole = max((float(item["diameter"]) for item in holes), default=3.2)
    hole_diameter = _number(parameters, "hole_diameter", default_hole, 0.8, 10.0)
    standoff_outer = _number(parameters, "standoff_outer_diameter", max(7.0, hole_diameter + 3.0), hole_diameter + 1.0, 20.0)
    return {
        "board_width": float(outline["width"]),
        "board_depth": float(outline["depth"]),
        "plate_width": float(outline["width"]) + clearance * 2,
        "plate_depth": float(outline["depth"]) + clearance * 2,
        "clearance": clearance,
        "plate_thickness": plate_thickness,
        "standoff_height": standoff_height,
        "hole_diameter": hole_diameter,
        "standoff_outer_diameter": standoff_outer,
        "holes": [{"x": float(item["x"]), "y": float(item["y"])} for item in holes],
    }


def _scad(project_name: str, geometry: dict[str, Any]) -> str:
    holes = ",\n  ".join(f"[{item['x']:.6f}, {item['y']:.6f}]" for item in geometry["holes"])
    return f'''// ChatMaker ChatCAD Alpha - {project_name}
$fn = 64;
plate_width = {geometry["plate_width"]:.6f};
plate_depth = {geometry["plate_depth"]:.6f};
plate_thickness = {geometry["plate_thickness"]:.6f};
standoff_height = {geometry["standoff_height"]:.6f};
standoff_outer_diameter = {geometry["standoff_outer_diameter"]:.6f};
hole_diameter = {geometry["hole_diameter"]:.6f};
mounting_holes = [
  {holes}
];

module mounting_plate() {{
  union() {{
    translate([-plate_width / 2, -plate_depth / 2, 0])
      cube([plate_width, plate_depth, plate_thickness]);
    for (point = mounting_holes)
      translate([point[0], point[1], plate_thickness])
        difference() {{
          cylinder(h=standoff_height, d=standoff_outer_diameter);
          translate([0, 0, -0.01]) cylinder(h=standoff_height + 0.02, d=hole_diameter);
        }}
  }}
}}

mounting_plate();
'''


def _svg(project_name: str, geometry: dict[str, Any]) -> str:
    width = geometry["plate_width"]
    depth = geometry["plate_depth"]
    board_x = (width - geometry["board_width"]) / 2
    board_y = (depth - geometry["board_depth"]) / 2
    circles = "\n".join(
        f'<circle cx="{width / 2 + item["x"]:.6f}" cy="{depth / 2 - item["y"]:.6f}" r="{geometry["hole_diameter"] / 2:.6f}" />'
        for item in geometry["holes"]
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.6f}mm" height="{depth:.6f}mm" viewBox="0 0 {width:.6f} {depth:.6f}">
  <title>{html.escape(project_name)}</title>
  <g fill="none" stroke="#111827" stroke-width="0.3">
    <rect x="0.15" y="0.15" width="{width - 0.3:.6f}" height="{depth - 0.3:.6f}" />
    <rect x="{board_x:.6f}" y="{board_y:.6f}" width="{geometry["board_width"]:.6f}" height="{geometry["board_depth"]:.6f}" stroke-dasharray="1.2 0.8" />
    {circles}
  </g>
</svg>
'''


def _dxf(geometry: dict[str, Any]) -> str:
    width = geometry["plate_width"]
    depth = geometry["plate_depth"]
    entities: list[str] = []
    points = [(0.0, 0.0), (width, 0.0), (width, depth), (0.0, depth)]
    for start, end in zip(points, points[1:] + points[:1]):
        entities.append(f"0\nLINE\n8\nOUTLINE\n10\n{start[0]:.6f}\n20\n{start[1]:.6f}\n11\n{end[0]:.6f}\n21\n{end[1]:.6f}\n")
    for item in geometry["holes"]:
        entities.append(
            f"0\nCIRCLE\n8\nMOUNTING\n10\n{width / 2 + item['x']:.6f}\n20\n{depth / 2 + item['y']:.6f}\n40\n{geometry['hole_diameter'] / 2:.6f}\n"
        )
    return "0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n" + "".join(entities) + "0\nENDSEC\n0\nEOF\n"


def _normal(a: tuple[float, float, float], b: tuple[float, float, float], c: tuple[float, float, float]) -> tuple[float, float, float]:
    ux, uy, uz = (b[index] - a[index] for index in range(3))
    vx, vy, vz = (c[index] - a[index] for index in range(3))
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length


def _box(width: float, depth: float, height: float) -> list[tuple[tuple[float, float, float], ...]]:
    x0, x1, y0, y1 = -width / 2, width / 2, -depth / 2, depth / 2
    v = [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (x0, y0, height), (x1, y0, height), (x1, y1, height), (x0, y1, height)]
    indices = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return [(v[a], v[b], v[c]) for a, b, c in indices]


def _tube(x: float, y: float, z: float, height: float, outer: float, inner: float, segments: int = 32) -> list[tuple[tuple[float, float, float], ...]]:
    triangles = []
    ro, ri = outer / 2, inner / 2
    for index in range(segments):
        a0, a1 = index * math.tau / segments, (index + 1) * math.tau / segments
        ob0, ob1 = (x + ro * math.cos(a0), y + ro * math.sin(a0), z), (x + ro * math.cos(a1), y + ro * math.sin(a1), z)
        ot0, ot1 = (ob0[0], ob0[1], z + height), (ob1[0], ob1[1], z + height)
        ib0, ib1 = (x + ri * math.cos(a0), y + ri * math.sin(a0), z), (x + ri * math.cos(a1), y + ri * math.sin(a1), z)
        it0, it1 = (ib0[0], ib0[1], z + height), (ib1[0], ib1[1], z + height)
        triangles.extend([(ob0, ob1, ot1), (ob0, ot1, ot0), (ib0, it1, ib1), (ib0, it0, it1), (ot0, ot1, it1), (ot0, it1, it0), (ob0, ib1, ob1), (ob0, ib0, ib1)])
    return triangles


def _stl(project_name: str, geometry: dict[str, Any]) -> str:
    solid_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", project_name).strip("-.") or "chatcad-model"
    triangles = _box(geometry["plate_width"], geometry["plate_depth"], geometry["plate_thickness"])
    for item in geometry["holes"]:
        triangles.extend(_tube(item["x"], item["y"], geometry["plate_thickness"], geometry["standoff_height"], geometry["standoff_outer_diameter"], geometry["hole_diameter"]))
    lines = [f"solid {solid_name}"]
    for a, b, c in triangles:
        normal = _normal(a, b, c)
        lines.append(f"  facet normal {normal[0]:.8f} {normal[1]:.8f} {normal[2]:.8f}\n    outer loop")
        lines.extend(f"      vertex {point[0]:.8f} {point[1]:.8f} {point[2]:.8f}" for point in (a, b, c))
        lines.append("    endloop\n  endfacet")
    lines.append(f"endsolid {solid_name}")
    return "\n".join(lines) + "\n"


def _lab_html(project_name: str, profile: dict[str, Any], geometry: dict[str, Any]) -> str:
    profile_json = json.dumps(profile, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    geometry_json = json.dumps(geometry, ensure_ascii=False, separators=(",", ":"))
    template = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ChatCAD 预览实验室</title><style>
:root{color-scheme:dark;--bg:#08111f;--panel:#101c2c;--line:#2a3a50;--cyan:#52e0d1;--amber:#ffc76b;--text:#eef6ff;--muted:#91a5bd}*{box-sizing:border-box}body{margin:0;font-family:Inter,"Microsoft YaHei",sans-serif;background:radial-gradient(circle at 80% 10%,#173550 0,#08111f 45%);color:var(--text);min-height:100vh}.shell{display:grid;grid-template-columns:minmax(260px,360px) 1fr;gap:18px;padding:18px;min-height:100vh}.controls,.lab{background:rgba(16,28,44,.88);border:1px solid var(--line);border-radius:18px;box-shadow:0 18px 50px #0007}.controls{padding:22px}.eyebrow{color:var(--cyan);font-size:12px;letter-spacing:.16em;text-transform:uppercase}h1{font-size:25px;margin:8px 0 4px}p{color:var(--muted);line-height:1.6;margin:5px 0 18px}.field{margin:18px 0}.field label{display:flex;justify-content:space-between;font-size:14px;margin-bottom:8px}.value{color:var(--amber);font-variant-numeric:tabular-nums}input[type=range]{width:100%;accent-color:var(--cyan)}.exports{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:24px}button{border:1px solid #34506d;border-radius:11px;background:#162a40;color:var(--text);padding:11px;cursor:pointer}button:hover{border-color:var(--cyan);transform:translateY(-1px)}.lab{padding:18px;display:grid;grid-template-rows:auto 1fr}.lab-head{display:flex;align-items:center;justify-content:space-between;padding:4px 5px 14px}.status{font-size:12px;color:var(--muted)}.stage{display:grid;place-items:center;min-height:520px;border-radius:14px;background:linear-gradient(135deg,#0b1625,#13263b);overflow:hidden}.stage svg{width:min(86%,900px);height:min(78vh,720px);filter:drop-shadow(0 18px 25px #0008)}.plate{fill:#173f4b;stroke:var(--cyan);stroke-width:.45}.board{fill:#d99a3522;stroke:var(--amber);stroke-width:.38;stroke-dasharray:2 1}.hole{fill:#08111f;stroke:#fff;stroke-width:.28}.dimension{fill:#cfe3f7;font-size:3px}@media(max-width:800px){.shell{grid-template-columns:1fr}.stage{min-height:420px}}
</style></head><body><main class="shell"><section class="controls"><div class="eyebrow">ChatCAD Alpha</div><h1>__PROJECT__</h1><p id="boardName"></p>
<div class="field"><label>边缘间隙 <span class="value" id="clearanceValue"></span></label><input id="clearance" type="range" min="1" max="30" step="0.5"></div>
<div class="field"><label>底板厚度 <span class="value" id="plateValue"></span></label><input id="plateThickness" type="range" min="1" max="10" step="0.5"></div>
<div class="field"><label>安装柱高度 <span class="value" id="heightValue"></span></label><input id="standoffHeight" type="range" min="0" max="20" step="0.5"></div>
<div class="field"><label>安装孔直径 <span class="value" id="holeValue"></span></label><input id="holeDiameter" type="range" min="0.8" max="10" step="0.1"></div>
<div class="exports"><button data-kind="dxf">导出 DXF</button><button data-kind="svg">导出 SVG</button><button data-kind="scad">导出 SCAD</button><button data-kind="stl">导出 STL</button></div>
<p style="font-size:12px;margin-top:16px">当前是规则安装底板原型。实体孔位与接口间隙仍需用真实板卡确认。</p></section>
<section class="lab"><header class="lab-head"><strong>右侧预览实验室</strong><span class="status" id="status">参数已同步</span></header><div class="stage"><svg id="preview" xmlns="http://www.w3.org/2000/svg"></svg></div></section></main>
<script>const profile=__PROFILE_JSON__;const defaults=__GEOMETRY_JSON__;const name="__PROJECT_JS__";const $=id=>document.getElementById(id);const state={clearance:defaults.clearance,plateThickness:defaults.plate_thickness,standoffHeight:defaults.standoff_height,holeDiameter:defaults.hole_diameter,standoffOuter:defaults.standoff_outer_diameter};
$("boardName").textContent=profile.name+" · "+profile.revision;for(const [id,key] of [["clearance","clearance"],["plateThickness","plateThickness"],["standoffHeight","standoffHeight"],["holeDiameter","holeDiameter"]]){$(id).value=state[key];$(id).addEventListener("input",()=>{state[key]=Number($(id).value);render()})}
function geom(){return{bw:profile.outline.width,bd:profile.outline.depth,pw:profile.outline.width+state.clearance*2,pd:profile.outline.depth+state.clearance*2,holes:profile.mounting.holes}}
function render(){const g=geom(),svg=$("preview");svg.setAttribute("viewBox",`0 0 ${g.pw} ${g.pd}`);const circles=g.holes.map(h=>`<circle class="hole" cx="${g.pw/2+h.x}" cy="${g.pd/2-h.y}" r="${state.holeDiameter/2}"/>`).join("");svg.innerHTML=`<rect class="plate" x=".2" y=".2" width="${g.pw-.4}" height="${g.pd-.4}" rx="2"/><rect class="board" x="${state.clearance}" y="${state.clearance}" width="${g.bw}" height="${g.bd}"/>${circles}<text class="dimension" x="2" y="${g.pd-2}">${g.pw.toFixed(1)} × ${g.pd.toFixed(1)} mm</text>`;$("clearanceValue").textContent=state.clearance.toFixed(1)+" mm";$("plateValue").textContent=state.plateThickness.toFixed(1)+" mm";$("heightValue").textContent=state.standoffHeight.toFixed(1)+" mm";$("holeValue").textContent=state.holeDiameter.toFixed(1)+" mm";$("status").textContent="参数已同步"}
function download(filename,text,type="text/plain"){const blob=new Blob([text],{type});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);$("status").textContent="已导出 "+filename}
function svgText(){const copy=$("preview").cloneNode(true);copy.setAttribute("width",geom().pw+"mm");copy.setAttribute("height",geom().pd+"mm");return new XMLSerializer().serializeToString(copy)}
function dxf(){const g=geom(),p=[[0,0],[g.pw,0],[g.pw,g.pd],[0,g.pd]];let e="";for(let i=0;i<4;i++){const a=p[i],b=p[(i+1)%4];e+=`0\nLINE\n8\nOUTLINE\n10\n${a[0]}\n20\n${a[1]}\n11\n${b[0]}\n21\n${b[1]}\n`}for(const h of g.holes)e+=`0\nCIRCLE\n8\nMOUNTING\n10\n${g.pw/2+h.x}\n20\n${g.pd/2+h.y}\n40\n${state.holeDiameter/2}\n`;return"0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n"+e+"0\nENDSEC\n0\nEOF\n"}
function scad(){const g=geom(),holes=g.holes.map(h=>`[${h.x},${h.y}]`).join(",");return`$fn=64;plate_width=${g.pw};plate_depth=${g.pd};plate_thickness=${state.plateThickness};standoff_height=${state.standoffHeight};standoff_outer_diameter=${Math.max(state.standoffOuter,state.holeDiameter+1)};hole_diameter=${state.holeDiameter};mounting_holes=[${holes}];union(){translate([-plate_width/2,-plate_depth/2,0])cube([plate_width,plate_depth,plate_thickness]);for(p=mounting_holes)translate([p[0],p[1],plate_thickness])difference(){cylinder(h=standoff_height,d=standoff_outer_diameter);translate([0,0,-.01])cylinder(h=standoff_height+.02,d=hole_diameter);}}\n`}
function facet(a,b,c){return`facet normal 0 0 0\n outer loop\n  vertex ${a.join(" ")}\n  vertex ${b.join(" ")}\n  vertex ${c.join(" ")}\n endloop\nendfacet\n`}function box(w,d,h){const x=w/2,y=d/2,v=[[-x,-y,0],[x,-y,0],[x,y,0],[-x,y,0],[-x,-y,h],[x,-y,h],[x,y,h],[-x,y,h]],q=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]];return q.map(t=>facet(v[t[0]],v[t[1]],v[t[2]])).join("")}function tube(x,y,z,h,ro,ri){let s="",n=32;for(let i=0;i<n;i++){const a=i*Math.PI*2/n,b=(i+1)*Math.PI*2/n,ob0=[x+ro*Math.cos(a),y+ro*Math.sin(a),z],ob1=[x+ro*Math.cos(b),y+ro*Math.sin(b),z],ot0=[ob0[0],ob0[1],z+h],ot1=[ob1[0],ob1[1],z+h],ib0=[x+ri*Math.cos(a),y+ri*Math.sin(a),z],ib1=[x+ri*Math.cos(b),y+ri*Math.sin(b),z],it0=[ib0[0],ib0[1],z+h],it1=[ib1[0],ib1[1],z+h];s+=facet(ob0,ob1,ot1)+facet(ob0,ot1,ot0)+facet(ib0,it1,ib1)+facet(ib0,it0,it1)+facet(ot0,ot1,it1)+facet(ot0,it1,it0)+facet(ob0,ib1,ob1)+facet(ob0,ib0,ib1)}return s}function stl(){const g=geom();let s=`solid ${name}\n`+box(g.pw,g.pd,state.plateThickness);for(const h of g.holes)s+=tube(h.x,h.y,state.plateThickness,state.standoffHeight,Math.max(state.standoffOuter,state.holeDiameter+1)/2,state.holeDiameter/2);return s+`endsolid ${name}\n`}
document.querySelectorAll("button[data-kind]").forEach(button=>button.addEventListener("click",()=>{const kind=button.dataset.kind;if(kind==="svg")download(name+".svg",svgText(),"image/svg+xml");if(kind==="dxf")download(name+".dxf",dxf());if(kind==="scad")download(name+".scad",scad());if(kind==="stl")download(name+".stl",stl())}));render();</script></body></html>'''
    return template.replace("__PROJECT__", html.escape(project_name)).replace("__PROJECT_JS__", json.dumps(project_name)[1:-1]).replace("__PROFILE_JSON__", profile_json).replace("__GEOMETRY_JSON__", geometry_json)


def generate_project(request: dict[str, Any]) -> dict[str, Any]:
    board_id = str(request.get("board_id", ""))
    loaded = get_profile(board_id)
    if not loaded.get("success"):
        return loaded
    mode = str(request.get("mode", "mounting-plate"))
    if mode not in {"mounting-plate", "chat2d", "chat3d"}:
        return {"success": False, "error": "unsupported_cad_mode", "mode": mode}
    project_name = _PROJECT_NAME.sub("-", str(request.get("project_name", "chatcad-project")).strip()).strip("-.") or "chatcad-project"
    output_dir = Path(str(request.get("output_dir", project_name))).expanduser().resolve()
    parameters = request.get("parameters", {})
    if not isinstance(parameters, dict):
        return {"success": False, "error": "parameters_must_be_object"}
    if mode == "chat3d":
        from . import chat3d
        try:
            return chat3d.generate(request, loaded["profile"], output_dir, project_name)
        except (OSError, ValueError) as exc:
            return {"success": False, "error": "cad_generation_failed", "detail": str(exc)}
    equipment_id = str(request.get("equipment_id", "lasermaker-generic"))
    material_id = str(request.get("material_id", "wood-sheet-3mm"))
    fabrication = get_fabrication_profile(equipment_id, material_id)
    if not fabrication.get("success"):
        return fabrication
    if mode == "chat2d":
        from . import chat2d
        try:
            return chat2d.generate(request, loaded["profile"], fabrication, output_dir, project_name)
        except (OSError, ValueError) as exc:
            return {"success": False, "error": "cad_generation_failed", "detail": str(exc)}
    try:
        geometry = _geometry(
            loaded["profile"],
            parameters,
            default_plate_thickness=float(
                fabrication["material"]["default_thickness_mm"]
            ),
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "project": output_dir / "project.json",
            "scad": output_dir / f"{project_name}.scad",
            "dxf": output_dir / f"{project_name}.dxf",
            "svg": output_dir / f"{project_name}.svg",
            "stl": output_dir / f"{project_name}.stl",
            "preview_lab": output_dir / "preview-lab.html",
        }
        files["scad"].write_text(_scad(project_name, geometry), encoding="utf-8", newline="\n")
        files["dxf"].write_text(_dxf(geometry), encoding="ascii", newline="\n")
        files["svg"].write_text(_svg(project_name, geometry), encoding="utf-8", newline="\n")
        files["stl"].write_text(_stl(project_name, geometry), encoding="ascii", newline="\n")
        files["preview_lab"].write_text(_lab_html(project_name, loaded["profile"], geometry), encoding="utf-8", newline="\n")
        project = {
            "schema_version": "1.0",
            "project_name": project_name,
            "board_id": board_id,
            "model_kind": "mounting-plate",
            "equipment_id": equipment_id,
            "material_id": material_id,
            "fabrication": {
                "layer_rules": fabrication["equipment"]["layer_rules"],
                "process_order": fabrication["equipment"]["process_order"],
                "parameter_policy": fabrication["equipment"]["parameter_policy"],
            },
            "parameters": geometry,
            "physical_fit": "unverified",
        }
        files["project"].write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        return {"success": False, "error": "cad_generation_failed", "detail": str(exc)}
    return {
        "success": True,
        "action": "generate",
        "status": "alpha_generated",
        "board_id": board_id,
        "equipment_id": equipment_id,
        "material_id": material_id,
        "output_dir": str(output_dir),
        "files": {name: str(path) for name, path in files.items()},
        "physical_fit": "unverified",
    }


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action == "list-profiles":
        return list_profiles()
    if action == "profile":
        return get_profile(str(request.get("board_id", "")))
    if action == "component-profile":
        return get_component_profile(str(request.get("component_id", "")))
    if action == "list-fabrication-profiles":
        return list_fabrication_profiles()
    if action == "fabrication-profile":
        return get_fabrication_profile(
            str(request.get("equipment_id", "lasermaker-generic")),
            str(request.get("material_id", "wood-sheet-3mm")),
        )
    if action == "generate":
        return generate_project(request)
    return {"success": False, "error": "unknown_cad_action", "action": action}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a ChatCAD Alpha parameterized maker model.")
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request_json)
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        result = execute_request(request)
    except Exception as exc:
        result = {"success": False, "error": "cad_request_failed", "detail": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

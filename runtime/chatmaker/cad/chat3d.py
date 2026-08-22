"""Chat3D V1 printable enclosure generator."""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
import re
from typing import Any


def _num(values: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    value = values.get(key, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not low <= float(value) <= high:
        raise ValueError(f"{key}_out_of_range")
    return float(value)


def geometry(profile: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    board = profile["outline"]
    return {
        "inner_width": _num(values, "inner_width", float(board["width"]) + 12, 20, 500),
        "inner_depth": _num(values, "inner_depth", float(board["depth"]) + 12, 20, 500),
        "inner_height": _num(values, "inner_height", 35, 8, 300),
        "wall": _num(values, "wall", 2.4, 1, 8),
        "floor": _num(values, "floor", 2.4, 1, 8),
        "lid": _num(values, "lid", 2.0, 1, 8),
        "standoff_height": _num(values, "standoff_height", 5, 0, 20),
        "hole_diameter": _num(values, "hole_diameter", 2.8, 1, 8),
        "holes": profile["mounting"]["holes"],
    }


def _engrave_plan(values: dict[str, Any], g: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve CJK-safe lid text settings (polygon geometry, never text()).

    Glyph outlines are baked once: the SCAD gets polygon statements centred on
    the label's own origin (so Bambu customizer sliders can still move, scale
    and re-depth it), the STL gets absolutely positioned triangles, and the
    lab page embeds the contours for re-export.
    """
    label = str(values.get("engrave_text", "")).strip()
    if not label:
        return None
    from . import text as text_engine

    size = _num(values, "text_size", min(12.0, g["inner_width"] / 4), 3, 60)
    depth = _num(values, "text_depth", 1.2, 0.4, 5)
    raw_font = values.get("engrave_font")
    font = (str(raw_font).strip() or None) if raw_font else None
    layout = text_engine.glyph_layout(label, size, font)
    width = layout["width"]
    centered = (-width / 2, -size / 2)
    polygons = text_engine.scad_polygons_from_layout(layout, centered)
    contours = [
        [
            [(x + centered[0], y + centered[1]) for x, y in contour]
            for contour in glyph["contours"]
        ]
        for glyph in layout["glyphs"]
    ]
    outer_width = g["inner_width"] + 2 * g["wall"]
    outer_depth = g["inner_depth"] + 2 * g["wall"]
    return {
        "text": label,
        "size": size,
        "depth": depth,
        "font": font,
        "layout": layout,
        "polygons": polygons,
        "contours": contours,
        "width": width,
        "font_file": layout["font"],
        "stl_offset": (
            (outer_width - width) / 2,
            outer_depth + 8 + outer_depth / 2 - size / 2,
        ),
    }


def _scad(name: str, g: dict[str, Any], engrave: dict[str, Any] | None = None) -> str:
    holes = ",".join(f"[{float(h['x'])},{float(h['y'])}]" for h in g["holes"])
    label_params = ""
    label_module = ""
    label_calls = ""
    if engrave:
        polygon_lines = "\n".join(f"  {statement}" for statement in engrave["polygons"])
        label_params = f'''
/* [文字雕刻] */
show_label = true; // 显示中文文字（改文字内容需回到 ChatCAD 重新生成）
label_depth = {engrave["depth"]}; // 文字浮凸深度 (mm)
label_scale = 1.0; // 文字缩放
label_x = 0; // 文字水平偏移 (mm)
label_y = 0; // 文字垂直偏移 (mm)
'''
        label_module = f'''
// 中文以字形轮廓多边形固化：不使用 OpenSCAD 字体渲染，也不引用任何字体文件，
// OpenSCAD 任意版本与拓竹自定义参数实验室都能正确显示。
module label_glyphs(){{
{polygon_lines}
}}
module label_on(cover_y){{
  if (show_label)
    translate([inner_width/2+wall+label_x, cover_y+inner_depth/2+wall+label_y, lid])
      linear_extrude(height=label_depth)
        scale(label_scale)
          children();
}}
'''
        label_calls = "  label_on(inner_depth+2*wall+8) label_glyphs();\n"
    return f'''// ChatMaker Chat3D V1 - {name}
// 盒体中心为 XY 原点、Z 向上，单位 mm。
/* [输出] */
part = "assembled"; // [assembled,base,lid]

/* [内腔尺寸] */
inner_width = {g["inner_width"]}; // 内腔宽度 (mm)
inner_depth = {g["inner_depth"]}; // 内腔深度 (mm)
inner_height = {g["inner_height"]}; // 内腔高度 (mm)

/* [壁厚] */
wall = {g["wall"]}; // 侧壁厚 (mm)
floor = {g["floor"]}; // 底板厚 (mm)
lid = {g["lid"]}; // 上盖厚 (mm)

/* [安装柱] */
standoff_height = {g["standoff_height"]}; // 安装柱高度 (mm)
hole_diameter = {g["hole_diameter"]}; // 安装孔直径 (mm)
{label_params}
$fn = 64;
holes = [{holes}];

module base_part(){{
  difference(){{
    cube([inner_width+2*wall, inner_depth+2*wall, inner_height+floor]);
    translate([wall,wall,floor]) cube([inner_width, inner_depth, inner_height+1]);
  }}
  for(p=holes)
    translate([wall+inner_width/2+p[0], wall+inner_depth/2-p[1], floor])
      difference(){{
        cylinder(h=standoff_height, d=hole_diameter+3);
        translate([0,0,-.1]) cylinder(h=standoff_height+.2, d=hole_diameter);
      }}
}}
module cover_part(){{cube([inner_width+2*wall, inner_depth+2*wall, lid]);}}
{label_module}
if (part == "base") base_part();
if (part == "lid") {{
  cover_part();
  label_on(0) label_glyphs();
}}
if (part == "assembled") {{
  base_part();
  translate([0, inner_depth+2*wall+8, 0]) cover_part();
{label_calls}}}
'''


def _box(x: float, y: float, z: float, w: float, d: float, h: float):
    v=[(x,y,z),(x+w,y,z),(x+w,y+d,z),(x,y+d,z),(x,y,z+h),(x+w,y,z+h),(x+w,y+d,z+h),(x,y+d,z+h)]
    q=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return [(v[a],v[b],v[c]) for a,b,c in q]


def _normal(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]);m=math.sqrt(sum(x*x for x in n)) or 1
    return tuple(x/m for x in n)


def _stl(name: str, g: dict[str, Any], engrave: dict[str, Any] | None = None) -> str:
    w,d,h,t,f,l=g["inner_width"],g["inner_depth"],g["inner_height"],g["wall"],g["floor"],g["lid"]
    ow,od=w+2*t,d+2*t
    triangles=[]
    triangles += _box(0,0,0,ow,od,f)
    triangles += _box(0,0,f,t,od,h)
    triangles += _box(ow-t,0,f,t,od,h)
    triangles += _box(t,0,f,w,t,h)
    triangles += _box(t,od-t,f,w,t,h)
    triangles += _box(0,od+8,0,ow,od,l)
    if engrave:
        from .text import triangles_from_layout

        triangles += triangles_from_layout(
            engrave["layout"],
            engrave["depth"],
            base_z=l,
            offset=engrave["stl_offset"],
        )
    solid=re.sub(r"[^A-Za-z0-9_.-]","-",name) or "chat3d"
    lines=[f"solid {solid}"]
    for a,b,c in triangles:
        n=_normal(a,b,c);lines.append(f"facet normal {n[0]} {n[1]} {n[2]}\n outer loop")
        lines.extend(f"  vertex {p[0]} {p[1]} {p[2]}" for p in (a,b,c));lines.append(" endloop\nendfacet")
    lines.append(f"endsolid {solid}")
    return "\n".join(lines)+"\n"


def _lab(name: str, g: dict[str, Any], engrave: dict[str, Any] | None = None) -> str:
    data=json.dumps(g,separators=(",",":"));safe=html.escape(name)
    if engrave:
        label_json=json.dumps({"depth":engrave["depth"],"glyphs":engrave["contours"]},separators=(",",":"))
        engrave_note=(f'<p class="engrave">盖面浮凸文字：<strong>{html.escape(engrave["text"])}</strong>'
                      f'（{engrave["size"]:g} mm，深度 {engrave["depth"]:g} mm）——中文按轮廓多边形写入 SCAD 与 STL，不依赖 OpenSCAD 字体。'
                      f'导出的 SCAD 支持 OpenSCAD customizer 与拓竹自定义参数实验室：文字深度/缩放/位置可调，改文字内容请回 ChatCAD 重新生成。</p>')
    else:
        label_json="null"
        engrave_note=''
    return r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chat3D 打印外壳实验室</title><style>
*{box-sizing:border-box}body{margin:0;background:#edf1f4;color:#14202a;font-family:Inter,"Microsoft YaHei",sans-serif}.app{display:grid;grid-template-columns:320px 1fr;min-height:100vh}.side{padding:24px;background:#fff;border-right:1px solid #d9e0e6}.field{margin:15px 0}.field label{display:flex;justify-content:space-between;font-size:14px}.field input{width:100%;margin-top:7px}button{min-height:46px;padding:0 18px;border:1px solid #ccd5dd;border-radius:11px;background:#fff;cursor:pointer}.exports{display:flex;gap:8px}.lab{padding:20px}.stage{height:calc(100vh - 40px);min-height:520px;background:#fff;border:1px solid #d9e0e6;border-radius:18px;overflow:hidden;position:relative}.stage canvas{width:100%;height:100%;touch-action:none}.hint{position:absolute;left:18px;bottom:15px;color:#5f6e7a;font-size:13px}.engrave{font-size:13px;color:#33505f;background:#eef6f2;border:1px solid #cfe6da;border-radius:10px;padding:10px 12px}@media(max-width:780px){.app{grid-template-columns:1fr}.stage{height:560px}}</style></head><body><main class="app"><aside class="side"><small>CHATCAD · CHAT3D</small><h1>__NAME__</h1><p>3D 打印外壳：底壳、壁、安装柱与独立上盖。</p><div id="fields"></div>__ENGRAVE__<div class="exports"><button id="scad">导出 OpenSCAD</button><button id="stl">导出 STL</button></div><p><small>生成文件未经过切片和实物试装。正式打印前建议先打印孔位或接口小样。</small></p></aside><section class="lab"><div class="stage"><canvas id="view"></canvas><span class="hint">拖拽旋转 · 滚轮缩放 · Shift+拖拽平移</span></div></section></main><script>
const s=__DATA__,label=__LABEL__,$=id=>document.getElementById(id),defs=[['inner_width','内宽',20,500,.5],['inner_depth','内深',20,500,.5],['inner_height','内高',8,300,.5],['wall','壁厚',1,8,.1],['floor','底厚',1,8,.1],['lid','盖厚',1,8,.1],['standoff_height','安装柱高',0,20,.5],['hole_diameter','孔径',1,8,.1]];$('fields').innerHTML=defs.map(([k,n,min,max,step])=>`<div class="field"><label>${n}<output id="${k}v"></output></label><input id="${k}" type="range" min="${min}" max="${max}" step="${step}" value="${s[k]}"></div>`).join('');for(const[k]of defs){$(k).oninput=()=>{s[k]=Number($(k).value);draw()}}
function labelContours(z){if(!label)return;ctx.fillStyle='#f5c66d';ctx.strokeStyle='#795019';ctx.lineWidth=1.2;for(const contours of label.glyphs){ctx.beginPath();for(const contour of contours){if(!contour.length)continue;ctx.moveTo(...project([contour[0][0],contour[0][1],z]));for(let i=1;i<contour.length;i++)ctx.lineTo(...project([contour[i][0],contour[i][1],z]));ctx.closePath()}ctx.fill('evenodd');ctx.stroke()}}
const c=$('view'),ctx=c.getContext('2d');let rx=-.55,ry=.7,zoom=3,panX=0,panY=0,drag=null;function project(p){let[x,y,z]=p,cy=Math.cos(ry),sy=Math.sin(ry),cx=Math.cos(rx),sx=Math.sin(rx),x1=x*cy+z*sy,z1=-x*sy+z*cy,y1=y*cx-z1*sx;return[c.width/2+panX+x1*zoom,c.height/2+panY+y1*zoom]};function cuboid(x,y,z,w,d,h,color){const v=[[x,y,z],[x+w,y,z],[x+w,y+d,z],[x,y+d,z],[x,y,z+h],[x+w,y,z+h],[x+w,y+d,z+h],[x,y+d,z+h]],edges=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];ctx.strokeStyle=color;ctx.lineWidth=2;for(const[a,b]of edges){const p=project(v[a]),q=project(v[b]);ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.stroke()}}function draw(){const r=c.getBoundingClientRect(),d=devicePixelRatio||1;c.width=r.width*d;c.height=r.height*d;ctx.clearRect(0,0,c.width,c.height);panX=panX||0;panY=panY||0;const w=s.inner_width,dpt=s.inner_depth,t=s.wall,h=s.inner_height;cuboid(-w/2-t,-dpt/2-t,0,w+2*t,dpt+2*t,s.floor,'#177a61');cuboid(-w/2-t,-dpt/2-t,s.floor,t,dpt+2*t,h,'#172b3a');cuboid(w/2,-dpt/2-t,s.floor,t,dpt+2*t,h,'#172b3a');cuboid(-w/2,-dpt/2-t,s.floor,w,t,h,'#172b3a');cuboid(-w/2,dpt/2,s.floor,w,t,h,'#172b3a');cuboid(-w/2-t,-dpt/2-t,h+s.floor+8,w+2*t,dpt+2*t,s.lid,'#d28d2d');for(const[k]of defs)$(k+'v').value=s[k]+' mm'}
const drawWireframe=draw;draw=()=>{drawWireframe();labelContours(s.inner_height+s.floor+8+s.lid+.02)};
c.onpointerdown=e=>drag={x:e.clientX,y:e.clientY,rx,ry,panX,panY,shift:e.shiftKey};c.onpointermove=e=>{if(!drag)return;if(drag.shift){panX=drag.panX+(e.clientX-drag.x)*devicePixelRatio;panY=drag.panY+(e.clientY-drag.y)*devicePixelRatio}else{ry=drag.ry+(e.clientX-drag.x)*.01;rx=drag.rx+(e.clientY-drag.y)*.01}draw()};c.onpointerup=()=>drag=null;c.onwheel=e=>{e.preventDefault();zoom=Math.max(.5,Math.min(10,zoom-e.deltaY*.004));draw()};window.onresize=draw;
function scad(){const L=label,ow=s.inner_width+2*s.wall,od=s.inner_depth+2*s.wall,holes=(s.holes||[]).map(h=>`[${h.x},${h.y}]`).join(",");let lp="",lm="",la="",ll="";if(L){const polys=L.glyphs.filter(cs=>cs.length).map(cs=>{let pts=[],paths=[];for(const c of cs){paths.push("["+Array.from({length:c.length},(_,i)=>pts.length+i).join(",")+"]");for(const p of c)pts.push("["+p[0].toFixed(4)+","+p[1].toFixed(4)+"]")}return`  polygon(points=[${pts.join(",")}],paths=[${paths.join(",")}]);`}).join("\n");lp=`\n/* [文字雕刻] */\nshow_label = true; // 显示中文文字\nlabel_depth = ${L.depth}; // 文字浮凸深度 (mm)\nlabel_scale = 1.0; // 文字缩放\nlabel_x = 0; // 文字水平偏移 (mm)\nlabel_y = 0; // 文字垂直偏移 (mm)\n`;lm=`\nmodule label_glyphs(){\n${polys}\n}\nmodule label_on(cover_y){\n  if(show_label)\n    translate([inner_width/2+wall+label_x,cover_y+inner_depth/2+wall+label_y,lid])\n      linear_extrude(height=label_depth) scale(label_scale) children();\n}\n`;la=`  label_on(inner_depth+2*wall+8) label_glyphs();\n`;ll=`  label_on(0) label_glyphs();\n`}return`// ChatMaker Chat3D V1\n/* [输出] */\npart = "assembled"; // [assembled,base,lid]\n\n/* [内腔尺寸] */\ninner_width = ${s.inner_width}; // 内腔宽度 (mm)\ninner_depth = ${s.inner_depth}; // 内腔深度 (mm)\ninner_height = ${s.inner_height}; // 内腔高度 (mm)\n\n/* [壁厚] */\nwall = ${s.wall}; // 侧壁厚 (mm)\nfloor = ${s.floor}; // 底板厚 (mm)\nlid = ${s.lid}; // 上盖厚 (mm)\n\n/* [安装柱] */\nstandoff_height = ${s.standoff_height}; // 安装柱高度 (mm)\nhole_diameter = ${s.hole_diameter}; // 安装孔直径 (mm)${lp}\n$fn = 64;\nholes = [${holes}];\n\nmodule base_part(){difference(){cube([inner_width+2*wall,inner_depth+2*wall,inner_height+floor]);translate([wall,wall,floor])cube([inner_width,inner_depth,inner_height+1]);}for(p=holes)translate([wall+inner_width/2+p[0],wall+inner_depth/2-p[1],floor])difference(){cylinder(h=standoff_height,d=hole_diameter+3);translate([0,0,-.1])cylinder(h=standoff_height+.2,d=hole_diameter);}}\nmodule cover_part(){cube([inner_width+2*wall,inner_depth+2*wall,lid]);}${lm}\nif(part=="base")base_part();\nif(part=="lid"){cover_part();${ll}}\nif(part=="assembled"){base_part();translate([0,inner_depth+2*wall+8,0])cover_part();${la}}\n`};function box(x,y,z,w,d,h){const v=[[x,y,z],[x+w,y,z],[x+w,y+d,z],[x,y+d,z],[x,y,z+h],[x+w,y,z+h],[x+w,y+d,z+h],[x,y+d,z+h]],q=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]];return q.map(t=>`facet normal 0 0 0\n outer loop\n${t.map(i=>`  vertex ${v[i].join(' ')}`).join('\n')}\n endloop\nendfacet\n`).join('')}function stl(){const w=s.inner_width,d=s.inner_depth,t=s.wall,h=s.inner_height;return`solid chat3d\n`+box(0,0,0,w+2*t,d+2*t,s.floor)+box(0,0,s.floor,t,d+2*t,h)+box(w+t,0,s.floor,t,d+2*t,h)+box(t,0,s.floor,w,t,h)+box(t,d+t,s.floor,w,t,h)+box(0,d+2*t+8,0,w+2*t,d+2*t,s.lid)+`endsolid chat3d\n`}function dl(n,t){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([t]));a.download=n;a.click()}$('scad').onclick=()=>dl('__FILE__.scad',scad());$('stl').onclick=()=>dl('__FILE__.stl',stl());draw();
</script></body></html>'''.replace("__NAME__",safe).replace("__FILE__",name).replace("__DATA__",data).replace("__LABEL__",label_json).replace("__ENGRAVE__",engrave_note)


def generate(request: dict[str, Any], profile: dict[str, Any], output: Path, name: str) -> dict[str, Any]:
    values=request.get("parameters",{})
    design_kind = str(values.get("design_kind", "enclosure")).strip() or "enclosure"
    if design_kind != "enclosure":
        from . import mechanics

        return mechanics.generate(request, profile, output, name)
    g=geometry(profile,values)
    engrave=_engrave_plan(values,g)
    output.mkdir(parents=True,exist_ok=True)
    files={"project":output/"project.json","scad":output/f"{name}.scad","stl":output/f"{name}.stl","preview_lab":output/"preview-lab.html"}
    files["scad"].write_text(_scad(name,g,engrave),encoding="utf-8");files["stl"].write_text(_stl(name,g,engrave),encoding="ascii");files["preview_lab"].write_text(_lab(name,g,engrave),encoding="utf-8")
    project={"schema_version":"1.0","mode":"chat3d","project_name":name,"board_id":profile["board_id"],"parameters":g,"engrave_text":engrave["text"] if engrave else "","model_generated":"verified","file_opened":"unverified","physical_fit":"unverified"}
    files["project"].write_text(json.dumps(project,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"success":True,"action":"generate","mode":"chat3d","files":{k:str(v) for k,v in files.items()},"model_generated":"verified","file_opened":"unverified","physical_fit":"unverified"}

"""Chat2D V1 laser-cut box generator."""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any


def _num(values: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    value = values.get(key, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not low <= float(value) <= high:
        raise ValueError(f"{key}_out_of_range")
    return float(value)


def geometry(profile: dict[str, Any], parameters: dict[str, Any], thickness: float) -> dict[str, Any]:
    board = profile["outline"]
    width = _num(parameters, "box_width", max(100, float(board["width"]) + 30), 30, 600)
    depth = _num(parameters, "box_depth", max(80, float(board["depth"]) + 30), 30, 600)
    height = _num(parameters, "box_height", 45, 15, 300)
    material = _num(parameters, "material_thickness", thickness, 1, 12)
    joint = _num(parameters, "joint_size", 10, max(3, material * 1.5), 50)
    return {
        "box_width": width, "box_depth": depth, "box_height": height,
        "material_thickness": material,
        "joint_size": joint,
        "board": {
            "id": profile["board_id"], "name": profile["name"],
            "width": float(board["width"]), "depth": float(board["depth"]),
            "x": width / 2, "y": depth / 2, "rotation": 0,
            "holes": profile["mounting"]["holes"],
        },
    }


def _panels(g: dict[str, Any]) -> list[dict[str, float | str]]:
    w, d, h, gap = g["box_width"], g["box_depth"], g["box_height"], g["material_thickness"] * 3
    return [
        {"name": "bottom", "x": gap, "y": gap, "width": w, "depth": d, "phase": 0},
        {"name": "top", "x": w + 3 * gap, "y": gap, "width": w, "depth": d, "phase": 0},
        {"name": "front", "x": gap, "y": d + 3 * gap, "width": w, "depth": h, "phase": 1},
        {"name": "back", "x": w + 3 * gap, "y": d + 3 * gap, "width": w, "depth": h, "phase": 1},
        {"name": "left", "x": 2 * w + 5 * gap, "y": gap, "width": d, "depth": h, "phase": 1},
        {"name": "right", "x": 2 * w + 5 * gap, "y": h + 3 * gap, "width": d, "depth": h, "phase": 1},
    ]


def _finger_edge(start: tuple[float, float], end: tuple[float, float], normal: tuple[float, float], depth: float, target: float, phase: int) -> list[tuple[float, float]]:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    count = max(3, int(round(length / target)))
    if count % 2 == 0:
        count += 1
    ux, uy = dx / length, dy / length
    points = [start]
    for index in range(count):
        a, b = length * index / count, length * (index + 1) / count
        offset = depth if (index + phase) % 2 else -depth
        points.extend([
            (start[0] + ux * a + normal[0] * offset, start[1] + uy * a + normal[1] * offset),
            (start[0] + ux * b + normal[0] * offset, start[1] + uy * b + normal[1] * offset),
        ])
    points.append(end)
    return points[:-1] if points and points[-1] == points[0] else points


def _finger_panel(panel: dict[str, float | str], g: dict[str, Any]) -> list[tuple[float, float]]:
    x, y, w, d = (float(panel[k]) for k in ("x", "y", "width", "depth"))
    phase = int(panel["phase"])
    t, joint = g["material_thickness"] / 2, g["joint_size"]
    corners = [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]
    normals = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    points: list[tuple[float, float]] = []
    for index in range(4):
        edge = _finger_edge(corners[index], corners[(index + 1) % 4], normals[index], t, joint, phase + index)
        points.extend(edge if not points else edge[1:])
    return points


def _svg(name: str, g: dict[str, Any]) -> str:
    b = g["board"]
    panels = _panels(g)
    base_x, base_y = float(panels[0]["x"]), float(panels[0]["y"])
    sheet_width = max(float(p["x"]) + float(p["width"]) for p in panels)
    sheet_depth = max(float(p["y"]) + float(p["depth"]) for p in panels)
    panel_rects = "".join(
        '<polyline points="' + " ".join(f"{x:.3f},{y:.3f}" for x, y in _finger_panel(p, g)) + '"/>'
        for p in panels
    )
    holes = "".join(
        f'<circle cx="{base_x + b["x"] + float(h["x"]):.3f}" cy="{base_y + b["y"] - float(h["y"]):.3f}" r="{float(h["diameter"])/2:.3f}"/>'
        for h in b["holes"]
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{sheet_width}mm" height="{sheet_depth}mm" viewBox="0 0 {sheet_width} {sheet_depth}">
<title>{html.escape(name)}</title><g id="cut-through" fill="none" stroke="#000000" stroke-width="0.2">{panel_rects}{holes}</g>
<g id="line-engrave" fill="none" stroke="#ff0000" stroke-width="0.2"><rect x="{base_x+b["x"]-b["width"]/2}" y="{base_y+b["y"]-b["depth"]/2}" width="{b["width"]}" height="{b["depth"]}"/><text x="{base_x+b["x"]}" y="{base_y+b["y"]}" text-anchor="middle" fill="#ff0000" font-size="4">{html.escape(b["name"])}</text></g>
<g id="shallow-engrave" fill="none" stroke="#ffff00" stroke-width="0.2"/><g id="deep-engrave" fill="none" stroke="#0000ff" stroke-width="0.2"/></svg>'''


def _dxf(g: dict[str, Any]) -> str:
    b = g["board"]
    base = _panels(g)[0]
    base_x, base_y = float(base["x"]), float(base["y"])
    entities = []
    for panel in _panels(g):
        points = _finger_panel(panel, g)
        for a, z in zip(points, points[1:] + points[:1]):
            entities.append(f"0\nLINE\n8\nBLACK_CUT_THROUGH\n10\n{a[0]}\n20\n{a[1]}\n11\n{z[0]}\n21\n{z[1]}\n")
    for hole in b["holes"]:
        entities.append(f"0\nCIRCLE\n8\nBLACK_CUT_THROUGH\n10\n{base_x+b['x']+float(hole['x'])}\n20\n{base_y+b['y']-float(hole['y'])}\n40\n{float(hole['diameter'])/2}\n")
    entities.append(f"0\nTEXT\n8\nRED_LINE_ENGRAVE\n10\n{base_x+b['x']}\n20\n{base_y+b['y']}\n40\n4\n1\n{b['name']}\n")
    return "0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n" + "".join(entities) + "0\nENDSEC\n0\nEOF\n"


def _lab(name: str, g: dict[str, Any]) -> str:
    data = json.dumps(g, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    safe = html.escape(name)
    return r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chat2D 激光盒子实验室</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef1f4;color:#17212b;font-family:Inter,"Microsoft YaHei",sans-serif}.app{display:grid;grid-template-columns:320px 1fr;min-height:100vh}.side{padding:24px;background:#fff;border-right:1px solid #dce2e8}.side h1{margin:.2em 0}.field{margin:17px 0}.field label{display:flex;justify-content:space-between;font-size:14px}.field input{width:100%;margin-top:8px}.buttons{display:grid;grid-template-columns:1fr 1fr;gap:8px}.buttons button,.add{min-height:44px;border:1px solid #c9d2dc;border-radius:10px;background:#fff;cursor:pointer}.add{width:100%;margin:10px 0}.lab{padding:20px}.tabs{display:flex;gap:8px;margin-bottom:12px}.tabs button{min-height:44px;padding:0 18px;border:1px solid #c9d2dc;border-radius:10px;background:#fff}.stage{height:calc(100vh - 100px);min-height:520px;background:#fff;border:1px solid #dce2e8;border-radius:18px;display:grid;place-items:center;overflow:hidden}.canvas{width:90%;height:86%;touch-action:none}.cut{fill:#fcfcfc;stroke:#000;stroke-width:.35}.item{fill:#f5e7e7;stroke:#f00;stroke-width:.35;cursor:move}.hole{fill:#fff;stroke:#000;stroke-width:.35}.label{fill:#f00;font-size:4px;pointer-events:none}.legend{font-size:12px;line-height:1.8}.swatch{display:inline-block;width:12px;height:12px;margin-right:6px;vertical-align:-1px}.three{display:none;perspective:900px}.box{position:relative;width:260px;height:190px;transform-style:preserve-3d;transform:rotateX(-25deg) rotateY(32deg)}.face{position:absolute;border:2px solid #17212b;background:#dab77f88}.front,.back{width:260px;height:120px;left:0;top:35px}.front{transform:translateZ(95px)}.back{transform:rotateY(180deg) translateZ(95px)}.left,.right{width:190px;height:120px;left:35px;top:35px}.left{transform:rotateY(-90deg) translateZ(130px)}.right{transform:rotateY(90deg) translateZ(130px)}.bottom,.top{width:260px;height:190px;left:0;top:0}.bottom{transform:rotateX(90deg) translateZ(-60px)}.top{transform:rotateX(90deg) translateZ(60px);opacity:.35}@media(max-width:780px){.app{grid-template-columns:1fr}.stage{height:560px}.side{border-right:0}}
</style></head><body><main class="app"><aside class="side"><small>CHATCAD · CHAT2D</small><h1>__NAME__</h1><p>参考 LaserMaker 直角盒子逻辑：输入长宽高、榫槽和材料厚度，一键生成六面指接盒。</p><div class="field"><label>宽度 <output id="wv"></output></label><input id="w" type="range" min="30" max="600" step="1"></div><div class="field"><label>深度 <output id="dv"></output></label><input id="d" type="range" min="30" max="600" step="1"></div><div class="field"><label>高度 <output id="hv"></output></label><input id="h" type="range" min="15" max="300" step="1"></div><div class="field"><label>材料厚度 <output id="tv"></output></label><input id="t" type="range" min="1" max="12" step=".5"></div><div class="field"><label>榫槽大小 <output id="jv"></output></label><input id="j" type="range" min="3" max="50" step="1"></div><button class="add" id="add">添加自定义模块</button><div class="buttons"><button id="svg">导出 SVG</button><button id="dxf">导出 DXF</button></div><p class="legend"><span class="swatch" style="background:#000"></span>黑色：切透<br><span class="swatch" style="background:#f00"></span>红色：雕刻<br><span class="swatch" style="background:#ff0;border:1px solid #aaa"></span>黄色：浅雕<br><span class="swatch" style="background:#00f"></span>蓝色：深雕</p><small>功率、速度与切缝补偿仍需按具体设备和材料校准；实体榫槽与孔位需先试切。</small></aside><section class="lab"><nav class="tabs"><button id="flat">二维编辑</button><button id="assembled">三维组装预览</button></nav><div class="stage"><svg class="canvas" id="canvas"></svg><div class="three" id="three"><div class="box" id="box"><div class="face front"></div><div class="face back"></div><div class="face left"></div><div class="face right"></div><div class="face bottom"></div><div class="face top"></div></div></div></div></section></main><script>
const initial=__DATA__,s={...initial,items:[initial.board]},$=id=>document.getElementById(id);let drag=null,rx=-25,ry=32;
for(const [id,key,out] of [['w','box_width','wv'],['d','box_depth','dv'],['h','box_height','hv'],['t','material_thickness','tv'],['j','joint_size','jv']]){$(id).value=s[key];$(id).oninput=()=>{s[key]=Number($(id).value);render();};}
function boxTransform(){const sx=Math.max(.45,Math.min(1.5,s.box_width/100)),sy=Math.max(.45,Math.min(1.5,s.box_height/45)),sz=Math.max(.45,Math.min(1.5,s.box_depth/80));$('box').style.transform=`rotateX(${rx}deg) rotateY(${ry}deg) scale3d(${sx},${sy},${sz})`}function render(){const svg=$('canvas');svg.setAttribute('viewBox',`0 0 ${s.box_width} ${s.box_depth}`);svg.innerHTML=`<rect class="cut" x=".2" y=".2" width="${s.box_width-.4}" height="${s.box_depth-.4}"/>`+s.items.map((m,i)=>`<g data-i="${i}" transform="translate(${m.x-m.width/2} ${m.y-m.depth/2}) rotate(${m.rotation||0} ${m.width/2} ${m.depth/2})"><rect class="item" width="${m.width}" height="${m.depth}"/>${(m.holes||[]).map(h=>`<circle class="hole" cx="${m.width/2+h.x}" cy="${m.depth/2-h.y}" r="${h.diameter/2}"/>`).join('')}<text class="label" x="${m.width/2}" y="${m.depth/2}" text-anchor="middle">${m.name}</text></g>`).join('');for(const [key,out] of [['box_width','wv'],['box_depth','dv'],['box_height','hv'],['material_thickness','tv'],['joint_size','jv']])$(out).value=s[key]+' mm';svg.querySelectorAll('g[data-i]').forEach(g=>g.onpointerdown=e=>{drag={i:Number(g.dataset.i),x:e.clientX,y:e.clientY,ox:s.items[g.dataset.i].x,oy:s.items[g.dataset.i].y};g.setPointerCapture(e.pointerId)});boxTransform()}
$('canvas').onpointermove=e=>{if(!drag)return;const r=$('canvas').getBoundingClientRect(),m=s.items[drag.i];m.x=Math.max(m.width/2,Math.min(s.box_width-m.width/2,drag.ox+(e.clientX-drag.x)*s.box_width/r.width));m.y=Math.max(m.depth/2,Math.min(s.box_depth-m.depth/2,drag.oy+(e.clientY-drag.y)*s.box_depth/r.height));render()};$('canvas').onpointerup=()=>drag=null;
$('add').onclick=()=>{const name=prompt('模块名称','自定义模块');if(!name)return;s.items.push({name,width:30,depth:20,x:s.box_width/2,y:s.box_depth/2,rotation:0,holes:[]});render()};
function panels(){const w=s.box_width,d=s.box_depth,h=s.box_height,g=s.material_thickness*3;return[[g,g,w,d,0],[w+3*g,g,w,d,0],[g,d+3*g,w,h,1],[w+3*g,d+3*g,w,h,1],[2*w+5*g,g,d,h,1],[2*w+5*g,h+3*g,d,h,1]]}function edge(a,b,n,phase){const dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy),count=Math.max(3,Math.round(len/s.joint_size))|1,ux=dx/len,uy=dy/len,out=[a];for(let i=0;i<count;i++){const q=s.material_thickness/2*((i+phase)%2?1:-1),u=len*i/count,v=len*(i+1)/count;out.push([a[0]+ux*u+n[0]*q,a[1]+uy*u+n[1]*q],[a[0]+ux*v+n[0]*q,a[1]+uy*v+n[1]*q])}out.push(b);return out}function finger(p){const[x,y,w,d,phase]=p,c=[[x,y],[x+w,y],[x+w,y+d],[x,y+d]],n=[[0,-1],[1,0],[0,1],[-1,0]],out=[];for(let i=0;i<4;i++){const e=edge(c[i],c[(i+1)%4],n[i],phase+i);out.push(...(out.length?e.slice(1):e))}return out}function svgText(){const ps=panels(),sw=Math.max(...ps.map(p=>p[0]+p[2]+s.material_thickness)),sh=Math.max(...ps.map(p=>p[1]+p[3]+s.material_thickness));let body=ps.map(p=>`<polyline points="${finger(p).map(q=>q.join(',')).join(' ')}"/>`).join('');for(const m of s.items){for(const h of(m.holes||[]))body+=`<circle cx="${m.x+h.x+s.material_thickness*3}" cy="${m.y-h.y+s.material_thickness*3}" r="${h.diameter/2}"/>`;body+=`<text x="${m.x}" y="${m.y}" fill="#ff0000" text-anchor="middle">${m.name.replace(/[<&]/g,'')}</text>`}return`<svg xmlns="http://www.w3.org/2000/svg" width="${sw}mm" height="${sh}mm" viewBox="0 0 ${sw} ${sh}"><g fill="none" stroke="#000000" stroke-width=".2">${body}</g></svg>`}function dxf(){let e='';const line=(a,b,c,d)=>e+=`0\nLINE\n8\nBLACK_CUT_THROUGH\n10\n${a}\n20\n${b}\n11\n${c}\n21\n${d}\n`;for(const p of panels()){const q=finger(p);for(let i=0;i<q.length;i++){const a=q[i],b=q[(i+1)%q.length];line(a[0],a[1],b[0],b[1])}}for(const m of s.items)for(const h of(m.holes||[]))e+=`0\nCIRCLE\n8\nBLACK_CUT_THROUGH\n10\n${m.x+h.x+s.material_thickness*3}\n20\n${m.y-h.y+s.material_thickness*3}\n40\n${h.diameter/2}\n`;return'0\nSECTION\n2\nENTITIES\n'+e+'0\nENDSEC\n0\nEOF\n'}function dl(n,t,type='text/plain'){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([t],{type}));a.download=n;a.click()}$('svg').onclick=()=>dl('__FILE__.svg',svgText(),'image/svg+xml');$('dxf').onclick=()=>dl('__FILE__.dxf',dxf());
$('flat').onclick=()=>{$('canvas').style.display='block';$('three').style.display='none'};$('assembled').onclick=()=>{$('canvas').style.display='none';$('three').style.display='grid'};$('three').onpointerdown=e=>drag={three:true,x:e.clientX,y:e.clientY,rx,ry};$('three').onpointermove=e=>{if(!drag?.three)return;ry=drag.ry+(e.clientX-drag.x)*.4;rx=drag.rx-(e.clientY-drag.y)*.4;boxTransform()};$('three').onpointerup=()=>drag=null;render();
</script></body></html>'''.replace("__NAME__", safe).replace("__FILE__", name).replace("__DATA__", data)


def generate(request: dict[str, Any], profile: dict[str, Any], fabrication: dict[str, Any], output: Path, name: str) -> dict[str, Any]:
    g = geometry(profile, request.get("parameters", {}), float(fabrication["material"]["default_thickness_mm"]))
    output.mkdir(parents=True, exist_ok=True)
    files = {"project": output / "project.json", "svg": output / f"{name}.svg", "dxf": output / f"{name}.dxf", "preview_lab": output / "preview-lab.html"}
    files["svg"].write_text(_svg(name, g), encoding="utf-8")
    files["dxf"].write_text(_dxf(g), encoding="utf-8")
    files["preview_lab"].write_text(_lab(name, g), encoding="utf-8")
    project = {"schema_version": "1.0", "mode": "chat2d", "project_name": name, "board_id": profile["board_id"], "parameters": g, "layers": fabrication["equipment"]["layer_rules"], "model_generated": "verified", "file_opened": "unverified", "physical_fit": "unverified"}
    files["project"].write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"success": True, "action": "generate", "mode": "chat2d", "files": {k: str(v) for k, v in files.items()}, "model_generated": "verified", "file_opened": "unverified", "physical_fit": "unverified"}

from __future__ import annotations

import argparse
import html
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .directions import DesignDirection, suggest_directions


@dataclass(frozen=True)
class WebProjectRequest:
    kind: str
    title: str
    prompt: str
    primary_label: str
    direction_id: str


@dataclass(frozen=True)
class GeneratedWebProject:
    path: Path
    direction_id: str
    evidence: dict[str, str]


def _direction_for(request: WebProjectRequest) -> DesignDirection:
    for direction in suggest_directions(request.kind):
        if direction.id == request.direction_id:
            return direction
    raise ValueError(
        f"direction {request.direction_id!r} is not available for kind {request.kind!r}"
    )


def _render(request: WebProjectRequest, direction: DesignDirection) -> str:
    title = html.escape(request.title, quote=True)
    prompt = html.escape(request.prompt, quote=True)
    label = html.escape(request.primary_label, quote=True)
    mode_note = (
        "本页只演示浏览器交互，不代表任何硬件已经连接。"
        if request.kind == "hardware-interface"
        else "每次轻触都会留下一个清楚、可撤销的课堂信号。"
    )
    paper, ink, accent, glow = direction.palette
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ --paper:{paper}; --ink:{ink}; --accent:{accent}; --glow:{glow}; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; color:var(--ink); background:
      radial-gradient(circle at 14% 8%, color-mix(in srgb,var(--glow) 42%,transparent), transparent 28rem),
      repeating-linear-gradient(104deg,transparent 0 19px,color-mix(in srgb,var(--ink) 4%,transparent) 20px),var(--paper);
      font-family:"Avenir Next","Trebuchet MS",sans-serif; }}
    main {{ width:min(1080px,100%); min-height:100vh; margin:auto; padding:clamp(22px,5vw,72px); display:grid;
      grid-template-columns:minmax(0,1.25fr) minmax(250px,.75fr); gap:clamp(28px,6vw,88px); align-items:center; }}
    .eyebrow {{ display:inline-flex; align-items:center; gap:10px; font-size:.78rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }}
    .eyebrow::before {{ content:""; width:34px; height:4px; background:var(--accent); transform:rotate(-4deg); }}
    h1 {{ max-width:9ch; margin:.35em 0 .28em; font-family:"Iowan Old Style","Palatino Linotype",Georgia,serif;
      font-size:clamp(3.4rem,10vw,8.8rem); line-height:.82; letter-spacing:-.065em; text-wrap:balance; }}
    .prompt {{ max-width:34rem; font-size:clamp(1.15rem,2.2vw,1.65rem); line-height:1.45; }}
    .card {{ position:relative; padding:clamp(24px,4vw,44px); border:2px solid var(--ink); border-radius:30px 8px 30px 8px;
      background:color-mix(in srgb,var(--paper) 82%,white); box-shadow:14px 16px 0 var(--ink); transform:rotate(1.2deg); }}
    .count {{ display:block; font-family:"Iowan Old Style",Georgia,serif; font-size:clamp(5rem,15vw,9rem); line-height:.82; color:var(--accent); }}
    .caption {{ margin:12px 0 24px; font-weight:800; }}
    button {{ width:100%; min-height:56px; padding:14px 18px; border:2px solid var(--ink); border-radius:999px; color:var(--paper);
      background:var(--ink); font:inherit; font-weight:900; cursor:pointer; box-shadow:0 7px 0 var(--accent); transition:transform .16s,box-shadow .16s; }}
    button:hover {{ transform:translateY(-2px); box-shadow:0 9px 0 var(--accent); }}
    button:active {{ transform:translateY(5px); box-shadow:0 2px 0 var(--accent); }}
    button:focus-visible {{ outline:4px solid var(--glow); outline-offset:5px; }}
    .status {{ min-height:1.5em; margin:22px 0 0; font-weight:750; }}
    .note {{ grid-column:1/-1; margin:0; padding-top:20px; border-top:1px solid color-mix(in srgb,var(--ink) 28%,transparent); font-size:.86rem; }}
    [data-state="active"] .count {{ animation:stamp .34s ease-out; }}
    @keyframes stamp {{ 45% {{ transform:scale(1.12) rotate(-3deg); }} }}
    @media (max-width:720px) {{ main {{ grid-template-columns:1fr; align-content:center; }} h1 {{ font-size:clamp(3.7rem,20vw,6.3rem); }} .card {{ transform:none; }} }}
    @media (prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ animation:none!important; transition:none!important; }} }}
  </style>
</head>
<body>
  <main>
    <section>
      <span class="eyebrow">ChatWeb · {html.escape(direction.name)}</span>
      <h1>{title}</h1>
      <p class="prompt">{prompt}</p>
    </section>
    <section class="card" data-state="ready" aria-label="互动区">
      <output class="count" id="count">0</output>
      <p class="caption">条课堂信号已经收到</p>
      <button id="primary" type="button">{label}</button>
      <p class="status" id="status" aria-live="polite">页面已准备好</p>
    </section>
    <p class="note">{html.escape(mode_note)}</p>
  </main>
  <script>
    const card=document.querySelector('.card');
    const count=document.querySelector('#count');
    const status=document.querySelector('#status');
    document.querySelector('#primary').addEventListener('click',()=>{{
      count.value=String(Number(count.value)+1); card.dataset.state='active';
      status.textContent=`已收到第 ${{count.value}} 条信号`;
      window.setTimeout(()=>{{card.dataset.state='ready';}},360);
    }});
  </script>
</body>
</html>
'''


def generate_single_file(request: WebProjectRequest, output: Path) -> GeneratedWebProject:
    direction = _direction_for(request)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render(request, direction), encoding="utf-8")
    return GeneratedWebProject(
        path=output,
        direction_id=direction.id,
        evidence={
            "generated": "verified",
            "browser_interaction": "unverified",
            "hardware_connectivity": "not_applicable" if request.kind == "classroom-tool" else "unverified",
        },
    )


def _request_from_json(value: str) -> WebProjectRequest:
    payload: dict[str, Any] = json.loads(value)
    return WebProjectRequest(**payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one self-contained ChatWeb HTML file.")
    parser.add_argument("--request-json", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = generate_single_file(_request_from_json(args.request_json), args.output)
    print(json.dumps({**asdict(result), "path": str(result.path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

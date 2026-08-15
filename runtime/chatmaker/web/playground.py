from __future__ import annotations

import argparse
import html
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .directions import DesignDirection, suggest_directions, validate_advanced_flag


@dataclass(frozen=True)
class PlaygroundRequest:
    kind: str
    title: str
    brief: str
    advanced: bool = False


@dataclass(frozen=True)
class GeneratedPlayground:
    path: Path
    direction_ids: tuple[str, ...]
    evidence: dict[str, str]


def _direction_card(direction: DesignDirection, index: int) -> str:
    paper, ink, accent, glow = direction.palette
    level = "进阶方向" if direction.advanced else "基础方向"
    return f'''
      <article class="direction-card" data-aesthetic="{html.escape(direction.aesthetic)}"
        style="--card-paper:{paper};--card-ink:{ink};--card-accent:{accent};--card-glow:{glow}">
        <div class="specimen" aria-hidden="true">
          <span class="index">0{index}</span>
          <span class="signal"></span>
          <span class="specimen-name">{html.escape(direction.name)}</span>
        </div>
        <div class="direction-copy">
          <p class="level">{level}</p>
          <h2>{html.escape(direction.name)}</h2>
          <p class="feeling">{html.escape(direction.feeling)}</p>
          <dl>
            <div><dt>主要互动</dt><dd>{html.escape(direction.primary_interaction)}</dd></div>
            <div><dt>适合场景</dt><dd>{html.escape(direction.best_for)}</dd></div>
            <div><dt>取舍</dt><dd>{html.escape(direction.tradeoff)}</dd></div>
          </dl>
          <button class="choose-direction" type="button" data-direction-id="{html.escape(direction.id)}"
            aria-pressed="false">选择这个方向</button>
        </div>
      </article>'''


def _render(request: PlaygroundRequest, directions: list[DesignDirection]) -> str:
    title = html.escape(request.title, quote=True)
    brief = html.escape(request.brief, quote=True)
    hardware_note = (
        '    <aside class="simulation-note" role="note"><strong>模拟比较</strong>'
        "这里只比较界面与浏览器操作，不代表任何硬件已经连接。</aside>\n"
        if request.kind == "hardware-interface"
        else ""
    )
    cards = "".join(
        _direction_card(direction, index)
        for index, direction in enumerate(directions, start=1)
    )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ --paper:#eee9dc; --ink:#171a17; --accent:#d84b32; --line:#bbb4a4; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-width:0; color:var(--ink); background:
      linear-gradient(90deg,transparent 0 49.7%,rgba(23,26,23,.045) 49.8% 50.2%,transparent 50.3%),
      repeating-linear-gradient(0deg,transparent 0 31px,rgba(23,26,23,.035) 32px),var(--paper);
      font-family:"Avenir Next","Trebuchet MS",sans-serif; }}
    main {{ width:min(1180px,100%); margin:auto; padding:clamp(22px,5vw,72px); }}
    header {{ display:grid; grid-template-columns:minmax(0,1.15fr) minmax(220px,.55fr); gap:32px;
      align-items:end; padding:12px 0 clamp(38px,7vw,88px); border-top:8px solid var(--ink); }}
    .kicker,.level {{ margin:0 0 10px; font-size:.72rem; font-weight:900; letter-spacing:.16em; text-transform:uppercase; }}
    .kicker {{ color:var(--accent); }}
    h1 {{ max-width:12ch; margin:0; font-family:"Bodoni 72","Bodoni MT",Didot,serif;
      font-size:clamp(3.3rem,9vw,7.8rem); line-height:.82; letter-spacing:-.055em; }}
    .brief {{ margin:0; padding:20px 0 0; border-top:1px solid var(--line); font-size:clamp(1rem,2vw,1.3rem); line-height:1.55; }}
    .simulation-note {{ margin:-34px 0 34px; padding:14px 18px; border:2px solid #8a4c1f;
      color:#4f2c15; background:#f5dcae; line-height:1.5; }}
    .simulation-note strong {{ margin-right:10px; text-transform:uppercase; letter-spacing:.1em; }}
    .directions {{ display:grid; gap:clamp(22px,4vw,46px); }}
    .direction-card {{ display:grid; grid-template-columns:minmax(230px,.8fr) minmax(0,1.2fr); min-width:0;
      overflow:hidden; border:2px solid var(--card-ink); color:var(--card-ink); background:var(--card-paper);
      box-shadow:10px 12px 0 color-mix(in srgb,var(--card-ink) 80%,transparent); }}
    .specimen {{ position:relative; min-height:330px; overflow:hidden; padding:24px; background:var(--card-ink); color:var(--card-paper); }}
    .index {{ position:absolute; top:18px; left:20px; z-index:2; font-weight:900; letter-spacing:.16em; }}
    .signal {{ position:absolute; inset:28% 13% 18%; background:var(--card-accent); }}
    .specimen-name {{ position:absolute; right:20px; bottom:18px; left:20px; z-index:2;
      font-size:clamp(2rem,5vw,4.7rem); font-weight:900; line-height:.86; letter-spacing:-.04em; }}
    .direction-copy {{ min-width:0; padding:clamp(24px,4vw,48px); }}
    .level {{ color:var(--card-accent); }}
    h2 {{ margin:0 0 12px; font-family:"Iowan Old Style","Palatino Linotype",Georgia,serif;
      font-size:clamp(2rem,4.4vw,4.1rem); line-height:.95; }}
    .feeling {{ max-width:39rem; margin:0 0 24px; font-size:clamp(1.05rem,2vw,1.35rem); line-height:1.5; }}
    dl {{ display:grid; gap:0; margin:0 0 26px; border-top:1px solid color-mix(in srgb,var(--card-ink) 30%,transparent); }}
    dl div {{ display:grid; grid-template-columns:6.2rem 1fr; gap:14px; padding:13px 0;
      border-bottom:1px solid color-mix(in srgb,var(--card-ink) 20%,transparent); }}
    dt {{ font-weight:900; }} dd {{ margin:0; line-height:1.45; }}
    button {{ min-height:48px; padding:11px 19px; border:2px solid var(--card-ink); color:var(--card-paper);
      background:var(--card-ink); font:900 1rem/1 "Avenir Next","Trebuchet MS",sans-serif; cursor:pointer;
      transition:transform .18s ease,box-shadow .18s ease; }}
    button:hover {{ transform:translateY(-3px); box-shadow:0 6px 0 var(--card-accent); }}
    button[aria-pressed="true"] {{ color:var(--card-ink); background:var(--card-glow); box-shadow:0 6px 0 var(--card-accent); }}
    button:focus-visible {{ outline:4px solid var(--card-accent); outline-offset:4px; }}
    .selection {{ position:sticky; bottom:12px; z-index:5; min-height:48px; margin:34px auto 0; padding:13px 18px;
      border:2px solid var(--ink); color:var(--paper); background:var(--ink); box-shadow:7px 7px 0 var(--accent);
      font-weight:850; text-align:center; }}

    [data-aesthetic="editorial-signal"] .signal {{ transform:rotate(-8deg); clip-path:polygon(0 8%,100% 0,88% 100%,7% 87%); }}
    [data-aesthetic="editorial-signal"] .specimen::after {{ content:""; position:absolute; inset:16% 18%; border:3px solid var(--card-glow); transform:rotate(6deg); }}
    [data-aesthetic="tactile-spark"] {{ border-radius:34px 8px 34px 8px; }}
    [data-aesthetic="tactile-spark"] .specimen {{ background:var(--card-glow); color:var(--card-ink); }}
    [data-aesthetic="tactile-spark"] .signal {{ inset:24% 16%; border:8px solid var(--card-ink); border-radius:50%; box-shadow:12px 14px 0 var(--card-accent); }}
    [data-aesthetic="quiet-focus"] {{ box-shadow:0 18px 50px rgba(23,34,29,.13); }}
    [data-aesthetic="quiet-focus"] .specimen {{ background:var(--card-paper); color:var(--card-ink); }}
    [data-aesthetic="quiet-focus"] .signal {{ inset:30% 27%; border-radius:50%; opacity:.72; }}
    [data-aesthetic="field-notebook"] {{ transform:rotate(-.35deg); border-style:dashed; }}
    [data-aesthetic="field-notebook"] .specimen {{ color:var(--card-ink); background:
      radial-gradient(circle,var(--card-glow) 1.5px,transparent 1.7px) 0 0/18px 18px,var(--card-paper); }}
    [data-aesthetic="field-notebook"] .signal {{ inset:22% 12% 24%; border-radius:52% 34% 48% 25%; transform:rotate(9deg); opacity:.88; }}
    [data-aesthetic="field-notebook"] .specimen-name {{ font-family:"American Typewriter","Courier New",monospace; transform:rotate(-3deg); }}
    [data-aesthetic="stage-cue"] {{ border-color:var(--card-glow); box-shadow:10px 12px 0 var(--card-accent); }}
    [data-aesthetic="stage-cue"] .specimen {{ background:var(--card-ink); }}
    [data-aesthetic="stage-cue"] .signal {{ inset:0 29%; transform:skew(-14deg); background:linear-gradient(var(--card-glow),var(--card-accent)); }}
    [data-aesthetic="stage-cue"] .specimen-name {{ font-family:"Bodoni 72","Bodoni MT",Didot,serif; text-transform:uppercase; }}
    [data-aesthetic="device-console"] .specimen {{ background:repeating-linear-gradient(90deg,#101714 0 2px,#17221d 2px 34px); }}
    [data-aesthetic="device-console"] .signal {{ inset:27% 12%; border:2px solid var(--card-glow); background:transparent; box-shadow:inset 0 0 0 18px var(--card-accent); }}
    [data-aesthetic="tactile-control"] {{ border-radius:46px; }}
    [data-aesthetic="tactile-control"] .signal {{ inset:23% 18%; border:9px solid var(--card-paper); border-radius:999px; box-shadow:0 15px 0 #090b0e; }}
    [data-aesthetic="field-monitor"] .signal {{ clip-path:polygon(0 72%,18% 55%,34% 66%,51% 19%,68% 42%,84% 30%,100% 8%,100% 100%,0 100%); }}
    [data-aesthetic="flight-deck"] .specimen {{ background:repeating-linear-gradient(0deg,#111817 0 28px,#27302c 29px); }}
    [data-aesthetic="flight-deck"] .signal {{ inset:25% 11%; border:3px solid var(--card-accent); background:transparent; clip-path:polygon(0 0,88% 0,100% 22%,100% 100%,12% 100%,0 78%); }}
    [data-aesthetic="flight-deck"] .signal::after {{ content:"ARM"; position:absolute; right:12px; bottom:10px; color:var(--card-accent); font-weight:900; letter-spacing:.2em; }}
    [data-aesthetic="botanical-lab"] {{ border-radius:70px 8px 70px 8px; }}
    [data-aesthetic="botanical-lab"] .specimen {{ color:var(--card-ink); background:var(--card-paper); }}
    [data-aesthetic="botanical-lab"] .signal {{ inset:18% 17%; border:16px double var(--card-glow); border-radius:48% 52% 42% 58%; background:var(--card-accent); transform:rotate(-12deg); }}
    [data-aesthetic="botanical-lab"] .specimen-name {{ font-family:"Hoefler Text","Palatino Linotype",Georgia,serif; font-style:italic; }}

    @media (max-width:700px) {{
      main {{ padding:18px 16px 30px; overflow:hidden; }}
      header {{ grid-template-columns:1fr; gap:24px; padding-bottom:42px; }}
      h1 {{ font-size:clamp(3.2rem,17vw,5.6rem); }}
      .simulation-note {{ margin:-18px 0 26px; }}
      .direction-card {{ grid-template-columns:1fr; transform:none; box-shadow:6px 7px 0 color-mix(in srgb,var(--card-ink) 76%,transparent); }}
      .specimen {{ min-height:230px; }}
      dl div {{ grid-template-columns:1fr; gap:5px; }}
      .choose-direction {{ width:100%; }}
    }}
    @media (prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ animation:none!important; transition:none!important; scroll-behavior:auto!important; }} }}
  </style>
</head>
<body>
  <main data-kind="{html.escape(request.kind)}">
    <header>
      <div><p class="kicker">ChatWeb · Advanced playground</p><h1>{title}</h1></div>
      <p class="brief">{brief}</p>
    </header>
{hardware_note}    <section class="directions" aria-label="扩展设计方向">{cards}
    </section>
    <p class="selection" id="selection-status" role="status" aria-live="polite">还没有选择方向</p>
  </main>
  <script>
    const buttons=[...document.querySelectorAll('.choose-direction')];
    const status=document.querySelector('#selection-status');
    buttons.forEach((button)=>button.addEventListener('click',()=>{{
      buttons.forEach((candidate)=>candidate.setAttribute('aria-pressed',String(candidate===button)));
      const name=button.closest('.direction-card').querySelector('h2').textContent;
      status.textContent=`已选择：${{name}}。下一步会先生成这一版。`;
    }}));
  </script>
</body>
</html>
'''


def generate_playground(request: PlaygroundRequest, output: Path) -> GeneratedPlayground:
    advanced = validate_advanced_flag(request.advanced)
    if not advanced:
        raise ValueError("playground requires explicit advanced opt-in")
    directions = suggest_directions(request.kind, advanced=True)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render(request, directions), encoding="utf-8")
    return GeneratedPlayground(
        path=output,
        direction_ids=tuple(direction.id for direction in directions),
        evidence={
            "generated": "verified",
            "browser_interaction": "unverified",
            "hardware_connectivity": (
                "not_applicable" if request.kind == "classroom-tool" else "unverified"
            ),
            "physical_effect": (
                "not_applicable" if request.kind == "classroom-tool" else "unverified"
            ),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an opt-in advanced ChatWeb direction playground."
    )
    parser.add_argument("--kind", choices=("classroom-tool", "hardware-interface"), required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--advanced",
        action="store_true",
        required=True,
        help="Required explicit opt-in for the expanded playground.",
    )
    args = parser.parse_args()
    result = generate_playground(
        PlaygroundRequest(
            kind=args.kind,
            title=args.title,
            brief=args.brief,
            advanced=args.advanced,
        ),
        args.output,
    )
    print(json.dumps({**asdict(result), "path": str(result.path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

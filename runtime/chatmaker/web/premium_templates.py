from __future__ import annotations

import html

from .directions import DesignDirection


def render_spatial_glass(
    *, title: str, prompt: str, label: str, direction: DesignDirection
) -> str:
    safe_title = html.escape(title, quote=True)
    safe_prompt = html.escape(prompt, quote=True)
    safe_label = html.escape(label, quote=True)
    safe_direction = html.escape(direction.name, quote=True)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{ color-scheme:dark; --ink:#f7f8ff; --muted:#b9bfd4; --violet:#8b7cff; --cyan:#65e8ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; overflow-x:hidden; color:var(--ink); background:#080a15;
      font-family:Inter,"SF Pro Display","PingFang SC",system-ui,sans-serif; }}
    body::before {{ content:""; position:fixed; inset:-20%; z-index:-2; background:
      radial-gradient(circle at 18% 18%,#7657ff 0 8%,transparent 30%),
      radial-gradient(circle at 84% 24%,#14c7e8 0 7%,transparent 28%),
      radial-gradient(circle at 58% 90%,#e55ed0 0 6%,transparent 32%); filter:blur(24px); animation:drift 11s ease-in-out infinite alternate; }}
    body::after {{ content:""; position:fixed; inset:0; z-index:-1; opacity:.32; background-image:
      linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);
      background-size:42px 42px; mask-image:linear-gradient(to bottom,black,transparent 80%); }}
    main {{ width:min(1120px,100%); min-height:100vh; margin:auto; padding:clamp(22px,6vw,76px); display:grid;
      grid-template-columns:minmax(0,1.1fr) minmax(280px,.8fr); gap:clamp(30px,7vw,90px); align-items:center; }}
    .intro {{ animation:rise .72s cubic-bezier(.2,.8,.2,1) both; }}
    .eyebrow {{ display:inline-flex; gap:10px; align-items:center; margin:0; color:#dfe2ff; font-size:.76rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }}
    .eyebrow::before {{ content:""; width:8px; height:8px; border-radius:50%; background:var(--cyan); box-shadow:0 0 20px var(--cyan); }}
    h1 {{ max-width:9ch; margin:.28em 0 .22em; font-size:clamp(3.7rem,10vw,8.5rem); line-height:.84; letter-spacing:-.075em; text-wrap:balance; }}
    .prompt {{ max-width:34rem; color:var(--muted); font-size:clamp(1.08rem,2vw,1.45rem); line-height:1.6; }}
    .card {{ position:relative; overflow:hidden; padding:clamp(26px,4vw,46px); border:1px solid rgba(255,255,255,.22); border-radius:34px;
      background:linear-gradient(145deg,rgba(255,255,255,.18),rgba(255,255,255,.055)); box-shadow:0 30px 90px rgba(0,0,0,.36),inset 0 1px rgba(255,255,255,.35);
      backdrop-filter:blur(26px) saturate(145%); -webkit-backdrop-filter:blur(26px) saturate(145%); animation:rise .72s .12s cubic-bezier(.2,.8,.2,1) both; }}
    .card::before {{ content:""; position:absolute; width:180px; height:180px; top:-95px; right:-70px; border-radius:50%; background:rgba(101,232,255,.24); filter:blur(5px); }}
    .count-wrap {{ position:relative; display:grid; place-items:center; width:min(230px,62vw); aspect-ratio:1; margin:0 auto 24px; }}
    .count-wrap::before {{ content:""; position:absolute; inset:0; border:1px solid rgba(255,255,255,.25); border-radius:50%; box-shadow:inset 0 0 48px rgba(139,124,255,.18),0 0 44px rgba(101,232,255,.12); }}
    .count {{ position:relative; font-size:clamp(5.5rem,14vw,9rem); font-weight:740; line-height:1; letter-spacing:-.08em; text-shadow:0 0 34px rgba(139,124,255,.45); }}
    .caption {{ margin:0 0 20px; color:var(--muted); font-weight:700; text-align:center; }}
    button {{ width:100%; min-height:58px; padding:14px 20px; border:1px solid rgba(255,255,255,.32); border-radius:18px; color:#090b17;
      background:linear-gradient(135deg,#fff,#dfe7ff); box-shadow:0 12px 34px rgba(101,232,255,.18); font:800 1rem/1.2 inherit; cursor:pointer;
      transition:transform .18s cubic-bezier(.2,.8,.2,1),box-shadow .18s; touch-action:manipulation; }}
    button:hover {{ transform:translateY(-2px); box-shadow:0 16px 42px rgba(101,232,255,.28); }}
    button:active {{ transform:scale(.965); }}
    button:focus-visible {{ outline:4px solid var(--cyan); outline-offset:4px; }}
    .status {{ min-height:1.5em; margin:20px 0 0; color:#dfe2ff; font-weight:700; text-align:center; }}
    .note {{ grid-column:1/-1; margin:0; color:#8f96ac; font-size:.82rem; text-align:center; }}
    [data-state="active"] .count-wrap {{ animation:halo .58s ease-out; }}
    [data-state="active"] .count {{ animation:count-pop .42s cubic-bezier(.15,.9,.25,1.3); }}
    .spark {{ position:absolute; left:50%; top:50%; width:7px; height:7px; border-radius:50%; background:var(--cyan); pointer-events:none; animation:spark .65s ease-out forwards; }}
    @keyframes drift {{ to {{ transform:translate3d(3%,2%,0) scale(1.06); }} }}
    @keyframes rise {{ from {{ opacity:0; transform:translateY(24px) scale(.985); }} }}
    @keyframes halo {{ 50% {{ transform:scale(1.035); filter:drop-shadow(0 0 25px var(--violet)); }} }}
    @keyframes count-pop {{ 45% {{ transform:scale(1.14); color:var(--cyan); }} }}
    @keyframes spark {{ to {{ opacity:0; transform:translate(var(--x),var(--y)) scale(0); }} }}
    @media (max-width:760px) {{ main {{ grid-template-columns:1fr; align-content:center; }} h1 {{ font-size:clamp(3.6rem,19vw,6.5rem); }} .card {{ border-radius:28px; }} }}
    @media (prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ animation:none!important; transition:none!important; }} }}
  </style>
</head>
<body>
  <main data-template="spatial-glass">
    <section class="intro">
      <p class="eyebrow">ChatWeb · {safe_direction}</p>
      <h1>{safe_title}</h1>
      <p class="prompt">{safe_prompt}</p>
    </section>
    <section class="card" data-state="ready" data-mode="classroom" aria-label="互动投票区">
      <div class="count-wrap" id="visual"><output class="count" id="count">0</output></div>
      <p class="caption">条课堂信号已经收到</p>
      <button id="primary" type="button">{safe_label}</button>
      <p class="status" id="status" aria-live="polite">页面已准备好</p>
    </section>
    <p class="note">每次轻触都会留下一个清楚的课堂信号。</p>
  </main>
  <script>
    const card=document.querySelector('.card'); const count=document.querySelector('#count');
    const status=document.querySelector('#status'); const visual=document.querySelector('#visual');
    document.querySelector('#primary').addEventListener('click',()=>{{
      count.value=String(Number(count.value)+1); card.dataset.state='active'; status.textContent=`已收到第 ${{count.value}} 条信号`;
      if(!matchMedia('(prefers-reduced-motion: reduce)').matches){{
        for(let i=0;i<8;i+=1){{ const spark=document.createElement('i'); spark.className='spark';
          const angle=(Math.PI*2*i)/8; spark.style.setProperty('--x',`${{Math.cos(angle)*92}}px`); spark.style.setProperty('--y',`${{Math.sin(angle)*92}}px`);
          visual.append(spark); window.setTimeout(()=>spark.remove(),700); }}
      }}
      window.setTimeout(()=>{{ card.dataset.state='ready'; }},650);
    }});
  </script>
</body>
</html>
'''


def render_mission_console(
    *, title: str, prompt: str, label: str, direction: DesignDirection
) -> str:
    safe_title = html.escape(title, quote=True)
    safe_prompt = html.escape(prompt, quote=True)
    safe_label = html.escape(label, quote=True)
    safe_direction = html.escape(direction.name, quote=True)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{ color-scheme:dark; --cyan:#57f6da; --amber:#ffb74d; --panel:#111a22; --line:#263947; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; color:#edf7f5; background:#070d12; font-family:"IBM Plex Mono","SFMono-Regular",Consolas,monospace; }}
    body::before {{ content:""; position:fixed; inset:0; pointer-events:none; opacity:.2; background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px); background-size:32px 32px; }}
    main {{ position:relative; width:min(1180px,100%); min-height:100vh; margin:auto; padding:clamp(20px,4vw,54px); display:grid; align-content:center; gap:22px; }}
    header {{ display:grid; grid-template-columns:1fr auto; gap:20px; align-items:end; }}
    .eyebrow {{ margin:0 0 9px; color:var(--cyan); font-size:.72rem; font-weight:900; letter-spacing:.18em; text-transform:uppercase; }}
    h1 {{ margin:0; font-family:Inter,"PingFang SC",system-ui,sans-serif; font-size:clamp(2.8rem,7vw,6.5rem); line-height:.9; letter-spacing:-.06em; }}
    .prompt {{ max-width:44rem; margin:14px 0 0; color:#91a8b5; line-height:1.55; }}
    .signal {{ display:flex; align-items:center; gap:10px; min-height:44px; padding:10px 15px; border:1px solid var(--line); border-radius:999px; background:rgba(11,21,28,.88); font-size:.78rem; font-weight:800; }}
    .signal::before {{ content:""; width:9px; height:9px; border-radius:50%; background:#6c7f88; box-shadow:0 0 0 5px rgba(108,127,136,.12); }}
    .console {{ position:relative; overflow:hidden; display:grid; grid-template-columns:minmax(0,1.15fr) minmax(250px,.85fr); border:1px solid #304654; border-radius:24px; background:linear-gradient(145deg,rgba(20,32,41,.97),rgba(8,16,22,.98)); box-shadow:0 28px 80px rgba(0,0,0,.48); }}
    .console::after {{ content:""; position:absolute; inset:0; pointer-events:none; background:linear-gradient(transparent 50%,rgba(87,246,218,.025) 50%); background-size:100% 4px; }}
    .scope {{ min-height:330px; padding:clamp(22px,4vw,40px); border-right:1px solid var(--line); }}
    .scope-head {{ display:flex; justify-content:space-between; color:#76909c; font-size:.72rem; letter-spacing:.12em; }}
    .wave {{ position:relative; height:190px; margin-top:25px; overflow:hidden; border-block:1px solid var(--line); background:repeating-linear-gradient(90deg,transparent 0 39px,rgba(87,246,218,.08) 40px); }}
    .wave svg {{ width:100%; height:100%; overflow:visible; }}
    .wave path {{ fill:none; stroke:#627681; stroke-width:3; vector-effect:non-scaling-stroke; transition:stroke .3s,filter .3s; }}
    .readings {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:18px; }}
    .reading {{ padding:12px; border:1px solid var(--line); border-radius:12px; color:#8199a4; font-size:.7rem; }}
    .reading strong {{ display:block; margin-top:5px; color:#eaf4f1; font-size:1.15rem; }}
    .control {{ display:grid; align-content:center; gap:18px; padding:clamp(24px,4vw,42px); }}
    .count {{ font-family:Inter,system-ui,sans-serif; font-size:clamp(4.7rem,11vw,8rem); font-weight:800; line-height:.8; letter-spacing:-.08em; color:#778b95; }}
    .caption {{ margin:0; color:#8ba0aa; font-size:.78rem; font-weight:800; text-transform:uppercase; letter-spacing:.12em; }}
    button {{ min-height:58px; padding:14px 18px; border:1px solid var(--cyan); border-radius:10px; color:var(--cyan); background:rgba(87,246,218,.07); font:900 .9rem/1.2 inherit; cursor:pointer; text-transform:uppercase; letter-spacing:.06em; transition:transform .15s,background .2s,box-shadow .2s; touch-action:manipulation; }}
    button:hover {{ background:rgba(87,246,218,.13); box-shadow:0 0 25px rgba(87,246,218,.13); }} button:active {{ transform:scale(.97); }}
    button:focus-visible {{ outline:4px solid var(--amber); outline-offset:4px; }}
    .status {{ min-height:2.5em; margin:0; color:#a5b7bf; font-size:.8rem; line-height:1.5; }}
    .note {{ margin:0; color:#70848e; font-size:.76rem; }}
    [data-state="connected"] .signal::before {{ background:var(--cyan); box-shadow:0 0 18px var(--cyan),0 0 0 5px rgba(87,246,218,.12); }}
    [data-state="connected"] .wave path {{ stroke:var(--cyan); filter:drop-shadow(0 0 8px rgba(87,246,218,.55)); animation:scan 2.2s linear infinite; }}
    [data-state="connected"] .count {{ color:var(--cyan); text-shadow:0 0 24px rgba(87,246,218,.28); animation:lock .45s ease-out; }}
    [data-state="connected"] button {{ color:#07110f; background:var(--cyan); }}
    @keyframes scan {{ 50% {{ transform:translateY(-5px); }} }} @keyframes lock {{ 50% {{ transform:scale(1.06); }} }}
    @media (max-width:760px) {{ header,.console {{ grid-template-columns:1fr; }} .signal {{ justify-self:start; }} .scope {{ min-height:270px; border-right:0; border-bottom:1px solid var(--line); }} .wave {{ height:130px; }} }}
    @media (prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ animation:none!important; transition:none!important; }} }}
  </style>
</head>
<body>
  <main data-template="mission-console">
    <header><div><p class="eyebrow">ChatWeb · {safe_direction}</p><h1>{safe_title}</h1><p class="prompt">{safe_prompt}</p></div><div class="signal">SIMULATION LINK</div></header>
    <section class="console card" data-state="disconnected" data-mode="simulation" aria-label="模拟设备控制台">
      <div class="scope"><div class="scope-head"><span>LIVE SIGNAL</span><span>CH-01</span></div>
        <div class="wave" aria-hidden="true"><svg viewBox="0 0 700 190" preserveAspectRatio="none"><path d="M0 115 C70 115 75 72 135 72 S205 132 270 108 S345 52 410 78 S480 142 545 104 S630 62 700 88"/></svg></div>
        <div class="readings"><div class="reading">MODE<strong>SIM</strong></div><div class="reading">SIGNAL<strong id="signal">--</strong></div><div class="reading">LATENCY<strong>LOCAL</strong></div></div>
      </div>
      <div class="control"><output class="count" id="count">0</output><p class="caption">connected channels</p><button id="primary" type="button">{safe_label}</button><p class="status" id="status" aria-live="polite">模拟设备未连接</p></div>
    </section>
    <p class="note">本页只演示浏览器交互，不代表任何硬件已经连接。</p>
  </main>
  <script>
    const card=document.querySelector('.card'); const count=document.querySelector('#count'); const signal=document.querySelector('#signal');
    const status=document.querySelector('#status'); const primary=document.querySelector('#primary');
    primary.addEventListener('click',()=>{{ const connected=card.dataset.state==='connected'; card.dataset.state=connected?'disconnected':'connected';
      count.value=connected?'0':'1'; signal.textContent=connected?'--':'OK'; status.textContent=connected?'模拟设备未连接':'模拟设备已连接（仅浏览器演示）';
      primary.textContent=connected?'连接模拟设备':'断开模拟设备'; }});
  </script>
</body>
</html>
'''

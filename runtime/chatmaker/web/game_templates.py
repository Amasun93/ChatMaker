from __future__ import annotations

import html

from .directions import DesignDirection


_GAME_SHELL = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <style>
    :root { --paper:__PAPER__; --ink:__INK__; --accent:__ACCENT__; --glow:__GLOW__; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; color:var(--ink); background:var(--paper);
      font-family:"Avenir Next","Trebuchet MS",system-ui,sans-serif; }
    main { width:min(1040px,100%); margin:auto; padding:clamp(18px,4vw,48px); }
    header { display:grid; grid-template-columns:1fr auto; gap:18px; align-items:end; margin-bottom:22px; }
    .eyebrow { margin:0 0 8px; color:var(--accent); font-size:.76rem; font-weight:900; letter-spacing:.15em; text-transform:uppercase; }
    h1 { margin:0; font-size:clamp(2.5rem,7vw,5.7rem); line-height:.9; letter-spacing:-.055em; }
    .prompt { max-width:44rem; margin:14px 0 0; font-size:clamp(1rem,2vw,1.25rem); line-height:1.55; }
    .hud { display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end; }
    .hud span { min-width:92px; padding:10px 14px; border:2px solid var(--ink); border-radius:999px; background:white; font-weight:900; text-align:center; }
    .game-stage { position:relative; min-height:420px; overflow:hidden; border:3px solid var(--ink); border-radius:26px;
      background:color-mix(in srgb,var(--paper) 55%,white); box-shadow:10px 12px 0 var(--ink); touch-action:none; }
    .game-stage[data-state="ended"] { box-shadow:10px 12px 0 var(--accent); }
    .target { position:absolute; width:74px; height:74px; border:3px solid var(--ink); border-radius:50%; color:var(--ink);
      background:var(--glow); font-size:2rem; cursor:pointer; box-shadow:5px 6px 0 var(--accent); touch-action:manipulation; }
    canvas { display:block; width:100%; height:auto; max-height:420px; background:linear-gradient(#dff6ff,#fff8dc); }
    .touch-controls { position:absolute; right:14px; bottom:14px; left:14px; display:flex; justify-content:space-between; pointer-events:none; }
    .touch-controls button { width:76px; pointer-events:auto; }
    .puzzle-board { display:grid; grid-template-columns:1fr 1.2fr; gap:20px; min-height:414px; padding:clamp(18px,4vw,38px); }
    .pieces,.zones { display:grid; gap:12px; align-content:center; }
    .piece,.zone { min-height:68px; border:2px solid var(--ink); border-radius:16px; font:800 1rem/1.2 inherit; }
    .piece { color:var(--ink); background:var(--glow); cursor:grab; }
    .piece[aria-pressed="true"] { outline:5px solid var(--accent); transform:scale(1.03); }
    .piece[disabled] { opacity:.28; cursor:default; }
    .zone { display:grid; place-items:center; padding:12px; background:white; cursor:pointer; }
    .zone[data-filled="true"] { color:white; background:var(--accent); }
    .controls { display:grid; grid-template-columns:minmax(160px,260px) 1fr; gap:18px; align-items:center; margin-top:24px; }
    button { min-height:50px; padding:12px 18px; border:2px solid var(--ink); border-radius:999px; color:white;
      background:var(--ink); font:900 1rem/1 inherit; cursor:pointer; }
    button:focus-visible { outline:4px solid var(--accent); outline-offset:4px; }
    #status { min-height:1.5em; margin:0; font-weight:850; }
    .hint { margin:14px 0 0; font-size:.86rem; opacity:.72; }
    body.game-reaction-rush { background:
      radial-gradient(circle at 15% 10%,rgba(77,238,234,.16),transparent 30rem),
      radial-gradient(circle at 90% 0,rgba(255,79,163,.2),transparent 32rem),#080716; }
    main[data-game="reaction-rush"] { color:#f9f6ff; }
    main[data-game="reaction-rush"] .eyebrow { color:#4deeea; }
    main[data-game="reaction-rush"] .hud span { border-color:rgba(255,255,255,.2); color:#f9f6ff; background:rgba(255,255,255,.08); backdrop-filter:blur(14px); }
    main[data-game="reaction-rush"] .game-stage { isolation:isolate; border-color:rgba(255,255,255,.18); background:
      radial-gradient(circle at 50% -10%,rgba(255,79,163,.45),transparent 42%),
      radial-gradient(circle at 10% 110%,rgba(77,238,234,.28),transparent 42%),#0d0c21;
      box-shadow:0 30px 80px rgba(8,5,28,.5),inset 0 0 70px rgba(142,80,255,.14); }
    main[data-game="reaction-rush"] .game-stage::before,
    main[data-game="reaction-rush"] .game-stage::after { content:""; position:absolute; z-index:-1; top:-35%; width:34%; height:150%; pointer-events:none; opacity:.38; filter:blur(8px); }
    main[data-game="reaction-rush"] .game-stage::before { left:7%; background:linear-gradient(to bottom,rgba(77,238,234,.9),transparent 68%); transform:rotate(-18deg); transform-origin:top; }
    main[data-game="reaction-rush"] .game-stage::after { right:7%; background:linear-gradient(to bottom,rgba(255,79,163,.9),transparent 68%); transform:rotate(18deg); transform-origin:top; }
    main[data-game="reaction-rush"] .target { border-color:#fff; color:#111024; background:linear-gradient(145deg,#fff,#ffe169); box-shadow:0 0 0 8px rgba(255,255,255,.07),0 0 38px #ff4fa3; transition:transform .14s cubic-bezier(.2,.8,.2,1); }
    main[data-game="reaction-rush"] .target:active { transform:scale(.84); }
    main[data-game="reaction-rush"] #start { border-color:#4deeea; color:#0b1020; background:#4deeea; box-shadow:0 10px 30px rgba(77,238,234,.18); transition:transform .16s,box-shadow .16s; }
    main[data-game="reaction-rush"] #start:active { transform:scale(.97); }
    main[data-game="reaction-rush"] .game-stage[data-state="hit"] { animation:stage-hit .32s ease-out; }
    main[data-game="reaction-rush"] .game-stage[data-state="hit"]::before { opacity:.72; }
    main[data-game="reaction-rush"] .hud output[data-pop="true"] { display:inline-block; animation:score-pop .34s ease-out; }
    @keyframes stage-hit { 50% { box-shadow:0 0 0 4px rgba(77,238,234,.28),0 30px 90px rgba(255,79,163,.28),inset 0 0 90px rgba(77,238,234,.18); } }
    @keyframes score-pop { 50% { color:#4deeea; transform:scale(1.35); } }
    @media (max-width:680px) {
      header { grid-template-columns:1fr; } .hud { justify-content:flex-start; }
      .game-stage { min-height:390px; } .puzzle-board { grid-template-columns:1fr; }
      .controls { grid-template-columns:1fr; } #start { width:100%; }
    }
    @media (prefers-reduced-motion:reduce) { *,*::before,*::after { animation:none!important; transition:none!important; } }
  </style>
</head>
<body class="game-__GAME_ID__">
  <main data-kind="mini-game" data-game="__GAME_ID__">
    <header>
      <div>
        <p class="eyebrow">ChatWeb · __DIRECTION__</p>
        <h1>__TITLE__</h1>
        <p class="prompt">__PROMPT__</p>
      </div>
      <div class="hud" aria-label="游戏状态">
        <span>得分 <output id="score">0</output></span>
        <span>时间 <output id="timer">--</output></span>
      </div>
    </header>
    <section class="game-stage" id="stage" data-state="ready" aria-label="游戏区域"></section>
    <div class="controls">
      <button id="start" type="button">__START_LABEL__</button>
      <p id="status" role="status" aria-live="polite">准备好了，开始后可以随时重新挑战。</p>
    </div>
    <p class="hint">无需联网。支持鼠标和触控；需要移动时也可以使用键盘方向键。</p>
  </main>
  <script>
    const stage=document.querySelector('#stage');
    const score=document.querySelector('#score');
    const timer=document.querySelector('#timer');
    const status=document.querySelector('#status');
    const start=document.querySelector('#start');
    let cleanup=()=>{};
    function resetShell(){ cleanup(); score.value='0'; timer.value='--'; stage.dataset.state='playing'; start.textContent='重新开始'; }
    function finish(message='游戏结束'){ cleanup(); stage.dataset.state='ended'; start.disabled=false; start.textContent='重新开始'; status.textContent=message; }
__GAME_SCRIPT__
  </script>
</body>
</html>
'''


_REACTION_SCRIPT = r'''
    let reactionTimer=0;
    function placeTarget(target){
      const maxX=Math.max(12,stage.clientWidth-target.offsetWidth-12);
      const maxY=Math.max(12,stage.clientHeight-target.offsetHeight-12);
      target.style.left=`${12+Math.random()*(maxX-12)}px`;
      target.style.top=`${12+Math.random()*(maxY-12)}px`;
    }
    start.addEventListener('click',()=>{
      resetShell(); stage.replaceChildren(); start.disabled=true; status.textContent='看到星星就点它！';
      let remaining=20;
      const target=document.createElement('button'); target.className='target'; target.type='button'; target.textContent='★'; target.setAttribute('aria-label','点击得分');
      target.addEventListener('click',()=>{ score.value=String(Number(score.value)+1); placeTarget(target); status.textContent=`命中！当前 ${score.value} 分`;
        stage.dataset.state='hit'; score.dataset.pop='true'; window.setTimeout(()=>{ if(stage.dataset.state==='hit') stage.dataset.state='playing'; score.dataset.pop='false'; },340); });
      stage.append(target); placeTarget(target); timer.value=String(remaining);
      reactionTimer=window.setInterval(()=>{ remaining-=1; timer.value=String(remaining); if(remaining<=0) finish(`游戏结束，你获得了 ${score.value} 分。`); },1000);
      cleanup=()=>window.clearInterval(reactionTimer);
    });
'''


_DODGE_SCRIPT = r'''
    stage.innerHTML='<canvas width="720" height="420" aria-label="躲避收集游戏画布"></canvas><div class="touch-controls"><button id="left" type="button" aria-label="向左移动">←</button><button id="right" type="button" aria-label="向右移动">→</button></div>';
    const canvas=stage.querySelector('canvas'); const ctx=canvas.getContext('2d');
    let raf=0,active=false,left=false,right=false,startedAt=0,lastDrop=0;
    const player={x:330,y:362,w:60,h:32}; let drops=[];
    const key=(event,down)=>{ if(event.key==='ArrowLeft'||event.key==='a') left=down; if(event.key==='ArrowRight'||event.key==='d') right=down; };
    window.addEventListener('keydown',(event)=>key(event,true)); window.addEventListener('keyup',(event)=>key(event,false));
    for(const [id,setter] of [['left',(v)=>left=v],['right',(v)=>right=v]]){
      const control=document.querySelector(`#${id}`); control.addEventListener('pointerdown',()=>setter(true));
      control.addEventListener('pointerup',()=>setter(false)); control.addEventListener('pointercancel',()=>setter(false));
    }
    function hit(a,b){ return a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y; }
    function frame(now){
      if(!active) return; const elapsed=(now-startedAt)/1000; const remaining=Math.max(0,20-Math.floor(elapsed)); timer.value=String(remaining);
      if(left) player.x=Math.max(0,player.x-6); if(right) player.x=Math.min(canvas.width-player.w,player.x+6);
      if(now-lastDrop>520){ const good=Math.random()>.32; drops.push({x:Math.random()*680,y:-24,w:32,h:32,good}); lastDrop=now; }
      ctx.clearRect(0,0,canvas.width,canvas.height); ctx.fillStyle='__ACCENT__'; ctx.fillRect(player.x,player.y,player.w,player.h);
      drops.forEach((drop)=>{ drop.y+=4.1; ctx.fillStyle=drop.good?'#ffd166':'#ef476f'; ctx.beginPath(); ctx.arc(drop.x+16,drop.y+16,16,0,Math.PI*2); ctx.fill(); });
      drops=drops.filter((drop)=>{ if(hit(player,drop)){ score.value=String(Math.max(0,Number(score.value)+(drop.good?1:-1))); status.textContent=drop.good?'收集成功！':'碰到障碍，扣 1 分'; return false; } return drop.y<canvas.height+40; });
      if(elapsed>=20){ finish(`游戏结束，你获得了 ${score.value} 分。`); return; } raf=requestAnimationFrame(frame);
    }
    start.addEventListener('click',()=>{ resetShell(); start.disabled=true; status.textContent='收集黄色星球，避开红色障碍。'; player.x=330; drops=[]; active=true; startedAt=performance.now(); lastDrop=0; timer.value='20'; raf=requestAnimationFrame(frame); cleanup=()=>{ active=false; cancelAnimationFrame(raf); left=false; right=false; }; });
'''


_PUZZLE_SCRIPT = r'''
    const pairs=[['sun','☀️ 太阳','天空'],['fish','🐟 小鱼','水里'],['seed','🌱 种子','土壤']]; let selected='';
    function buildPuzzle(){
      const pieces=pairs.map(([id,label])=>`<button class="piece" type="button" draggable="true" data-piece="${id}" aria-pressed="false">${label}</button>`).join('');
      const zones=pairs.map(([id,,zone])=>`<button class="zone" type="button" data-zone="${id}" data-filled="false">${zone}</button>`).join('');
      stage.innerHTML=`<div class="puzzle-board"><div class="pieces" aria-label="可拖拽物件">${pieces}</div><div class="zones" aria-label="目标位置">${zones}</div></div>`;
      stage.querySelectorAll('.piece').forEach((piece)=>{
        piece.addEventListener('click',()=>selectPiece(piece));
        piece.addEventListener('dragstart',(event)=>{ selected=piece.dataset.piece; event.dataTransfer.setData('text/plain',selected); });
      });
      stage.querySelectorAll('.zone').forEach((zone)=>{
        zone.addEventListener('dragover',(event)=>event.preventDefault());
        zone.addEventListener('drop',(event)=>{ event.preventDefault(); tryPlace(event.dataTransfer.getData('text/plain'),zone); });
        zone.addEventListener('click',()=>tryPlace(selected,zone));
      });
    }
    function selectPiece(piece){ selected=piece.dataset.piece; stage.querySelectorAll('.piece').forEach((item)=>item.setAttribute('aria-pressed',String(item===piece))); status.textContent='现在选择右边对应的位置。'; }
    function tryPlace(id,zone){
      if(!id) return; if(id!==zone.dataset.zone){ status.textContent='还不匹配，换个位置试试看。'; return; }
      const piece=stage.querySelector(`[data-piece="${id}"]`); if(piece.disabled) return;
      piece.disabled=true; piece.setAttribute('aria-pressed','false'); zone.dataset.filled='true'; zone.textContent=`✓ ${zone.textContent}`; selected=''; score.value=String(Number(score.value)+1);
      if(Number(score.value)===pairs.length) finish('游戏结束，所有物件都找到了正确位置！'); else status.textContent='放对了，继续完成剩下的物件。';
    }
    start.addEventListener('click',()=>{ resetShell(); buildPuzzle(); timer.value='不限时'; status.textContent='拖动物件，或先点物件再点它应该去的位置。'; cleanup=()=>{}; });
    buildPuzzle();
'''


_SCRIPTS = {
    "reaction-rush": _REACTION_SCRIPT,
    "dodge-collect": _DODGE_SCRIPT,
    "drag-puzzle": _PUZZLE_SCRIPT,
}


def render_game(
    *,
    title: str,
    prompt: str,
    start_label: str,
    direction: DesignDirection,
) -> str:
    try:
        script = _SCRIPTS[direction.id]
    except KeyError as exc:
        raise ValueError(f"game template is not available for direction {direction.id!r}") from exc

    paper, ink, accent, glow = direction.palette
    replacements = {
        "__TITLE__": html.escape(title, quote=True),
        "__PROMPT__": html.escape(prompt, quote=True),
        "__START_LABEL__": html.escape(start_label, quote=True),
        "__DIRECTION__": html.escape(direction.name, quote=True),
        "__GAME_ID__": html.escape(direction.id, quote=True),
        "__PAPER__": paper,
        "__INK__": ink,
        "__ACCENT__": accent,
        "__GLOW__": glow,
        "__GAME_SCRIPT__": script.replace("__ACCENT__", accent),
    }
    rendered = _GAME_SHELL
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return rendered

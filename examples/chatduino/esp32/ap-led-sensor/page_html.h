#pragma once

#include <Arduino.h>

// Generated from a ChatWeb HTML source. Regenerate instead of editing this file.
const char CHATMAKER_AP_PAGE[] PROGMEM = R"CHATMAKER_PAGE(<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="dark">
  <title>DOIT ESP32 AP 控制台</title>
  <style>
    :root {
      --ink: #f5f8f2;
      --muted: #9aa89e;
      --panel: #17211b;
      --panel-soft: #1d2b23;
      --line: #33483b;
      --green: #7de49f;
      --green-deep: #173c25;
      --amber: #ffc76b;
      --red: #ff8d86;
      --blue: #8bc7ff;
      --shadow: 0 24px 70px rgba(0, 0, 0, .32);
    }

    * { box-sizing: border-box; }

    html { background: #0d1511; }

    body {
      margin: 0;
      min-height: 100vh;
      min-height: 100svh;
      color: var(--ink);
      background:
        radial-gradient(circle at 90% 4%, rgba(125, 228, 159, .13), transparent 34rem),
        linear-gradient(160deg, #101a15 0%, #0b120e 100%);
      font-family: Inter, "SF Pro Display", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }

    button { min-height: 48px; }

    button,
    .mode-button {
      border: 0;
      border-radius: 14px;
      font: inherit;
      font-weight: 760;
      cursor: pointer;
      touch-action: manipulation;
      -webkit-tap-highlight-color: transparent;
    }

    button:focus-visible {
      outline: 3px solid var(--blue);
      outline-offset: 3px;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: .42;
    }

    .shell {
      width: min(100%, 760px);
      margin: 0 auto;
      padding: max(22px, env(safe-area-inset-top)) 18px max(34px, env(safe-area-inset-bottom));
    }

    .topline {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 28px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
      color: var(--muted);
      font-size: .78rem;
      font-weight: 800;
      letter-spacing: .12em;
      text-transform: uppercase;
    }

    .brand-mark {
      width: 29px;
      height: 29px;
      flex: 0 0 auto;
      border: 1px solid var(--green);
      border-radius: 9px;
      background:
        linear-gradient(90deg, transparent 44%, var(--green) 45% 55%, transparent 56%),
        linear-gradient(transparent 44%, var(--green) 45% 55%, transparent 56%);
      box-shadow: inset 0 0 0 6px #12231a;
    }

    .state-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 32px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      background: rgba(255, 255, 255, .025);
      font-size: .78rem;
      font-weight: 750;
      white-space: nowrap;
    }

    .state-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 0 4px color-mix(in srgb, currentColor 13%, transparent);
    }

    [data-state="loading"] .state-pill { color: var(--amber); }
    [data-state="connected"] .state-pill { color: var(--green); }
    [data-state="error"] .state-pill { color: var(--red); }
    [data-state="loading"] .state-dot { animation: pulse 1s ease-in-out infinite; }

    .hero { margin-bottom: 22px; }

    .kicker {
      margin: 0 0 9px;
      color: var(--green);
      font-size: .75rem;
      font-weight: 850;
      letter-spacing: .15em;
      text-transform: uppercase;
    }

    h1 {
      max-width: 12ch;
      margin: 0;
      font-size: clamp(2.35rem, 11vw, 4.6rem);
      line-height: .96;
      letter-spacing: -.055em;
      text-wrap: balance;
    }

    .subtitle {
      max-width: 38rem;
      margin: 16px 0 0;
      color: var(--muted);
      font-size: .96rem;
      line-height: 1.65;
    }

    .mode-switch {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      margin: 24px 0 14px;
      padding: 5px;
      border: 1px solid var(--line);
      border-radius: 17px;
      background: #0d1711;
    }

    .mode-button {
      min-height: 48px;
      padding: 10px 12px;
      color: var(--muted);
      background: transparent;
    }

    .mode-button[aria-pressed="true"] {
      color: var(--ink);
      background: var(--panel-soft);
      box-shadow: 0 5px 14px rgba(0, 0, 0, .22);
    }

    .mode-note {
      display: flex;
      align-items: flex-start;
      gap: 9px;
      min-height: 44px;
      margin: 0 0 18px;
      padding: 11px 13px;
      border: 1px solid #64502c;
      border-radius: 13px;
      color: #f8d99c;
      background: rgba(255, 199, 107, .08);
      font-size: .82rem;
      line-height: 1.45;
    }

    [data-mode="real"] .mode-note { display: none; }

    .dashboard {
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: linear-gradient(145deg, rgba(29, 43, 35, .98), rgba(18, 29, 23, .98));
      box-shadow: var(--shadow);
    }

    .connection {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 20px;
      border-bottom: 1px solid var(--line);
    }

    .label {
      display: block;
      margin-bottom: 5px;
      color: var(--muted);
      font-size: .73rem;
      font-weight: 760;
      letter-spacing: .08em;
      text-transform: uppercase;
    }

    .connection strong { font-size: 1.08rem; }

    .refresh {
      min-width: 112px;
      padding: 11px 15px;
      color: #0c1710;
      background: var(--green);
    }

    .metrics {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1px;
      background: var(--line);
    }

    .metric {
      min-width: 0;
      min-height: 112px;
      padding: 18px;
      background: var(--panel);
    }

    .metric:last-child { grid-column: 1 / -1; }

    .metric-value {
      display: block;
      overflow: hidden;
      font-size: clamp(1.55rem, 7vw, 2.15rem);
      font-weight: 780;
      letter-spacing: -.04em;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .meter {
      height: 5px;
      margin-top: 14px;
      overflow: hidden;
      border-radius: 99px;
      background: #314039;
    }

    .meter-fill {
      width: 0;
      height: 100%;
      border-radius: inherit;
      background: var(--green);
      transition: width .25s ease;
    }

    .control-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 20px;
    }

    .control-copy { min-width: 0; }

    .control-copy p {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: .8rem;
      line-height: 1.4;
    }

    .led-button {
      min-width: 118px;
      padding: 12px 16px;
      border: 1px solid var(--line);
      color: var(--ink);
      background: #26342c;
    }

    .led-button[data-on="true"] {
      border-color: var(--green);
      color: var(--green);
      background: var(--green-deep);
      box-shadow: 0 0 24px rgba(125, 228, 159, .14);
    }

    .footnote {
      margin: 18px 4px 0;
      color: #77867d;
      font-size: .76rem;
      line-height: 1.55;
    }

    @keyframes pulse {
      50% { opacity: .35; transform: scale(.75); }
    }

    @media (min-width: 620px) {
      .shell { padding-right: 28px; padding-left: 28px; }
      .metrics { grid-template-columns: repeat(3, 1fr); }
      .metric { min-height: 126px; }
      .metric:last-child { grid-column: auto; }
    }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        scroll-behavior: auto !important;
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .01ms !important;
      }
    }
  </style>
</head>
<body>
  <main class="shell" id="app" data-state="disconnected" data-mode="real">
    <header class="topline">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span>DOIT ESP32 · AP</div>
      <div class="state-pill" role="status" aria-live="polite">
        <span class="state-dot" aria-hidden="true"></span>
        <span id="state-label">已断开</span>
      </div>
    </header>

    <section class="hero" aria-labelledby="page-title">
      <p class="kicker">Local device console</p>
      <h1 id="page-title">掌心里的<br>设备状态台</h1>
      <p class="subtitle">连接 ESP32 创建的 Wi-Fi AP 后，可读取传感器与运行时间，并控制 LED。页面不会把预览数据当作真实硬件状态。</p>
    </section>

    <div class="mode-switch" role="group" aria-label="连接模式">
      <button class="mode-button" id="mode-real" type="button" aria-pressed="true">真实设备</button>
      <button class="mode-button" id="mode-simulation" type="button" aria-pressed="false">模拟预览</button>
    </div>

    <p class="mode-note"><span aria-hidden="true">⚠</span><span>模拟模式仅用于页面预览，不代表 ESP32、Wi-Fi AP 或任何实物已经连接。</span></p>

    <section class="dashboard" aria-label="ESP32 状态与控制">
      <div class="connection">
        <div>
          <span class="label">Connection</span>
          <strong id="connection-status">未连接</strong>
        </div>
        <button class="refresh" id="refresh-state" type="button">读取状态</button>
      </div>

      <div class="metrics" aria-label="设备数据">
        <div class="metric">
          <span class="label">Sensor raw</span>
          <output class="metric-value" id="sensor-value">—</output>
          <div class="meter" aria-hidden="true"><div class="meter-fill" id="sensor-meter"></div></div>
        </div>
        <div class="metric">
          <span class="label">Uptime</span>
          <output class="metric-value" id="uptime-value">—</output>
        </div>
        <div class="metric">
          <span class="label">Schema</span>
          <output class="metric-value" id="schema-value">—</output>
        </div>
      </div>

      <div class="control-row">
        <div class="control-copy">
          <span class="label">LED output</span>
          <strong id="led-status">状态未知</strong>
          <p>设备模式会回读状态；模拟模式只更新预览数据。</p>
        </div>
        <button class="led-button" id="led-control" type="button" data-on="false" disabled>打开 LED</button>
      </div>
    </section>

    <p class="footnote">真实模式只访问当前页面同源的 <code>/api/state</code> 与 <code>/api/led</code>。请使用 ESP32 实际提供的页面地址打开本页。</p>
  </main>

  <script>
    const app = document.querySelector("#app");
    const stateLabel = document.querySelector("#state-label");
    const connectionStatus = document.querySelector("#connection-status");
    const refreshState = document.querySelector("#refresh-state");
    const ledControl = document.querySelector("#led-control");
    const ledStatus = document.querySelector("#led-status");
    const sensorValue = document.querySelector("#sensor-value");
    const sensorMeter = document.querySelector("#sensor-meter");
    const uptimeValue = document.querySelector("#uptime-value");
    const schemaValue = document.querySelector("#schema-value");
    const modeReal = document.querySelector("#mode-real");
    const modeSimulation = document.querySelector("#mode-simulation");

    let mode = "real";
    let currentDeviceState = null;
    let simulationTimer = null;

    const stateLabels = {
      "disconnected": "已断开",
      "loading": "读取中",
      "connected": "已连接",
      "error": "连接错误"
    };

    function setConnectionState(state, message) {
      app.dataset.state = state;
      stateLabel.textContent = stateLabels[state];
      connectionStatus.textContent = message;
      ledControl.disabled = state !== "connected";
      refreshState.disabled = state === "loading";
    }

    function clearDeviceState() {
      currentDeviceState = null;
      sensorValue.value = "—";
      sensorMeter.style.width = "0%";
      uptimeValue.value = "—";
      schemaValue.value = "—";
      ledControl.dataset.on = "false";
      ledControl.textContent = "打开 LED";
      ledStatus.textContent = "状态未知";
    }

    function formatUptime(milliseconds) {
      const totalSeconds = Math.floor(milliseconds / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m ${seconds}s`;
    }

    function validateDeviceState(value) {
      const versionIsValid = typeof value?.schema_version === "string" || typeof value?.schema_version === "number";
      const sensorIsValid = typeof value?.sensor_raw === "number" && Number.isFinite(value.sensor_raw);
      const uptimeIsValid = typeof value?.uptime_ms === "number" && Number.isFinite(value.uptime_ms) && value.uptime_ms >= 0;
      if (!versionIsValid || typeof value?.led_on !== "boolean" || !sensorIsValid || !uptimeIsValid) {
        throw new Error("设备状态格式不符合约定");
      }
      return value;
    }

    function renderDeviceState(value) {
      currentDeviceState = value;
      sensorValue.value = String(value.sensor_raw);
      sensorMeter.style.width = `${Math.max(0, Math.min(100, value.sensor_raw / 4095 * 100))}%`;
      uptimeValue.value = formatUptime(value.uptime_ms);
      schemaValue.value = String(value.schema_version);
      ledControl.dataset.on = String(value.led_on);
      ledControl.textContent = value.led_on ? "关闭 LED" : "打开 LED";
      ledStatus.textContent = value.led_on ? "已开启" : "已关闭";
    }

    async function fetchRealState() {
      const response = await fetch("/api/state", { cache: "no-store" });
      if (!response.ok) throw new Error(`状态接口返回 ${response.status}`);
      return validateDeviceState(await response.json());
    }

    async function loadState() {
      window.clearTimeout(simulationTimer);
      setConnectionState("loading", mode === "simulation" ? "正在准备模拟数据…" : "正在读取设备…");

      if (mode === "simulation") {
        simulationTimer = window.setTimeout(() => {
          renderDeviceState({ schema_version: "preview-1", led_on: false, sensor_raw: 2186, uptime_ms: 94250 });
          setConnectionState("connected", "模拟预览已启动（非真实硬件）");
        }, 420);
        return;
      }

      try {
        renderDeviceState(await fetchRealState());
        setConnectionState("connected", "真实设备已响应");
      } catch (error) {
        clearDeviceState();
        setConnectionState("error", error instanceof Error ? error.message : "无法读取设备");
      }
    }

    async function toggleLed() {
      if (!currentDeviceState || app.dataset.state !== "connected") return;
      const nextOn = !currentDeviceState.led_on;
      setConnectionState("loading", mode === "simulation" ? "正在更新模拟 LED…" : "正在发送 LED 指令…");

      if (mode === "simulation") {
        renderDeviceState({ ...currentDeviceState, led_on: nextOn, uptime_ms: currentDeviceState.uptime_ms + 700 });
        setConnectionState("connected", "模拟 LED 已更新（非真实硬件）");
        return;
      }

      try {
        const response = await fetch("/api/led", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({on: nextOn})
        });
        if (!response.ok) throw new Error(`LED 接口返回 ${response.status}`);
        renderDeviceState(await fetchRealState());
        setConnectionState("connected", "LED 指令已发送并同步");
      } catch (error) {
        setConnectionState("error", error instanceof Error ? error.message : "LED 指令失败");
      }
    }

    function selectMode(nextMode) {
      window.clearTimeout(simulationTimer);
      mode = nextMode;
      app.dataset.mode = mode;
      modeReal.setAttribute("aria-pressed", String(mode === "real"));
      modeSimulation.setAttribute("aria-pressed", String(mode === "simulation"));
      refreshState.textContent = mode === "real" ? "读取状态" : "启动预览";
      clearDeviceState();
      setConnectionState("disconnected", mode === "real" ? "未连接" : "模拟预览未启动");
    }

    refreshState.addEventListener("click", loadState);
    ledControl.addEventListener("click", toggleLed);
    modeReal.addEventListener("click", () => selectMode("real"));
    modeSimulation.addEventListener("click", () => selectMode("simulation"));
  </script>
</body>
</html>
)CHATMAKER_PAGE";
constexpr size_t CHATMAKER_AP_PAGE_LENGTH = sizeof(CHATMAKER_AP_PAGE) - 1;

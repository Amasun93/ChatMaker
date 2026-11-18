(() => {
  const button = document.querySelector("#button");
  const led = document.querySelector("#led");
  const ledState = document.querySelector("#led-state");
  const status = document.querySelector("#status");
  const wiringStatus = document.querySelector("#wiring-status");
  const clearWires = document.querySelector("#clear-wires");
  const canvas = document.querySelector(".wires");
  const terminals = new Map(Array.from(document.querySelectorAll("[data-terminal]"),
    (element) => [element.dataset.terminal, element]));
  const connections = new Map();
  const wireColors = { d2: "#137cc5", gnd: "#405067" };
  let selected = null;
  let pressed = false;
  const { CPU, avrInstruction, AVRIOPort, PinState, portBConfig, portCConfig,
    portDConfig, AVRTimer, timer0Config, timer1Config, timer2Config, AVRUSART, usart0Config } = ChatSimAVR;
  const flashWords = new Uint16Array(16 * 1024).fill(0xffff);
  const firmware = atob(document.querySelector("#firmware").textContent);
  for (let index = 0; index < firmware.length; index += 2) {
    const high = index + 1 < firmware.length ? firmware.charCodeAt(index + 1) : 0xff;
    flashWords[index / 2] = firmware.charCodeAt(index) | (high << 8);
  }

  const cpu = new CPU(flashWords, 2048);
  new AVRTimer(cpu, timer0Config);
  new AVRTimer(cpu, timer1Config);
  new AVRTimer(cpu, timer2Config);
  new AVRUSART(cpu, usart0Config, 16_000_000);
  const portB = new AVRIOPort(cpu, portBConfig);
  new AVRIOPort(cpu, portCConfig);
  const portD = new AVRIOPort(cpu, portDConfig);

  function updateInput() {
    // With INPUT_PULLUP, D2 goes LOW only through a closed path to GND.
    portD.setPin(2, !(pressed && connections.has("d2") && connections.has("gnd")));
  }

  function setPressed(active) {
    pressed = active;
    button.setAttribute("aria-pressed", String(active));
    updateInput();
  }

  function drawWires() {
    const bounds = canvas.getBoundingClientRect();
    const scale = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(bounds.width * scale);
    canvas.height = Math.round(bounds.height * scale);
    const context = canvas.getContext("2d");
    if (!context) return;
    context.scale(scale, scale);

    function socketPosition(name) {
      const socket = terminals.get(name).querySelector(".socket").getBoundingClientRect();
      return { x: socket.left + socket.width / 2 - bounds.left,
        y: socket.top + socket.height / 2 - bounds.top };
    }

    for (const [pin, leg] of connections) {
      const start = socketPosition(pin);
      const end = socketPosition(leg);
      const offset = Math.abs(end.x - start.x) * 0.52;
      context.lineCap = "round";
      context.beginPath();
      context.moveTo(start.x, start.y);
      context.bezierCurveTo(start.x + offset, start.y, end.x - offset, end.y, end.x, end.y);
      context.lineWidth = 7;
      context.strokeStyle = "#f7faf9";
      context.stroke();
      context.lineWidth = 4;
      context.strokeStyle = wireColors[pin];
      context.stroke();
    }
  }

  function showWiring(message) {
    const connected = new Set([...connections.keys(), ...connections.values()]);
    for (const [name, element] of terminals) {
      element.setAttribute("aria-pressed", String(name === selected));
      element.dataset.connected = String(connected.has(name));
    }
    clearWires.disabled = !selected && connections.size === 0;
    wiringStatus.textContent = message;
    updateInput();
    drawWires();
  }

  for (const [name, element] of terminals) {
    element.addEventListener("click", () => {
      if (selected === name) {
        selected = null;
        showWiring("已取消选点。");
        return;
      }
      const isBoardPin = Object.hasOwn(wireColors, name);
      if (selected === null || isBoardPin === Object.hasOwn(wireColors, selected)) {
        selected = name;
        showWiring(isBoardPin ? "再选一个按钮接点。" : "再选主控板的 D2 或 GND。");
        return;
      }
      const pin = isBoardPin ? name : selected;
      const leg = isBoardPin ? selected : name;
      for (const [wiredPin, wiredLeg] of connections) {
        if (wiredLeg === leg) connections.delete(wiredPin);
      }
      connections.set(pin, leg);
      selected = null;
      showWiring(connections.size === 2 ? "两根线已接好，按住按钮看 D13。"
        : "接好一根线，再把另一端接上。");
    });
  }
  clearWires.addEventListener("click", () => {
    connections.clear();
    selected = null;
    showWiring("接线已清空。");
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && selected !== null) {
      selected = null;
      showWiring("已取消选点。");
    }
  });
  new ResizeObserver(drawWires).observe(canvas.parentElement);

  button.addEventListener("pointerdown", (event) => {
    if (!event.isPrimary || event.button !== 0) return;
    button.setPointerCapture(event.pointerId);
    setPressed(true);
  });
  for (const event of ["pointerup", "pointercancel", "lostpointercapture", "blur"]) {
    button.addEventListener(event, () => setPressed(false));
  }
  for (const event of ["keydown", "keyup"]) {
    button.addEventListener(event, (key) => {
      if (key.key !== " " && key.key !== "Enter") return;
      key.preventDefault();
      setPressed(event === "keydown");
    });
  }
  window.addEventListener("blur", () => setPressed(false));
  setPressed(false);

  let lastFrame;
  function frame(time) {
    const elapsed = Math.min(lastFrame === undefined ? 16 : time - lastFrame, 32);
    const end = cpu.cycles + Math.round(elapsed * 16_000);
    lastFrame = time;
    try {
      while (cpu.cycles < end) {
        avrInstruction(cpu);
        cpu.tick();
      }
      const on = portB.pinState(5) === PinState.High;
      if (led.dataset.led !== (on ? "on" : "off")) {
        led.dataset.led = on ? "on" : "off";
        ledState.textContent = on ? "点亮" : "熄灭";
      }
      if (button.disabled) {
        button.disabled = false;
        status.textContent = "固件仿真运行中";
      }
      requestAnimationFrame(frame);
    } catch {
      button.disabled = true;
      status.textContent = "仿真中断，请检查程序和当前板型。";
    }
  }
  requestAnimationFrame(frame);
})();

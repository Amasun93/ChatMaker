(() => {
  const viewport = document.querySelector(".viewport");
  const schematic = document.querySelector(".schematic");
  const canvas = document.querySelector(".wires");
  const board = document.querySelector("#uno-part");
  const switchGraphic = document.querySelector("#button-part");
  const run = document.querySelector("#run");
  const button = document.querySelector("#button");
  const led = document.querySelector("#led");
  const ledState = document.querySelector("#led-state");
  const status = document.querySelector("#status");

  const signal = document.querySelector(".wire-list .signal");
  const ground = document.querySelector(".wire-list .ground");
  const inputPin = Number(signal.dataset.boardPin);
  const { CPU, avrInstruction, AVRIOPort, PinState, portBConfig, portCConfig,
    portDConfig, AVRTimer, timer0Config, timer1Config, timer2Config, AVRUSART, usart0Config } = ChatSimAVR;
  const flashWords = new Uint16Array(16 * 1024).fill(0xffff);
  const firmware = atob(document.querySelector("#firmware").textContent);
  for (let index = 0; index < firmware.length; index += 2) {
    const high = index + 1 < firmware.length ? firmware.charCodeAt(index + 1) : 0xff;
    flashWords[index / 2] = firmware.charCodeAt(index) | (high << 8);
  }

  let scale;
  let emulation = null;
  let lastFrame;
  let pendingFrame;

  function fitSchematic() {
    scale = Math.min(1, viewport.clientWidth / schematic.offsetWidth, viewport.clientHeight / schematic.offsetHeight);
    schematic.style.setProperty("--scale", String(scale));
  }

  function drawWires() {
    const pixelRatio = 2;
    canvas.width = schematic.offsetWidth * pixelRatio;
    canvas.height = schematic.offsetHeight * pixelRatio;
    const context = canvas.getContext("2d");
    context.scale(pixelRatio, pixelRatio);
    context.lineJoin = "round";
    context.lineCap = "round";
    context.font = "bold 14px system-ui, sans-serif";
    const origin = schematic.getBoundingClientRect();

    function findPin(part, name) {
      const pin = part.pinInfo.find((entry) => entry.name === name);
      const bounds = part.getBoundingClientRect();
      return { x: (bounds.left - origin.left) / scale + pin.x, y: (bounds.top - origin.top) / scale + pin.y };
    }

    function drawConnection(row, laneX, laneY, pinName, labelY) {
      const start = findPin(board, row.dataset.boardPin);
      const end = findPin(switchGraphic, row.dataset.buttonPin);
      const color = getComputedStyle(row).getPropertyValue("--wire");
      context.beginPath();
      context.moveTo(start.x, start.y);
      context.lineTo(start.x, laneY);
      context.lineTo(laneX, laneY);
      context.lineTo(laneX, end.y);
      context.lineTo(end.x, end.y);
      context.lineWidth = 7;
      context.strokeStyle = "#f5f8f9";
      context.stroke();
      context.lineWidth = 3.5;
      context.strokeStyle = color;
      context.stroke();
      context.fillStyle = color;
      for (const pin of [start, end]) {
        context.beginPath();
        context.arc(pin.x, pin.y, 4, 0, Math.PI * 2);
        context.fill();
      }
      context.fillText(pinName, start.x + 9, labelY);
    }

    drawConnection(signal, 403, 51, "D2", 42);
    drawConnection(ground, 420, 316, "GND", 307);
  }

  function setPressed(pressed) {
    switchGraphic.pressed = pressed;
    button.setAttribute("aria-pressed", String(pressed));
    // The depicted switch closes the circuit from D2 to GND when pressed.
    emulation?.portD.setPin(inputPin, !pressed);
  }

  function updateLed(on) {
    const state = on ? "on" : "off";
    if (led.dataset.led === state) return;
    board.led13 = on;
    led.dataset.led = state;
    ledState.textContent = on ? "点亮" : "熄灭";
  }

  function setRunningUI(running, message) {
    board.ledPower = running;
    run.dataset.running = String(running);
    run.textContent = running ? "停止仿真" : "运行仿真";
    button.disabled = !running;
    status.textContent = message;
  }

  function stop(message = "仿真已停止，可以重新运行。") {
    cancelAnimationFrame(pendingFrame);
    emulation = null;
    setPressed(false);
    updateLed(false);
    setRunningUI(false, message);
  }

  function frame(time) {
    const { cpu, portB } = emulation;
    const elapsed = Math.min(lastFrame === undefined ? 16 : time - lastFrame, 32);
    const end = cpu.cycles + Math.round(elapsed * 16_000);
    lastFrame = time;
    try {
      while (cpu.cycles < end) {
        avrInstruction(cpu);
        cpu.tick();
      }
      updateLed(portB.pinState(5) === PinState.High);
      pendingFrame = requestAnimationFrame(frame);
    } catch {
      stop("仿真中断，请检查程序是否适用于 UNO R3。");
    }
  }

  function start() {
    const cpu = new CPU(flashWords.slice(), 2048);
    new AVRTimer(cpu, timer0Config);
    new AVRTimer(cpu, timer1Config);
    new AVRTimer(cpu, timer2Config);
    new AVRUSART(cpu, usart0Config, 16_000_000);
    const portB = new AVRIOPort(cpu, portBConfig);
    new AVRIOPort(cpu, portCConfig);
    const portD = new AVRIOPort(cpu, portDConfig);
    emulation = { cpu, portB, portD };
    lastFrame = undefined;
    setPressed(false);
    setRunningUI(true, "按住图中的红色按钮，看看 D13 板载灯。");
    pendingFrame = requestAnimationFrame(frame);
  }

  run.addEventListener("click", () => {
    if (emulation) stop();
    else start();
  });

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

  Promise.all([board.updateComplete, switchGraphic.updateComplete]).then(() => {
    fitSchematic();
    drawWires();
    new ResizeObserver(fitSchematic).observe(viewport);
    setRunningUI(false, "接线图已就绪。点「运行仿真」后试按按钮。");
    run.disabled = false;
  }).catch(() => {
    status.textContent = "元件图加载失败，请重新生成预览。";
  });
})();

(() => {
  const config = ChatSimDimmer;
  const viewport = document.querySelector(".viewport");
  const schematic = document.querySelector(".schematic");
  const context = document.querySelector("#wires").getContext("2d");
  const slider = document.querySelector("#level");
  const output = document.querySelector("#status");
  const board = document.querySelector("#board");
  const pot = document.querySelector("#pot");
  const lamp = document.querySelector("#lamp");
  const resistor = document.querySelector("#resistor");
  const firmware = Uint8Array.from(atob(document.querySelector("#program").textContent), char => char.charCodeAt(0));
  const pins = config.pins;
  const wires = [
    [board, pins.supply, pot, "VCC", config.supply + " → 旋钮一侧", "#c1543c"],
    [board, pins.ground, pot, "GND", "GND → 旋钮另一侧", "#374b54"],
    [board, pins.input, pot, "SIG", config.input + " → 旋钮中间脚", "#2a7d66"],
    [board, pins.output, resistor, "1", config.output + " → 330 Ω 电阻", "#235f97"],
    [resistor, "2", lamp, "A", "电阻另一端 → LED 长脚（+）", "#a47419"],
    [lamp, "C", board, pins.ground, "LED 短脚（−）→ GND", "#374b54"],
  ];

  function wireDiagram() {
    const scale = viewport.clientWidth / 580;
    schematic.style.setProperty("--scale", String(scale));
    context.setTransform(2, 0, 0, 2, 0, 0);
    context.clearRect(0, 0, 580, 322);
    const origin = schematic.getBoundingClientRect();
    function endpoint(part, name) {
      const pin = part.pinInfo.find(entry => entry.name === name);
      const rect = part.getBoundingClientRect();
      return { x: (rect.left - origin.left) / scale + pin.x, y: (rect.top - origin.top) / scale + pin.y };
    }
    const esp = config.mode === "program-logic";
    const path = [
      (a, b) => esp ? [[a.x + 33, a.y], [a.x + 33, 213], [b.x, 213]]
        : [[a.x, 251], [b.x, 251]],
      (a, b) => esp ? [[a.x + 16, a.y], [a.x + 16, 286], [b.x, 286]]
        : [[a.x, 286], [b.x, 286]],
      (a, b) => esp ? [[a.x - 41, a.y], [a.x - 41, 304], [b.x, 304]]
        : [[a.x, 269], [b.x, 269]],
      (a, b) => [...(esp ? [[a.x + 23, a.y]] : []), [a.x + (esp ? 23 : 0), 31],
        [b.x - 15, 31], [b.x - 15, b.y]],
      (a, b) => [[b.x + 27, a.y], [b.x + 27, b.y + 17], [b.x, b.y + 17]],
      (a, b) => [[a.x, 221], [555, 221], [555, 297], [b.x + (esp ? 16 : 0), 297],
        ...(esp ? [[b.x + 16, b.y]] : [])],
    ];
    for (const [index, [part, pin, device, terminal, , color]] of wires.entries()) {
      const a = endpoint(part, pin);
      const b = endpoint(device, terminal);
      context.beginPath();
      context.moveTo(a.x, a.y);
      for (const [x, y] of path[index](a, b)) context.lineTo(x, y);
      context.lineTo(b.x, b.y);
      context.lineJoin = "round";
      context.strokeStyle = "#fff";
      context.lineWidth = 6;
      context.stroke();
      context.strokeStyle = color;
      context.lineWidth = 3.2;
      context.stroke();
      for (const { x, y } of [a, b]) {
        context.beginPath();
        context.arc(x, y, 4, 0, 2 * Math.PI);
        context.fillStyle = color;
        context.fill();
      }
    }
  }

  function showDuty(duty) {
    const percent = Math.round(duty * 100);
    lamp.value = percent > 0;
    lamp.brightness = duty;
    if (output.dataset.level !== String(percent)) {
      output.dataset.level = String(percent);
      output.textContent = "LED 亮度 " + percent + "%";
    }
  }

  function startAvr() {
    const { CPU, avrInstruction, AVRIOPort, portBConfig, portCConfig, portDConfig,
      AVRTimer, timer0Config, timer1Config, timer2Config, AVRUSART, usart0Config, AVRADC, adcConfig } = ChatSimAVR;
    const words = new Uint16Array(16 * 1024).fill(65535);
    for (let offset = 0; offset < firmware.length; offset += 2) {
      words[offset / 2] = firmware[offset] | ((firmware[offset + 1] ?? 255) << 8);
    }
    const cpu = new CPU(words, 2048);
    new AVRIOPort(cpu, portBConfig);
    new AVRIOPort(cpu, portCConfig);
    const port = new AVRIOPort(cpu, portDConfig);
    new AVRTimer(cpu, timer0Config);
    new AVRTimer(cpu, timer1Config);
    new AVRTimer(cpu, timer2Config);
    new AVRUSART(cpu, usart0Config, 16_000_000);
    const adc = new AVRADC(cpu, adcConfig);
    let high = false;
    let highCycles = 0;
    let lastCycle = cpu.cycles;
    port.addListener(value => {
      if (high) highCycles += cpu.cycles - lastCycle;
      high = Boolean(value & (1 << 3));
      lastCycle = cpu.cycles;
    });
    function frame() {
      adc.channelValues[0] = Number(slider.value) / 100 * 5;
      const start = lastCycle = cpu.cycles;
      const end = start + 16 * 16000;
      highCycles = 0;
      while (cpu.cycles < end) {
        avrInstruction(cpu);
        cpu.tick();
      }
      if (high) highCycles += cpu.cycles - lastCycle;
      showDuty(highCycles / (cpu.cycles - start));
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  async function ready() {
    for (const [, , , , label, color] of wires) {
      const item = document.createElement("li");
      item.textContent = label;
      item.style.setProperty("--wire", color);
      document.querySelector("aside ul").append(item);
    }
    await Promise.all([board.updateComplete, pot.updateComplete, resistor.updateComplete, lamp.updateComplete]);
    wireDiagram();
    new ResizeObserver(wireDiagram).observe(viewport);
    board.ledPower = true;
    pot.max = 100;
    slider.addEventListener("input", () => { pot.value = Number(slider.value); });
    pot.addEventListener("input", event => {
      if (event.target !== pot || typeof event.detail !== "number") return;
      slider.value = pot.value;
      slider.dispatchEvent(new Event("input"));
    });
    if (config.mode === "firmware") {
      startAvr();
    } else {
      const { instance } = await WebAssembly.instantiate(firmware);
      instance.exports._initialize?.();
      const update = () => showDuty(instance.exports.knob_pwm(Math.round(Number(slider.value) * 4095 / 100)) / 255);
      slider.addEventListener("input", update);
      update();
    }
    slider.disabled = false;
  }
  ready().catch(() => { output.textContent = "实验未加载，请重新生成预览。"; });
})();

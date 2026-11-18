(() => {
  const button = document.querySelector("#button");
  const led = document.querySelector("#led");
  const ledState = document.querySelector("#led-state");
  const status = document.querySelector("#status");
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

  function setPressed(pressed) {
    button.setAttribute("aria-pressed", String(pressed));
    portD.setPin(2, !pressed);
  }

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

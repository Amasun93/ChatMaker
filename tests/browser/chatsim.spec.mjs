import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { expect, test } from "@playwright/test";

const assets = new URL("../../runtime/chatmaker/sim_assets/", import.meta.url);

async function openSimulation(page, inverted) {
  const [template, engine, parts, simulator] = await Promise.all(
    ["uno.html", "avr8js.js", "wokwi-parts.js", "uno.js"].map((name) => readFile(new URL(name, assets), "utf8")),
  );
  // A small AVR program sets PB5 as output and enables the PD2 pull-up.
  // Then it checks PIND2 and sets/clears PORTB5 in a loop.
  const lightOn = 0x9a2d;
  const lightOff = 0x982d;
  const instructions = [
    0x9a25, 0x9a5a, 0x994a, 0xc002, inverted ? lightOff : lightOn,
    0xcffc, inverted ? lightOn : lightOff, 0xcffa,
  ];
  const firmware = Buffer.alloc(instructions.length * 2);
  instructions.forEach((word, index) => firmware.writeUInt16LE(word, index * 2));
  const tokens = { sketch: "fixture.hex", sha256: "fixture", short_hash: "fixture",
    circuit: "button-led", lesson: "UNO R3 按钮亮灯", intro: "试按外接按钮，观察 D13 板载灯。",
    button_ground: "GND.2", ground_leg: "2.l", ground_label: "图中按钮左下脚",
    engine, parts, oled_model: "", firmware: firmware.toString("base64"), simulator };
  await page.goto("about:blank");
  await page.setContent(template.replace(/\$([a-z_0-9]+)/g, (_, name) => tokens[name]));
  await expect(page.getByRole("button", { name: "运行仿真" })).toBeEnabled();
}

async function expectLed(page, on) {
  await expect(page.locator("#led")).toHaveAttribute("data-led", on ? "on" : "off");
  await expect.poll(() => page.locator("wokwi-arduino-uno").evaluate((board) => board.led13)).toBe(on);
}

test("virtual UNO LED follows the provided AVR program", async ({ page, context }) => {
  await context.setOffline(true);
  for (const inverted of [false, true]) {
    await openSimulation(page, inverted);
    const button = page.getByRole("button", { name: "按住外接按钮" });
    await expect(button).toBeDisabled();
    await page.getByRole("button", { name: "运行仿真" }).click();
    await expectLed(page, inverted);
    await button.focus();
    await page.keyboard.down("Space");
    await expect(button).toHaveAttribute("aria-pressed", "true");
    await expectLed(page, !inverted);
    await page.keyboard.up("Space");
    await expectLed(page, inverted);
  }
});

test("the wired circuit is visible before running and can be used on a narrow screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 740 });
  await openSimulation(page, false);
  await expect(page.locator(".wire-list li:visible")).toHaveText(["D2 → 图中按钮左上脚", "GND → 图中按钮左下脚"]);
  await expect(page.locator("wokwi-arduino-uno")).toBeVisible();
  await expect(page.locator("wokwi-pushbutton")).toBeVisible();
  const hasWires = await page.locator(".wires").evaluate((canvas) =>
    canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data.some((value) => value !== 0));
  expect(hasWires).toBe(true);

  const switchButton = page.getByRole("button", { name: "按住外接按钮" });
  const runButton = page.locator("#run");
  await runButton.click();
  await switchButton.hover();
  await page.mouse.down();
  await expectLed(page, true);
  await page.mouse.up();
  await expectLed(page, false);
  await expect(runButton).toHaveText("停止仿真");
  await runButton.click();
  await expect(switchButton).toBeDisabled();

  await page.setViewportSize({ width: 320, height: 740 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(320);
  await runButton.click();
  await switchButton.focus();
  await page.keyboard.down("Enter");
  await expectLed(page, true);
  await page.keyboard.up("Enter");
  await expectLed(page, false);
});

test("SSD1306 framebuffer follows I2C commands and data", async ({ page }) => {
  await page.setContent('<canvas width="128" height="64"></canvas>');
  await page.addScriptTag({ path: fileURLToPath(new URL("ssd1306.js", assets)) });
  const states = await page.evaluate(() => {
    const screen = document.querySelector("canvas");
    const pixel = () => screen.getContext("2d").getImageData(10, 17, 1, 1).data[0] > 100;
    const device = new ChatSimSSD1306(screen);
    const bus = {
      completeStart() {}, completeStop() {}, completeRead() {}, completeWrite() {},
      completeConnect(ack) { this.ack = ack; },
    };
    device.connect(bus);
    const send = (address, bytes) => {
      bus.eventHandler.start(false);
      bus.eventHandler.connectToSlave(address, true);
      if (bus.ack) bytes.forEach((value) => bus.eventHandler.writeByte(value));
      bus.eventHandler.stop();
      device.redraw();
      return bus.ack;
    };
    send(0x3c, [0x00, 0x20, 0x00, 0x21, 10, 10, 0x22, 2, 2]);
    send(0x3c, [0x40, 0x02]);
    const beforePowerOn = pixel();
    const wrongAddress = send(0x3d, [0x00, 0xaf]);
    send(0x3c, [0x00, 0xaf]);
    const powered = pixel();
    send(0x3c, [0x40, 0x00]);
    const cleared = pixel();
    return { beforePowerOn, wrongAddress, powered, cleared };
  });
  expect(states).toEqual({ beforePowerOn: false, wrongAddress: false, powered: true, cleared: false });
});

async function openWasmDemo(page, name) {
  const [template, program, artwork] = await Promise.all([
    readFile(new URL(name + ".html", assets), "utf8"),
    readFile(new URL(name + ".wasm", assets)),
    name === "starcore-oled" ? readFile(new URL("starcore-board.js", assets), "utf8") : "",
  ]);
  await page.goto("about:blank");
  await page.setContent(template.replace("$wasm", program.toString("base64"))
    .replace("$notices", "").replace("$artwork", () => artwork));
}

async function frame(canvas) {
  return canvas.evaluate((element) => element.toDataURL());
}

test("Starcore A key drives the compiled OLED program off network", async ({ page, context }) => {
  await context.setOffline(true);
  await page.setViewportSize({ width: 390, height: 780 });
  await openWasmDemo(page, "starcore-oled");
  const button = page.getByRole("button", { name: "按住板载 A 键" });
  const oled = page.locator("#oled-screen");
  await expect(button).toBeEnabled();
  await expect(page.locator(".wiring li")).toHaveCount(4);
  const viewport = await page.locator(".viewport").boundingBox();
  const display = await oled.boundingBox();
  expect(display.x + display.width).toBeLessThanOrEqual(viewport.x + viewport.width);
  const rest = await frame(oled);
  await button.focus();
  await page.keyboard.down("Space");
  await expect(button).toHaveAttribute("aria-pressed", "true");
  expect(await frame(oled)).not.toBe(rest);
  await page.keyboard.up("Space");
  expect(await frame(oled)).toBe(rest);
  const select = page.getByLabel("查找下方排针");
  await expect(select.locator("option")).toHaveCount(27);
  await select.selectOption("P5");
  await expect(page.locator("#pin-marker")).toBeVisible();
  await expect(page.locator("#pin-note")).toHaveText("P5 的 S 排是 GPIO0。");
  await select.selectOption("");
  await expect(page.locator("#pin-marker")).toBeHidden();
  await page.locator('.pin-target[data-label="P15"]').click();
  await expect(select).toHaveValue("P15");
  await expect(page.locator("#pin-note")).toHaveText("P15 的 S 排是 GPIO21。");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
});

test("Waveshare V2 touch stays connected to the LVGL demo", async ({ page, context }) => {
  await context.setOffline(true);
  await openWasmDemo(page, "waveshare-touch");
  await expect(page.getByRole("status")).toHaveText("触屏已就绪。");
  const lcd = page.locator("#lcd");
  const rest = await frame(lcd);
  const box = await lcd.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height * .75);
  await page.mouse.down();
  expect(await frame(lcd)).not.toBe(rest);
  await page.mouse.up();
  expect(await frame(lcd)).toBe(rest);
});

test("Starcore library opens both bundled labs and keeps reference parts discoverable offline",
  async ({ page, context }, testInfo) => {
    const output = testInfo.outputPath("starcore-library.html");
    execFileSync(process.env.CHATMAKER_TEST_PYTHON || "python",
      ["-m", "chatmaker.sim", "--library", "starcore", "--output", output, "--progress", "none"]);
    await context.setOffline(true);
    await page.setViewportSize({ width: 390, height: 780 });
    await page.goto(pathToFileURL(output).href);
    await expect(page.getByRole("heading", { name: "配套元件 · 22 项" })).toBeVisible();
    await expect(page.getByRole("article")).toHaveCount(22);
    await page.getByRole("button", { name: "可互动", exact: true }).click();
    await expect(page.getByRole("article")).toHaveCount(4);
    await page.getByRole("button", { name: "外观参考", exact: true }).click();
    await expect(page.getByRole("article")).toHaveCount(7);
    await page.getByRole("button", { name: "外形与孔位", exact: true }).click();
    await expect(page.getByRole("article")).toHaveCount(11);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);

    await page.getByRole("button", { name: "按住星核板 A 键在 OLED 问好" }).click();
    const example = page.frameLocator("iframe");
    await expect(example.getByRole("button", { name: "按住板载 A 键" })).toBeEnabled();
    await page.getByRole("button", { name: "返回元件库" }).click();
    await page.getByRole("button", { name: "按住外接按钮，转旋钮调 RGB 灯色" }).click();
    const status = example.getByRole("status");
    const press = example.getByRole("button", { name: "按住外接按钮" });
    const lamp = example.locator("#rgb");
    await expect(status).toHaveText("灯已熄灭");
    const off = await frame(lamp);
    const box = await press.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await expect(status).toHaveText("灯已亮 · RGB 255 / 0 / 0");
    const red = await frame(lamp);
    expect(red).not.toBe(off);
    await page.mouse.up();
    await expect(status).toHaveText("灯已熄灭");
    expect(await frame(lamp)).toBe(off);
    await example.getByRole("button", { name: "保持按下" }).click();
    const slider = example.getByRole("slider", { name: "转动旋钮" });
    await slider.fill("2048");
    await expect(status).toHaveText("灯已亮 · RGB 0 / 255 / 0");
    await slider.press("End");
    await expect(status).toHaveText("灯已亮 · RGB 0 / 0 / 255");
    expect(await frame(lamp)).not.toBe(red);
    await example.getByRole("button", { name: "松开按钮" }).click();
    await expect(status).toHaveText("灯已熄灭");
    await example.getByRole("button", { name: "灯", exact: true }).click();
    await expect(example.getByRole("list", { name: "接线明细" })).toHaveText(
      /VCC → 3V3.*RED → P9.*GREEN → P15.*BLUE → P23/);
  });

for (const board of [
  { library: "arduino", mode: "firmware", pins: ["5V", "A0", "D3"], interactive: 4 },
  { library: "esp32", mode: "program-logic", pins: ["3V3", "GPIO34", "GPIO18"], interactive: 2 },
]) {
  test(board.library + " starter gallery opens its real knob program without network",
    async ({ page, context }, testInfo) => {
      const path = testInfo.outputPath("starter.html");
      execFileSync(process.env.CHATMAKER_TEST_PYTHON || "python",
        ["-m", "chatmaker.sim", "--library", board.library, "--output", path, "--progress", "none"]);
      await context.setOffline(true);
      await page.setViewportSize({ width: 390, height: 800 });
      await page.goto(pathToFileURL(path).href);
      await expect(page.getByRole("article")).toHaveCount(10);
      await expect(page.locator('article[data-status="interactive"]')).toHaveCount(board.interactive);
      await expect(page.locator('article[data-part="resistor-330"]')).toHaveAttribute("data-status", "wiring");
      for (const model of await page.locator(".art > :not(.oled)").all()) {
        expect(await model.evaluate(async element => {
          await element.updateComplete;
          return Boolean(element.shadowRoot?.querySelector("svg"));
        })).toBe(true);
      }
      await expect(page.locator(".art .oled .terminals span")).toHaveText(["VCC", "GND", "SDA", "SCL"]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
      await page.getByRole("button", { name: "转旋钮调 LED 亮度" }).click();
      const example = page.frameLocator("iframe");
      await expect(example.locator("html")).toHaveAttribute("data-simulation", board.mode);
      const slider = example.getByRole("slider", { name: "旋钮位置" });
      const status = example.getByRole("status");
      const lamp = example.locator("#lamp");
      const wiring = example.getByRole("list", { name: "接线明细" });
      for (const pin of board.pins) await expect(wiring).toContainText(pin);
      await expect(slider).toBeEnabled();
      await expect(status).toHaveText("LED 亮度 0%");
      await slider.fill("50");
      await expect.poll(() => lamp.evaluate(element => element.brightness)).toBeGreaterThan(.43);
      await expect.poll(() => lamp.evaluate(element => element.brightness)).toBeLessThan(.57);
      await slider.press("End");
      await expect(status).toHaveText("LED 亮度 100%");
      await slider.press("Home");
      await expect(status).toHaveText("LED 亮度 0%");
      expect(await lamp.evaluate(element => element.value)).toBe(false);
      await example.locator("#pot input").press("End");
      await expect(status).toHaveText("LED 亮度 100%");
      await page.getByRole("button", { name: "返回元件库" }).click();
      if (board.library === "esp32") {
        await page.getByRole("button", { name: "按住屏幕按钮问好" }).click();
        await expect(example.getByRole("status")).toHaveText("触屏已就绪。");
      } else {
        await page.getByRole("button", { name: "按住按钮在 OLED 显示你好" }).click();
        await expect(example.getByRole("button", { name: "运行仿真" })).toBeEnabled();
      }
    });
}

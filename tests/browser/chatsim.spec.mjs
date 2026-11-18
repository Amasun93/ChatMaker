import { readFile } from "node:fs/promises";
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
    engine, parts, firmware: firmware.toString("base64"), simulator };
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
  await expect(page.locator(".wire-list li")).toHaveText(["D2 → 图中按钮左上脚", "GND → 图中按钮左下脚"]);
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

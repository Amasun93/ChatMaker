import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";

const assets = new URL("../../runtime/chatmaker/sim_assets/", import.meta.url);

async function openSimulation(page, inverted) {
  const [template, engine, simulator] = await Promise.all(
    ["uno.html", "avr8js.js", "uno.js"].map((name) => readFile(new URL(name, assets), "utf8")),
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
    engine, firmware: firmware.toString("base64"), simulator };
  await page.goto("about:blank");
  await page.setContent(template.replace(/\$([a-z_0-9]+)/g, (_, name) => tokens[name]));
  await expect(page.getByRole("status")).toHaveText("固件仿真运行中");
}

async function wire(page, first, second) {
  await page.getByRole("button", { name: first, exact: true }).click();
  await page.getByRole("button", { name: second, exact: true }).click();
}

test("virtual UNO LED follows the provided AVR program", async ({ page, context }) => {
  await context.setOffline(true);
  for (const inverted of [false, true]) {
    await openSimulation(page, inverted);
    await wire(page, "主控板 D2", "按钮接点 1");
    await wire(page, "按钮接点 2", "主控板 GND");
    const led = page.locator("#led");
    const button = page.getByRole("button", { name: "按住按钮" });
    await expect(led).toHaveAttribute("data-led", inverted ? "on" : "off");
    await button.focus();
    await page.keyboard.down("Space");
    await expect(button).toHaveAttribute("aria-pressed", "true");
    await expect(led).toHaveAttribute("data-led", inverted ? "off" : "on");
    await page.keyboard.up("Space");
    await expect(led).toHaveAttribute("data-led", inverted ? "on" : "off");
  }
});

test("the switch needs two independent wires and unplugging breaks the circuit", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 740 });
  await openSimulation(page, false);
  const led = page.locator("#led");
  const switchButton = page.getByRole("button", { name: "按住按钮" });
  await wire(page, "主控板 D2", "按钮接点 1");
  await wire(page, "主控板 GND", "按钮接点 1");
  await expect(page.getByRole("button", { name: "主控板 D2" })).toHaveAttribute("data-connected", "false");
  await switchButton.hover();
  await page.mouse.down();
  await expect(switchButton).toHaveAttribute("aria-pressed", "true");
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await expect(led).toHaveAttribute("data-led", "off");
  await page.mouse.up();

  await wire(page, "主控板 D2", "按钮接点 2");
  await expect(page.locator("#wiring-status")).toContainText("两根线已接好");
  await switchButton.hover();
  await page.mouse.down();
  await expect(led).toHaveAttribute("data-led", "on");
  await page.mouse.up();
  await expect(led).toHaveAttribute("data-led", "off");

  await page.getByRole("button", { name: "清空接线" }).click();
  await expect(page.locator("#wiring-status")).toHaveText("接线已清空。");
  await switchButton.focus();
  await page.keyboard.down("Space");
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await expect(led).toHaveAttribute("data-led", "off");
  await page.keyboard.up("Space");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
});

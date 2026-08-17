import { expect, test } from "@playwright/test";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";


const pageUrl = (relativePath) => pathToFileURL(resolve(relativePath)).href;

function captureErrors(page) {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
  return errors;
}

async function expectPhoneReady(page, primaryControl) {
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    )
    .toBe(true);
  const bounds = await primaryControl.boundingBox();
  expect(bounds).not.toBeNull();
  expect(bounds.height).toBeGreaterThanOrEqual(44);
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(390);
}

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
});

test("classroom example records the primary signal on a phone", async ({ page }) => {
  const errors = captureErrors(page);
  await page.goto(pageUrl("examples/chatweb/classroom-pulse.html"));
  const primary = page.locator("#primary");

  await expectPhoneReady(page, primary);
  await expect(page.locator("#count")).toHaveText("0");
  await primary.click();
  await expect(page.locator("#count")).toHaveText("1");
  await expect(page.locator("#status")).toHaveText("已收到第 1 条信号");
  expect(errors).toEqual([]);
});

test("simulated hardware example labels its browser-only connection", async ({ page }) => {
  const errors = captureErrors(page);
  await page.goto(pageUrl("examples/chatweb/hardware-console.html"));
  const primary = page.locator("#primary");

  await expectPhoneReady(page, primary);
  await expect(page.locator("#status")).toHaveText("模拟设备未连接");
  await primary.click();
  await expect(page.locator("#status")).toHaveText("模拟设备已连接（仅浏览器演示）");
  await expect(page.locator(".card")).toHaveAttribute("data-mode", "simulation");
  expect(errors).toEqual([]);
});

test("ESP32 AP page exercises simulation without claiming hardware evidence", async ({ page }) => {
  const errors = captureErrors(page);
  await page.goto(pageUrl("examples/chatweb/esp32-ap-control.html"));
  const simulationMode = page.locator("#mode-simulation");
  const refresh = page.locator("#refresh-state");

  await expectPhoneReady(page, refresh);
  await simulationMode.click();
  await expect(page.locator("#app")).toHaveAttribute("data-mode", "simulation");
  await expect(page.locator(".mode-note")).toContainText("不代表 ESP32、Wi-Fi AP 或任何实物已经连接");
  await refresh.click();
  await expect(page.locator("#app")).toHaveAttribute("data-state", "connected");
  await expect(page.locator("#connection-status")).toHaveText("模拟预览已启动（非真实硬件）");
  await expect(page.locator("#led-control")).toBeEnabled();
  await page.locator("#led-control").click();
  await expect(page.locator("#connection-status")).toHaveText("模拟 LED 已更新（非真实硬件）");
  expect(errors).toEqual([]);
});

test("advanced playground compares and selects an expanded direction", async ({ page }) => {
  const errors = captureErrors(page);
  await page.goto(pageUrl("examples/chatweb/advanced-playground.html"));
  const primary = page.locator('[data-direction-id="field-notebook"]');

  await expectPhoneReady(page, primary);
  await primary.click();
  await expect(primary).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#selection-status")).toContainText("已选择：野外观察册");
  expect(errors).toEqual([]);
});

test("three mini-game patterns start, respond, and complete a playable loop", async ({ page }) => {
  const errors = captureErrors(page);

  await page.goto(pageUrl("examples/chatweb/game-reaction-rush.html"));
  await page.locator("#start").click();
  await page.locator(".target").click();
  await expect(page.locator("#score")).toHaveText("1");

  await page.goto(pageUrl("examples/chatweb/game-dodge-collect.html"));
  await page.locator("#start").click();
  await page.locator("#right").dispatchEvent("pointerdown");
  await page.waitForTimeout(100);
  await page.locator("#right").dispatchEvent("pointerup");
  await expect(page.locator("#timer")).not.toHaveText("--");

  await page.goto(pageUrl("examples/chatweb/game-drag-puzzle.html"));
  await page.locator("#start").click();
  for (const id of ["sun", "fish", "seed"]) {
    await page.locator(`[data-piece="${id}"]`).click();
    await page.locator(`[data-zone="${id}"]`).click();
  }
  await expect(page.locator("#stage")).toHaveAttribute("data-state", "ended");
  await expect(page.locator("#status")).toContainText("游戏结束");
  await page.locator("#start").click();
  await expect(page.locator("#score")).toHaveText("0");
  expect(errors).toEqual([]);
});

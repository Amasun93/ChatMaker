import { test, expect } from "@playwright/test";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const rally = pathToFileURL(resolve("skills/chatweb/assets/switchback-rally.html")).href;
test.use({ offline: true });

async function openRace(page) {
  const issues = [];
  page.on("pageerror", error => issues.push(error.message));
  page.on("console", message => { if (message.type() === "error") issues.push(message.text()); });
  page.on("request", request => { if (/^https?:/.test(request.url())) issues.push(request.url()); });
  await page.clock.install({ time: new Date("2025-01-01T00:00:00Z") });
  await page.clock.pauseAt(new Date("2025-01-01T00:00:01Z"));
  await page.goto(rally);
  await expect(page.getByRole("heading", { name: "赤线拉力" })).toBeVisible();
  return issues;
}

test("offline rally steers, pauses, jumps, changes cameras and records a lap", async ({ page }) => {
  test.setTimeout(90000);
  const issues = await openRace(page);
  const run = page.locator("#run"), wheel = page.getByRole("slider");
  await run.click();
  await page.keyboard.down("d");
  await page.clock.runFor(300);
  await page.keyboard.up("d");
  const lane = Number(await wheel.inputValue());
  expect(lane).toBeGreaterThan(45);
  await page.clock.runFor(150);
  expect(Number(await wheel.inputValue())).toBe(lane);
  await page.keyboard.press("Space");
  await expect(run).toHaveText("继续比赛");
  const paused = await page.locator("#time").textContent();
  await page.clock.runFor(500);
  await expect(page.locator("#time")).toHaveText(paused);
  await run.click();
  await page.clock.runFor(200);
  await expect(page.locator("#time")).not.toHaveText(paused);
  await page.getByRole("button", { name: "重新起跑" }).click();
  await expect(wheel).toHaveValue("0");
  await run.click();

  const sectors = new Set(), cameras = new Set(), surfaces = new Set();
  for (let i = 0; i < 125; i++) {
    await page.clock.runFor(240);
    const [section, camera, surface, lap] = await page.evaluate(() =>
      ["sector", "camera", "surface", "lap"].map(id => document.getElementById(id).textContent));
    sectors.add(section); cameras.add(camera); surfaces.add(surface);
    if (lap === "2") break;
  }
  expect([...sectors].sort()).toEqual(["码头", "采石场", "跨海桥"].sort());
  for (const shot of ["贴地追车", "高位看弯", "斜后追拍", "空中侧拍"]) expect(cameras.has(shot)).toBe(true);
  for (const effect of ["箭头带加速", "碎石减速", "四轮落地"]) expect(surfaces.has(effect)).toBe(true);
  await expect(page.locator("#lap")).toHaveText("2");
  await expect(page.locator("#best")).toHaveText(/^\d+\.\d\d s$/);
  await page.getByRole("button", { name: "重新起跑" }).click();
  await expect(page.locator("#best")).toHaveText("—");
  await expect(page.locator("#time")).toHaveText("0.00 s");
  expect(issues).toEqual([]);
});

test.describe("mobile rally", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, contextOptions: { reducedMotion: "reduce" } });

  test("touch steering changes the line and the stable camera still reports takeoff", async ({ page }) => {
    const issues = await openRace(page);
    await page.getByRole("button", { name: "开始比赛" }).tap();
    const wheel = page.getByRole("slider"), box = await wheel.boundingBox();
    expect(box.height).toBeGreaterThanOrEqual(44);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
    await page.touchscreen.tap(box.x + box.width * .64, box.y + box.height / 2);
    expect(Number(await wheel.inputValue())).toBeGreaterThan(15);
    await page.clock.runFor(100);
    await page.touchscreen.tap(box.x + box.width * .5, box.y + box.height / 2);
    expect(Math.abs(Number(await wheel.inputValue()))).toBeLessThan(3);
    let jumped = false;
    for (let i = 0; i < 30; i++) {
      await page.clock.runFor(200);
      if ((await page.locator("#surface").textContent()).includes("翻滚")) { jumped = true; break; }
    }
    expect(jumped).toBe(true);
    await expect(page.locator("#camera")).toHaveText("稳定追车");
    await page.getByRole("button", { name: "音效：关" }).tap();
    await expect(page.locator("#audio")).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "音效：开" }).tap();
    await expect(page.locator("#audio")).toHaveAttribute("aria-pressed", "false");
    expect(issues).toEqual([]);
  });
});

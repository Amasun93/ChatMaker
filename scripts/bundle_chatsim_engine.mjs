import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const assets = new URL("../runtime/chatmaker/sim_assets/", import.meta.url);
const resolveDir = fileURLToPath(new URL("../", import.meta.url));

async function thirdPartyNotice(name) {
  const pkg = new URL(`../node_modules/${name}/`, import.meta.url);
  const license = await readFile(new URL("LICENSE", pkg), "utf8");
  const { version } = JSON.parse(await readFile(new URL("package.json", pkg), "utf8"));
  return `/*! ${name} ${version}\n${license.trim()}\n*/`;
}

async function bundle(filename, contents, packages, globalName) {
  const notices = await Promise.all(packages.map(thirdPartyNotice));
  const { outputFiles } = await build({
    stdin: { contents, resolveDir },
    bundle: true,
    platform: "browser",
    format: "iife",
    globalName,
    target: "es2020",
    // Escape line breaks inside the component templates while preserving their contents.
    supported: { "template-literal": false },
    minify: true,
    write: false,
    banner: { js: notices.join("\n") },
  });
  await writeFile(new URL(filename, assets), outputFiles[0].text);
}

await bundle("avr8js.js", `
  export { CPU, avrInstruction, AVRIOPort, PinState, portBConfig, portCConfig, portDConfig,
    AVRTimer, timer0Config, timer1Config, timer2Config, AVRUSART, usart0Config } from "avr8js";
`, ["avr8js"], "ChatSimAVR");

await bundle("wokwi-parts.js", `
  import "@wokwi/elements/dist/esm/arduino-uno-element.js";
  import "@wokwi/elements/dist/esm/pushbutton-element.js";
`, ["@wokwi/elements", "lit", "lit-element", "lit-html", "@lit/reactive-element"]);

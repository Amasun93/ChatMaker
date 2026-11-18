import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const pkg = new URL("../node_modules/avr8js/", import.meta.url);
const assets = new URL("../runtime/chatmaker/sim_assets/", import.meta.url);
const license = await readFile(new URL("LICENSE", pkg), "utf8");
const { version } = JSON.parse(await readFile(new URL("package.json", pkg), "utf8"));
const { outputFiles } = await build({
  stdin: {
    contents: `export { CPU, avrInstruction, AVRIOPort, PinState, portBConfig, portCConfig, portDConfig,
      AVRTimer, timer0Config, timer1Config, timer2Config, AVRUSART, usart0Config } from "avr8js";`,
    resolveDir: fileURLToPath(new URL("../", import.meta.url)),
  },
  bundle: true,
  platform: "browser",
  format: "iife",
  globalName: "ChatSimAVR",
  target: "es2020",
  minify: true,
  write: false,
  banner: { js: `/*! AVR8js ${version} | https://github.com/wokwi/avr8js\n${license.trim()}\n*/` },
});
await writeFile(new URL("avr8js.js", assets), outputFiles[0].text);

"use strict";

const fs = require("node:fs");
const path = require("node:path");
// microbit-fs 0.10.0's public constructor rejects the official 2.1.1 image
// even though its filesystem reader reports no user files. The pinned package's
// builder is the same implementation used by that constructor and lets us
// explicitly replace the filesystem with one checked main.py.
const builder = require(path.join(
  __dirname,
  "node_modules",
  "@microbit",
  "microbit-fs",
  "dist",
  "cjs",
  "micropython-fs-builder.js"
));

const [runtimePath, sourcePath, outputPath] = process.argv.slice(2);
if (!runtimePath || !sourcePath || !outputPath) {
  throw new Error("usage: package_hex.cjs <runtime.hex> <main.py> <output.hex>");
}

const runtimeHex = fs.readFileSync(runtimePath, "utf8");
const source = fs.readFileSync(sourcePath, "utf8");
const cache = builder.createMpFsBuilderCache(runtimeHex);
const outputHex = builder.generateHexWithFiles(cache, {
  "main.py": Buffer.from(source, "utf8")
});
const packagedFiles = builder.getIntelHexFiles(outputHex);
if (!packagedFiles["main.py"] || Buffer.from(packagedFiles["main.py"]).toString("utf8") !== source) {
  throw new Error("packaged_source_roundtrip_mismatch");
}
fs.writeFileSync(outputPath, outputHex, "utf8");
process.stdout.write(JSON.stringify({
  success: true,
  sourceBytes: Buffer.byteLength(source, "utf8"),
  outputBytes: Buffer.byteLength(outputHex, "utf8")
}));

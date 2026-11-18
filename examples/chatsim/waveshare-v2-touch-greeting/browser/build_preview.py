"""Build the Waveshare V2 ChatSim example as a self-contained browser page."""

import argparse
import base64
from html import escape
from pathlib import Path
from string import Template
import subprocess
import tempfile

BROWSER = Path(__file__).resolve().parent
SKETCH = BROWSER.parent
ROOT = SKETCH.parents[2]
EXPORTS = ("demo_start", "demo_pixels", "demo_generation", "demo_pointer", "demo_key")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig", required=True, type=Path, help="Zig 0.15.2 executable")
    parser.add_argument("--lvgl", required=True, type=Path, help="LVGL 8.3.10 source directory")
    parser.add_argument("--output", type=Path, help="Path to the standalone HTML")
    parser.add_argument("--wasm-output", type=Path, help="Path to the demo module for ChatSim")
    args = parser.parse_args()
    if args.output is None and args.wasm_output is None:
        parser.error("choose --output or --wasm-output")

    lvgl = args.lvgl.resolve()
    header = (lvgl / "lvgl.h").read_text(encoding="utf-8")
    expected = {"MAJOR": 8, "MINOR": 3, "PATCH": 10}
    if any(f"#define LVGL_VERSION_{key} {value}\n" not in header for key, value in expected.items()):
        parser.error("--lvgl must point to LVGL 8.3.10, matching the Waveshare board libraries")

    lvgl_sources = sorted(str(path.relative_to(lvgl)) for path in (lvgl / "src").rglob("*.c"))
    demo_sources = sorted(str(path) for path in SKETCH.glob("*.c"))
    with tempfile.TemporaryDirectory(prefix="chatsim-touch-") as tmp:
        wasm = Path(tmp) / "touch.wasm"
        subprocess.run(
            [str(args.zig.resolve()), "cc", "-target", "wasm32-wasi", "-mexec-model=reactor", "-Os", "-s",
             "-DLV_CONF_SKIP=1", "-DLV_COLOR_DEPTH=32", "-DLV_USE_THEME_DEFAULT=0",
             "-I", ".", "-I", str(SKETCH), *(f"-Wl,--export={name}" for name in EXPORTS),
             str(BROWSER / "port.c"), *demo_sources, *lvgl_sources, "-o", str(wasm)],
            cwd=lvgl, check=True,
        )
        compiled = wasm.read_bytes()

    if args.wasm_output is not None:
        args.wasm_output.parent.mkdir(parents=True, exist_ok=True)
        args.wasm_output.write_bytes(compiled)
        print(args.wasm_output.resolve())
    if args.output is None:
        return
    font_license = ROOT / "runtime/chatmaker/cad/assets/OFL-1.1.txt"
    notices = (lvgl / "LICENCE.txt").read_text(encoding="utf-8") + "\n\n" + font_license.read_text(encoding="utf-8")
    template = Template((ROOT / "runtime/chatmaker/sim_assets/waveshare-touch.html").read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(template.substitute(wasm=base64.b64encode(compiled).decode("ascii"), notices=escape(notices)),
                           encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__":
    main()

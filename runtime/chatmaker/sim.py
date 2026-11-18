"""Open a ChatSim example or component library, or compile an UNO R3 sketch for simulation."""
from __future__ import annotations

import argparse
import base64
from hashlib import sha256
from html import escape
from importlib.resources import files
import json
from pathlib import Path
from string import Template
import tempfile
import webbrowser

from .hardware.workflow import run_project
from .progress import emit, reporting
from .runtime_info import identity
from .sim_catalog import ASSETS, STARCORE_BOARD, load_catalog, load_starcore_modules

BOARD_ID = "arduino-uno-r3"
FLASH_BYTES = 32 * 1024
CIRCUITS = ("button-led", "button-oled")


def read_avr_hex(text: str) -> bytes:
    flash = bytearray(b"\xff" * FLASH_BYTES)
    base = used = 0
    end = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if end or not line.startswith(":"):
            raise ValueError("invalid_avr_hex_record")
        record = bytes.fromhex(line[1:])
        if len(record) < 5 or record[0] != len(record) - 5 or sum(record) % 256:
            raise ValueError("invalid_avr_hex_checksum_or_length")
        address = int.from_bytes(record[1:3], "big")
        kind, data = record[3], record[4:-1]
        if kind == 0:
            start = base + address
            stop = start + len(data)
            if stop > len(flash):
                raise ValueError("firmware_exceeds_uno_flash")
            flash[start:stop] = data
            used = max(used, stop)
        elif kind == 1 and not address and not data:
            end = True
        elif kind in (2, 4) and not address and len(data) == 2:
            base = int.from_bytes(data, "big") << (4 if kind == 2 else 16)
        else:
            raise ValueError("unsupported_avr_hex_record")
    if not end or not used:
        raise ValueError("incomplete_avr_hex")
    return bytes(flash[:used])


def render_preview(
    firmware_path: Path, *, runtime_root: Path, output: Path | None, circuit: str = "button-led"
) -> dict:
    return render_avr_preview(firmware_path.read_bytes(), firmware_path.name, runtime_root=runtime_root,
                              output=output, circuit=circuit)


def render_avr_preview(original: bytes, name: str, *, runtime_root: Path, output: Path | None, circuit: str) -> dict:
    digest = sha256(original).hexdigest()
    firmware = read_avr_hex(original.decode("ascii"))
    assets = files("chatmaker").joinpath("sim_assets")
    oled = circuit == "button-oled"
    html = Template(assets.joinpath("uno.html").read_text(encoding="utf-8")).substitute(
        circuit=escape(circuit),
        lesson="UNO R3 按钮与小屏幕" if oled else "UNO R3 按钮亮灯",
        intro="试按外接按钮，观察 OLED 上的文字。" if oled else "试按外接按钮，观察 D13 板载灯。",
        button_ground="GND.1" if oled else "GND.2",
        ground_leg="2.r" if oled else "2.l",
        ground_label="图中按钮右下脚" if oled else "图中按钮左下脚",
        sketch=escape(name),
        sha256=digest,
        short_hash=digest[:12],
        engine=assets.joinpath("avr8js.js").read_text(encoding="utf-8"),
        parts=assets.joinpath("wokwi-parts.js").read_text(encoding="utf-8"),
        oled_model=assets.joinpath("ssd1306.js").read_text(encoding="utf-8") if oled else "",
        firmware=base64.b64encode(firmware).decode("ascii"),
        simulator=assets.joinpath("uno.js").read_text(encoding="utf-8"),
    )
    return {**save_preview(html, runtime_root, output), "firmware_sha256": digest}


def save_preview(html: str, runtime_root: Path, output: Path | None) -> dict:
    if output is None:
        previews = runtime_root / "previews" / "chatsim"
        previews.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix="preview-", dir=previews)) / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep an existing preview usable if generating a replacement is interrupted.
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".tmp", delete=False) as stream:
        staging = Path(stream.name)
        try:
            stream.write(html.encode("utf-8"))
        except BaseException:
            stream.close()
            staging.unlink(missing_ok=True)
            raise
    try:
        staging.replace(output)
    finally:
        staging.unlink(missing_ok=True)
    return {"path": str(output), "url": output.as_uri()}


def open_preview(state: dict, preview: dict, open_browser: bool) -> dict:
    dispatched = False
    if open_browser:
        try:
            dispatched = webbrowser.open(preview["url"], new=2)
        except (OSError, webbrowser.Error):
            pass
    return {**state, "success": True, "stage": "preview-ready", "preview_ready": True, "preview": preview,
            "browser_requested": open_browser, "browser_dispatched": dispatched}


def inline_json(data) -> str:
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def read_asset(name: str) -> str:
    return ASSETS.joinpath(name).read_text(encoding="utf-8")


def render_wasm_demo(demo: dict, program: bytes) -> str:
    tokens = {"wasm": base64.b64encode(program).decode("ascii")}
    if demo.get("artwork"):
        tokens["artwork"] = read_asset(demo["artwork"])
    if demo.get("module_artwork"):
        parts = [part for part in load_starcore_modules() if part["id"] in demo["parts"]]
        tokens.update(module_artwork=read_asset(demo["module_artwork"]),
                      module_data=inline_json(parts), wiring=inline_json(demo["wiring"]))
    if "lvgl" in demo.get("notices", []):
        font = files("chatmaker").joinpath("cad", "assets", "OFL-1.1.txt").read_text(encoding="utf-8")
        tokens["notices"] = escape(read_asset("lvgl-license.txt") + "\n\n" + font)
    return Template(read_asset(demo["template"])).substitute(tokens)


def run_library(library: str, *, runtime_root: Path, output: Path | None, open_browser: bool) -> dict:
    catalog = load_catalog()
    state = {"success": False, "action": "library", "library": library, "board_id": STARCORE_BOARD,
             "chatsim_version": catalog["chatsim_version"], "code_compiled": False,
             "preview_ready": False, "firmware_uploaded": False, "physical_effect_verified": False}
    if library != "starcore":
        return {**state, "stage": "source", "error": "unknown_simulation_library"}
    if output is not None and output.suffix.lower() != ".html":
        return {**state, "stage": "preview", "error": "output_requires_html_extension"}
    modules = load_starcore_modules()
    examples = []
    try:
        for demo in catalog["demos"]:
            if demo["board"] != STARCORE_BOARD:
                continue
            program = ASSETS.joinpath(demo["program"]).read_bytes()
            page = render_wasm_demo(demo, program)
            examples.append({**{key: demo[key] for key in ("id", "name", "parts")},
                             "html": base64.b64encode(page.encode("utf-8")).decode("ascii")})
        html = Template(read_asset("starcore-library.html")).substitute(
            version=catalog["chatsim_version"],
            artwork=read_asset("starcore-board.js"),
            module_artwork=read_asset("starcore-components.js"),
            module_data=inline_json(modules),
            examples=inline_json(examples),
        )
        preview = save_preview(html, runtime_root, output)
    except (OSError, ValueError) as exc:
        return {**state, "stage": "preview", "error": str(exc)}
    return open_preview({**state, "module_count": len(modules), "demos": [entry["id"] for entry in examples]},
                        preview, open_browser)


def run_demo(demo_id: str, *, runtime_root: Path, output: Path | None, open_browser: bool) -> dict:
    state = {"success": False, "action": "demo", "demo": demo_id, "code_compiled": False,
             "preview_ready": False, "firmware_uploaded": False, "physical_effect_verified": False}
    demo = next((entry for entry in load_catalog()["demos"] if entry["id"] == demo_id), None)
    if demo is None:
        return {**state, "stage": "source", "error": "unknown_simulation_demo"}
    state.update(board_id=demo["board"], simulation_mode=demo["mode"], parts=demo["parts"])
    if output is not None and output.suffix.lower() != ".html":
        return {**state, "stage": "preview", "error": "output_requires_html_extension"}
    try:
        program = ASSETS.joinpath(demo["program"]).read_bytes()
        if demo["mode"] == "firmware":
            preview = render_avr_preview(program, f"{demo_id}.ino.hex", runtime_root=runtime_root,
                                         output=output, circuit=demo["circuit"])
        else:
            preview = save_preview(render_wasm_demo(demo, program), runtime_root, output)
            preview["program_sha256"] = sha256(program).hexdigest()
    except (OSError, ValueError) as exc:
        return {**state, "stage": "preview", "error": str(exc)}
    return open_preview({**state, "uses_precompiled_program": True}, preview, open_browser)


def run_simulation(
    sketch: Path, *, runtime_root: Path, output: Path | None, open_browser: bool, circuit: str = "button-led"
) -> dict:
    state = {"success": False, "action": "simulate", "board_id": BOARD_ID, "code_compiled": False,
             "preview_ready": False, "firmware_uploaded": False, "physical_effect_verified": False,
             "circuit": circuit, "simulation_mode": "firmware"}
    if circuit not in CIRCUITS:
        return {**state, "stage": "source", "error": "unsupported_simulation_circuit"}
    source = sketch.resolve()
    folder = source if source.is_dir() else source.parent
    main_file = folder / (folder.name + ".ino")
    if (source not in (folder, main_file)) or not main_file.is_file():
        return {**state, "stage": "source", "error": "sketch_directory_with_matching_ino_required"}
    if output is not None and output.suffix.lower() != ".html":
        return {**state, "stage": "preview", "error": "output_requires_html_extension"}

    request = {"board_id": BOARD_ID, "sketch": str(folder)}
    doctor = run_project({**request, "action": "doctor"})
    if not doctor.get("ready_for_compile"):
        prepared = run_project({**request, "action": "prepare-environment"})
        if not prepared.get("success"):
            return {**state, "stage": "prepare", "environment": prepared}
    result = run_project({**request, "action": "compile"})
    if not result.get("success"):
        return {**state, "stage": "compile", "compile": result.get("compile") or result}

    compiled = result["compile"]
    firmware = Path(compiled["build_path"]) / (main_file.name + ".hex")
    state.update(code_compiled=True, compile=compiled)
    try:
        emit("stage", stage="preview", message="正在生成运行这份固件的浏览器预览")
        preview = render_preview(firmware, runtime_root=runtime_root, output=output, circuit=circuit)
    except (OSError, ValueError) as exc:
        return {**state, "stage": "preview", "error": str(exc)}

    return open_preview(state, preview, open_browser)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    entry = parser.add_mutually_exclusive_group(required=True)
    entry.add_argument("--sketch", type=Path, help="Compile a custom UNO R3 sketch")
    entry.add_argument("--demo", help="Open a bundled demo by ID")
    entry.add_argument("--library", choices=("starcore",), help="Open a board's component library")
    entry.add_argument("--list", action="store_true", help="List boards, parts and bundled demos")
    entry.add_argument("--version", action="store_true")
    parser.add_argument("--circuit", choices=CIRCUITS, default="button-led", help="Virtual UNO R3 circuit")
    parser.add_argument("--output", type=Path, help="Optional path to the generated HTML")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument("--expect-revision")
    parser.add_argument("--progress", choices=("human", "jsonl", "none"), default="human")
    args = parser.parse_args(argv)
    info = identity()
    if args.expect_revision and args.expect_revision != info["source_commit"]:
        result = {"success": False, "error": "source_revision_mismatch"}
    elif args.version:
        result = {"success": True, "action": "version", "board_id": BOARD_ID,
                  "chatsim_version": load_catalog()["chatsim_version"]}
    elif args.list:
        result = {"success": True, "action": "list", **load_catalog()}
    else:
        output = args.output.expanduser().resolve() if args.output else None
        runtime_root = Path(info["runtime_root"])
        with reporting(args.progress):
            if args.demo is not None:
                result = run_demo(args.demo, runtime_root=runtime_root, output=output, open_browser=args.open_browser)
            elif args.library is not None:
                result = run_library(args.library, runtime_root=runtime_root, output=output,
                                     open_browser=args.open_browser)
            else:
                result = run_simulation(args.sketch.expanduser(), runtime_root=runtime_root, output=output,
                                        open_browser=args.open_browser, circuit=args.circuit)
    print(json.dumps({**result, "runtime": info}, ensure_ascii=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Compile an Arduino UNO R3 sketch into a self-contained ChatSim preview."""
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

BOARD_ID = "arduino-uno-r3"
FLASH_BYTES = 32 * 1024


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


def render_preview(firmware_path: Path, *, runtime_root: Path, output: Path | None) -> dict:
    original = firmware_path.read_bytes()
    digest = sha256(original).hexdigest()
    firmware = read_avr_hex(original.decode("ascii"))
    assets = files("chatmaker").joinpath("sim_assets")
    html = Template(assets.joinpath("uno.html").read_text(encoding="utf-8")).substitute(
        sketch=escape(firmware_path.name),
        sha256=digest,
        short_hash=digest[:12],
        engine=assets.joinpath("avr8js.js").read_text(encoding="utf-8"),
        firmware=base64.b64encode(firmware).decode("ascii"),
        simulator=assets.joinpath("uno.js").read_text(encoding="utf-8"),
    )
    if output is None:
        previews = runtime_root / "previews" / "chatsim"
        previews.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix="uno-", dir=previews)) / "index.html"
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
    return {"path": str(output), "url": output.as_uri(), "firmware_sha256": digest}


def run_simulation(sketch: Path, *, runtime_root: Path, output: Path | None, open_browser: bool) -> dict:
    state = {"success": False, "action": "simulate", "board_id": BOARD_ID, "code_compiled": False,
             "preview_ready": False, "firmware_uploaded": False, "physical_effect_verified": False}
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
        preview = render_preview(firmware, runtime_root=runtime_root, output=output)
    except (OSError, ValueError) as exc:
        return {**state, "stage": "preview", "error": str(exc)}

    dispatched = False
    if open_browser:
        try:
            dispatched = webbrowser.open(preview["url"], new=2)
        except (OSError, webbrowser.Error):
            pass
    return {**state, "success": True, "stage": "preview-ready", "preview_ready": True, "preview": preview,
            "browser_requested": open_browser, "browser_dispatched": dispatched}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sketch", type=Path)
    parser.add_argument("--output", type=Path, help="Optional path to the generated HTML")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--expect-revision")
    parser.add_argument("--progress", choices=("human", "jsonl", "none"), default="human")
    args = parser.parse_args(argv)
    info = identity()
    if args.expect_revision and args.expect_revision != info["source_commit"]:
        result = {"success": False, "error": "source_revision_mismatch"}
    elif args.version:
        result = {"success": True, "action": "version", "board_id": BOARD_ID}
    elif args.sketch is None:
        parser.error("--sketch is required unless using --version")
    else:
        with reporting(args.progress):
            result = run_simulation(args.sketch.expanduser(), runtime_root=Path(info["runtime_root"]),
                                    output=args.output.expanduser().resolve() if args.output else None,
                                    open_browser=args.open_browser)
    print(json.dumps({**result, "runtime": info}, ensure_ascii=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Mind+ 1.8 bridge for IDMC-0001 Starcore v4.2.2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

from . import nano_mindplus as shared


BRIDGE_NAME = "starcore-mindplus"
SCHEMA_VERSION = 1
BOARD_ID = "idmc-0001-starcore-v4-2-2"
CURRENT_FQBN = "dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none"
HISTORICAL_FQBN = "mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none"


def _current_context() -> dict[str, Any] | None:
    for installation in shared.discover_installations():
        if installation.get("backend") != "mindplus-1-builder":
            continue
        root = Path(str(installation["root"]))
        arduino = root / "Arduino"
        board_file = arduino / "hardware" / "dfrobot" / "mpython" / "boards.txt"
        if Path(str(installation["builder"])).is_file() and board_file.is_file():
            return {**installation, "arduino": str(arduino), "boards": str(board_file)}
    return None


def _safe_name(value: str) -> str:
    return (re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-") or "starcore-project")[:48]


def _prepare_code(code: str, name: str) -> Path:
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code_required")
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]
    folder = Path(tempfile.gettempdir()) / "starcore-mindplus-sketches" / f"{_safe_name(name)}-{digest}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{folder.name}.ino").write_text(code, encoding="utf-8")
    return folder


def build_compile_command(context: dict[str, Any], sketch: Path, build: Path) -> list[str]:
    arduino = Path(str(context["arduino"]))
    return [
        str(context["builder"]),
        "-compile",
        "-logger=machine",
        "-hardware", str(arduino / "hardware"),
        "-tools", str(arduino / "arduino-builder"),
        "-tools", str(arduino / "hardware" / "tools" / "avr"),
        "-tools", str(arduino / "hardware" / "tools" / "mpython"),
        "-built-in-libraries", str(arduino / "libraries"),
        "-libraries", str(arduino / "libraries"),
        f"-fqbn={CURRENT_FQBN}",
        "-ide-version=10819",
        "-build-path", str(build),
        str(sketch),
    ]


def compile_result(context: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    try:
        if request.get("code") is not None:
            folder = _prepare_code(request["code"], request.get("project_name", "starcore-project"))
        elif request.get("sketch"):
            raw = Path(str(request["sketch"])).expanduser().resolve()
            folder = raw.parent if raw.is_file() else raw
            if not folder.is_dir() or not (folder / f"{folder.name}.ino").is_file():
                return {"action": "compile", "success": False, "error": "arduino_sketch_missing"}
        else:
            return {"action": "compile", "success": False, "error": "sketch_or_code_required"}
    except (OSError, ValueError) as exc:
        return {"action": "compile", "success": False, "error": str(exc)}

    build = Path(tempfile.gettempdir()) / "starcore-mindplus-builds" / hashlib.sha256(str(folder).encode()).hexdigest()[:12]
    build.mkdir(parents=True, exist_ok=True)
    execution = shared._run(
        build_compile_command(context, folder / f"{folder.name}.ino", build),
        timeout=int(request.get("timeout", 900)),
    )
    application = sorted(build.glob("*.bin"))
    partitions = sorted(build.glob("*.partitions.bin"))
    success = execution.get("returncode") == 0 and bool(application) and bool(partitions)
    result = {
        "action": "compile", "success": success, "board": BOARD_ID,
        "fqbn": CURRENT_FQBN, "historical_fqbn": HISTORICAL_FQBN,
        "sketch": str(folder), "build_dir": str(build),
        "application_bin": str(application[0]) if application else None,
        "partitions_bin": str(partitions[0]) if partitions else None,
        "execution": execution,
    }
    if not success:
        result["error"] = "compile_failed"
        result["diagnostics"] = shared._compile_diagnostics(execution)
    return result


def scan_ports() -> list[dict[str, Any]]:
    return shared.scan_ports()


def _select_port(request: dict[str, Any]) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    ports = scan_ports()
    if not request.get("board_confirmed"):
        return None, "starcore_identity_confirmation_required", ports
    eligible = [p for p in ports if p.get("eligible_for_upload")]
    requested = str(request.get("port", "")).upper()
    if requested:
        match = next((p for p in eligible if str(p.get("address", "")).upper() == requested), None)
        return (requested, None, ports) if match else (None, "upload_port_not_eligible", ports)
    if len(eligible) == 1:
        return str(eligible[0]["address"]).upper(), None, ports
    if not eligible:
        return None, "no_wired_upload_port_found", ports
    return None, "multiple_wired_ports_require_selection", ports


def upload_result(context: dict[str, Any], request: dict[str, Any], compiled: dict[str, Any]) -> dict[str, Any]:
    port, error, ports = _select_port(request)
    if error or not port:
        return {"action": "upload", "success": False, "error": error, "upload_executed": False, "ports": ports}
    arduino = Path(str(context["arduino"]))
    tool = arduino / "hardware" / "tools" / "mpython" / "esptool.exe"
    platform = arduino / "hardware" / "dfrobot" / "mpython"
    application = Path(str(compiled["application_bin"]))
    partitions = Path(str(compiled["partitions_bin"]))
    command = [
        str(tool), "--chip", "esp32", "--port", port, "--baud", "1500000",
        "--before", "default_reset", "--after", "hard_reset", "write_flash", "-z",
        "--flash_mode", "dio", "--flash_freq", "80m", "--flash_size", "detect",
        "0xe000", str(platform / "tools" / "partitions" / "boot_app0.bin"),
        "0x1000", str(platform / "tools" / "sdk" / "bin" / "bootloader_dio_80m.bin"),
        "0x10000", str(application), "0x8000", str(partitions),
    ]
    execution = shared._run(command, timeout=int(request.get("upload_timeout", 300)))
    success = execution.get("returncode") == 0
    return {
        "action": "upload", "success": success, "upload_executed": True,
        "firmware_written": success, "hardware_runtime_verified": False,
        "board": BOARD_ID, "port": port, "execution": execution,
        **({} if success else {"error": "upload_failed"}),
    }


def compile_upload_result(context: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    compiled = compile_result(context, request)
    if not compiled.get("success"):
        return {"action": "compile-upload", "success": False, "stage": "compile", "compile": compiled, "upload": None}
    uploaded = upload_result(context, request, compiled)
    if uploaded.get("success"):
        stage = "complete"
    elif uploaded.get("error") in {"no_wired_upload_port_found", "starcore_identity_confirmation_required"}:
        stage = "awaiting-hardware"
    else:
        stage = "upload"
    return {
        "action": "compile-upload", "success": bool(uploaded.get("success")), "stage": stage,
        "compile": compiled, "upload": uploaded,
        "hardware_connection_required": stage == "awaiting-hardware",
    }


def doctor_result() -> dict[str, Any]:
    context = _current_context()
    ports = scan_ports()
    return {
        "action": "doctor", "success": context is not None, "ready_for_compile": context is not None,
        "ready_for_upload": context is not None and bool([p for p in ports if p.get("eligible_for_upload")]),
        "board": BOARD_ID, "current_fqbn": CURRENT_FQBN, "historical_fqbn": HISTORICAL_FQBN,
        "environment": context, "ports": ports,
    }


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action == "doctor":
        result = doctor_result()
    elif action == "ports":
        result = {"action": "ports", "success": True, "board": BOARD_ID, "ports": scan_ports()}
    elif action in {"compile", "compile-upload"}:
        context = _current_context()
        if not context:
            result = {"action": action, "success": False, "error": "mindplus_1_starcore_toolchain_missing"}
        elif action == "compile":
            result = compile_result(context, request)
        else:
            result = compile_upload_result(context, request)
    else:
        raise ValueError("action_must_be_doctor_ports_compile_or_compile-upload")
    result.setdefault("bridge", BRIDGE_NAME)
    result.setdefault("schema_version", SCHEMA_VERSION)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Starcore Mind+ bridge")
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args(argv)
    try:
        result = execute_request(json.loads(args.request_json))
    except Exception as exc:
        result = {"success": False, "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

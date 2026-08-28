#!/usr/bin/env python3
"""Compile and upload bridge for IDMC-0001 Starcore v4.2.2.

ChatMaker's isolated managed toolchain is preferred. Existing Mind+ 2.x and
1.x environments remain compatibility fallbacks.
"""

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
from . import mpython_flash
from . import starcore_toolchain as managed


BRIDGE_NAME = "chatmaker-starcore"
SCHEMA_VERSION = 1
BOARD_ID = "idmc-0001-starcore-v4-2-2"
V2_FQBN = "mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none"
V1_FQBN = "dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none"
CURRENT_FQBN = V2_FQBN
FALLBACK_FQBN = V1_FQBN
FAST_UPLOAD_BAUD = 1500000
SAFE_UPLOAD_BAUD = 115200


def _current_context() -> dict[str, Any] | None:
    managed_environment = managed.managed_context()
    if managed_environment:
        return {**managed_environment, "fqbn": V2_FQBN}
    installations = shared.discover_installations()
    for installation in sorted(
        installations,
        key=lambda item: 0 if item.get("backend") == "mindplus-2-cli" else 1,
    ):
        backend = installation.get("backend")
        if backend == "mindplus-2-cli":
            cli = Path(str(installation.get("cli", "")))
            config = Path(str(installation.get("config", "")))
            if cli.is_file() and config.is_file():
                return {**installation, "fqbn": V2_FQBN}
        elif backend == "mindplus-1-builder":
            root = Path(str(installation["root"]))
            arduino = root / "Arduino"
            board_file = arduino / "hardware" / "dfrobot" / "mpython" / "boards.txt"
            if Path(str(installation["builder"])).is_file() and board_file.is_file():
                return {
                    **installation,
                    "arduino": str(arduino),
                    "boards": str(board_file),
                    "fqbn": V1_FQBN,
                }
    return None


def _safe_name(value: str) -> str:
    return (re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-") or "starcore-project")[:48]


def _prepare_code(code: str, name: str) -> Path:
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code_required")
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]
    folder = Path(tempfile.gettempdir()) / "chatmaker-starcore-sketches" / f"{_safe_name(name)}-{digest}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{folder.name}.ino").write_text(code, encoding="utf-8")
    return folder


def build_compile_command(context: dict[str, Any], sketch: Path, build: Path) -> list[str]:
    if context.get("backend") in {managed.BACKEND, "mindplus-2-cli"}:
        return [
            str(context["cli"]),
            "compile",
            "--config-file", str(context["config"]),
            "--no-color",
            "--fqbn", V2_FQBN,
            "--build-path", str(build),
            str(sketch.parent),
        ]
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
        f"-fqbn={V1_FQBN}",
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

    build = Path(tempfile.gettempdir()) / "chatmaker-starcore-builds" / hashlib.sha256(str(folder).encode()).hexdigest()[:12]
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
        "backend": context["backend"], "fqbn": str(context["fqbn"]),
        "preferred_fqbn": V2_FQBN, "fallback_fqbn": V1_FQBN,
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


def _upload_diagnostics(execution: dict[str, Any]) -> dict[str, Any]:
    raw = "\n".join(
        value for value in (execution.get("stdout", ""), execution.get("stderr", "")) if value
    )
    lowered = raw.lower()
    if "permissionerror" in lowered:
        return {
            "error_type": "high_baud_port_error",
            "retry_at_115200": True,
            "teacher_message": "高速串口打开失败，ChatMaker 将自动降到 115200 再试一次。",
            "diagnostic_excerpt": raw[-12000:],
        }
    if any(
        marker in lowered
        for marker in (
            "invalid head of packet",
            "wrong boot mode",
            "timed out waiting for packet header",
        )
    ):
        return {
            "error_type": "manual_download_mode_required",
            "retry_at_115200": False,
            "next_action": "hold_a_tap_rst_then_retry",
            "teacher_message": (
                "星核板没有进入下载模式。请按住板载 A 键，短按一下 RST，"
                "松开 RST 后再松开 A 键，然后让我重试上传。"
            ),
            "diagnostic_excerpt": raw[-12000:],
        }
    return {
        "error_type": "upload_failed",
        "retry_at_115200": False,
        "teacher_message": "上传失败；请保留这段错误，并检查端口是否被其他软件占用。",
        "diagnostic_excerpt": raw[-12000:],
    }


def upload_result(
    context: dict[str, Any],
    request: dict[str, Any],
    compiled: dict[str, Any],
    *,
    runner=shared._run,
) -> dict[str, Any]:
    port, error, ports = _select_port(request)
    if error or not port:
        result = {
            "action": "upload", "success": False, "error": error,
            "upload_executed": False, "ports": ports,
        }
        if error == "starcore_identity_confirmation_required":
            result.update(
                {
                    "next_action": "confirm_starcore_identity_then_retry",
                    "teacher_message": (
                        "上传前请先确认板身印有“星核板”和“V4.2.2”。"
                        "确认后我会自动继续，不需要你填写 board_confirmed 参数。"
                    ),
                }
            )
        return result
    flashed = mpython_flash.upload_with_font(
        context,
        request,
        compiled,
        port,
        fast_speed=FAST_UPLOAD_BAUD,
        safe_speed=SAFE_UPLOAD_BAUD,
        runner=runner,
        diagnostics_for=_upload_diagnostics,
        timeout=int(request.get("upload_timeout", 300)),
    )
    success = bool(flashed.get("success"))
    return {
        "action": "upload", "success": success,
        "firmware_written": success, "hardware_runtime_verified": False,
        "board": BOARD_ID, "backend": context["backend"],
        "fqbn": str(context["fqbn"]), "port": port,
        **flashed,
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
        "board": BOARD_ID, "preferred_fqbn": V2_FQBN, "fallback_fqbn": V1_FQBN,
        "selected_backend": context.get("backend") if context else None,
        "selected_fqbn": context.get("fqbn") if context else None,
        "environment": context, "ports": ports,
        "managed_toolchain": managed.managed_context(),
        "toolchain_lock": managed.toolchain_lock(),
    }


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action == "prepare-environment":
        result = managed.prepare_environment_result(runner=shared._run)
    elif action == "doctor":
        result = doctor_result()
    elif action == "ports":
        result = {"action": "ports", "success": True, "board": BOARD_ID, "ports": scan_ports()}
    elif action in {"compile", "compile-upload"}:
        context = _current_context()
        if not context:
            result = {
                "action": action,
                "success": False,
                "error": "starcore_toolchain_missing",
                "next_action": "prepare-environment",
            }
        elif action == "compile":
            result = compile_result(context, request)
        else:
            result = compile_upload_result(context, request)
    else:
        raise ValueError("action_must_be_prepare-environment_doctor_ports_compile_or_compile-upload")
    result.setdefault("bridge", BRIDGE_NAME)
    result.setdefault("schema_version", SCHEMA_VERSION)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ChatMaker Starcore bridge")
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

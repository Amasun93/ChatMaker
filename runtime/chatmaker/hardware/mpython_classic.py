#!/usr/bin/env python3
"""Independent Windows toolchain bridge for classic mPython V2.x boards.

The compiler target is shared with Mind+'s public mPython Arduino package, but
physical-board identity is not.  A classic mPython V2.x confirmation is always
required before upload or reset.  Existing Mind+ 1.8/2 installations remain
fallbacks; the ChatMaker-managed environment is preferred.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any, Callable

from . import nano_mindplus as shared
from . import mpython_flash
from . import serial_monitor
from . import starcore_toolchain as managed_mpython


BRIDGE_NAME = "chatmaker-mpython"
SCHEMA_VERSION = 1
BOARD_ID = "mpython-classic-v2x"
MANAGED_BACKEND = "chatmaker-managed-mpython-classic"
V2_FQBN = "mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none"
V1_FQBN = "dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none"
FAST_UPLOAD_BAUD = 1500000
SAFE_UPLOAD_BAUD = 115200


def toolchain_lock() -> dict[str, Any]:
    """Return immutable artifacts plus the reviewed redistribution boundary."""
    lock = managed_mpython.toolchain_lock()
    lock["licenses"] = {
        "arduino_cli": "GPL-3.0-only (LICENSE.txt in the official release archive)",
        "mindplus_esp32_core": "LGPL-2.1 (LICENSE.md in the official core archive)",
        "mindplus_arduino_libraries": "not-declared-in-the-six-official-archives",
    }
    lock["redistribution_boundary"] = (
        "ChatMaker stores URLs, sizes and SHA-256 values and downloads the six libraries "
        "from DFRobot/Mind+ at runtime. Do not repackage those library archives until "
        "their redistribution licenses are confirmed."
    )
    return lock


def _normalize_managed_context(context: dict[str, Any] | None) -> dict[str, Any] | None:
    if context is None:
        return None
    return {
        **context,
        "backend": MANAGED_BACKEND,
        "fqbn": V2_FQBN,
        "artifact_profile": "mindplus-esp32-0.0.1",
        "shared_mpython_artifacts": True,
    }


def _current_context() -> dict[str, Any] | None:
    context = _normalize_managed_context(managed_mpython.managed_context())
    if context:
        return context
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
            root = Path(str(installation.get("root", "")))
            arduino = root / "Arduino"
            boards = arduino / "hardware" / "dfrobot" / "mpython" / "boards.txt"
            if Path(str(installation.get("builder", ""))).is_file() and boards.is_file():
                return {
                    **installation,
                    "arduino": str(arduino),
                    "boards": str(boards),
                    "fqbn": V1_FQBN,
                }
    return None


def _safe_name(value: str) -> str:
    return (re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-") or "mpython-project")[:48]


def _prepare_code(code: str, name: str) -> Path:
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code_required")
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]
    folder = Path(tempfile.gettempdir()) / "chatmaker-mpython-sketches" / f"{_safe_name(name)}-{digest}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{folder.name}.ino").write_text(code, encoding="utf-8")
    return folder


def build_compile_command(context: dict[str, Any], sketch: Path, build: Path) -> list[str]:
    if context.get("backend") in {MANAGED_BACKEND, "mindplus-2-cli"}:
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
            folder = _prepare_code(request["code"], request.get("project_name", "mpython-project"))
        elif request.get("sketch"):
            raw = Path(str(request["sketch"])).expanduser().resolve()
            folder = raw.parent if raw.is_file() else raw
            if not folder.is_dir() or not (folder / f"{folder.name}.ino").is_file():
                return {"action": "compile", "success": False, "error": "arduino_sketch_missing"}
        else:
            return {"action": "compile", "success": False, "error": "sketch_or_code_required"}
    except (OSError, ValueError) as exc:
        return {"action": "compile", "success": False, "error": str(exc)}

    build = Path(tempfile.gettempdir()) / "chatmaker-mpython-builds" / hashlib.sha256(str(folder).encode()).hexdigest()[:12]
    build.mkdir(parents=True, exist_ok=True)
    execution = shared._run(
        build_compile_command(context, folder / f"{folder.name}.ino", build),
        timeout=int(request.get("timeout", 900)),
    )
    applications = sorted(build.glob("*.bin"))
    partitions = sorted(build.glob("*.partitions.bin"))
    success = execution.get("returncode") == 0 and bool(applications) and bool(partitions)
    result = {
        "action": "compile",
        "success": success,
        "board": BOARD_ID,
        "backend": context["backend"],
        "fqbn": str(context["fqbn"]),
        "preferred_fqbn": V2_FQBN,
        "fallback_fqbn": V1_FQBN,
        "sketch": str(folder),
        "build_dir": str(build),
        "application_bin": str(applications[0]) if applications else None,
        "partitions_bin": str(partitions[0]) if partitions else None,
        "source_generated": request.get("code") is not None,
        "source_available": True,
        "execution": execution,
    }
    if not success:
        result["error"] = "compile_failed"
        result["diagnostics"] = shared._compile_diagnostics(execution)
    return result


def scan_ports() -> list[dict[str, Any]]:
    return shared.scan_ports()


def _select_port(
    request: dict[str, Any],
    *,
    identity_required: bool,
) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    ports = scan_ports()
    if identity_required and not request.get("board_confirmed"):
        return None, "mpython_classic_identity_confirmation_required", ports
    eligible = [item for item in ports if item.get("eligible_for_upload")]
    requested = str(request.get("port", "")).upper()
    if requested:
        match = next(
            (item for item in eligible if str(item.get("address", "")).upper() == requested),
            None,
        )
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
    return {
        "error_type": "upload_failed",
        "retry_at_115200": False,
        "teacher_message": "上传失败；请保留这段错误，并检查端口、数据线和复位状态。",
        "diagnostic_excerpt": raw[-12000:],
    }


def upload_result(
    context: dict[str, Any],
    request: dict[str, Any],
    compiled: dict[str, Any],
    *,
    runner=shared._run,
) -> dict[str, Any]:
    port, error, ports = _select_port(request, identity_required=True)
    if error or not port:
        result = {
            "action": "upload", "success": False, "error": error,
            "upload_executed": False, "ports": ports,
        }
        if error == "mpython_classic_identity_confirmation_required":
            result.update(
                {
                    "next_action": "confirm_mpython_classic_identity_then_retry",
                    "teacher_message": (
                        "上传前请先确认实物是经典掌控板 V2.x，而不是掌控板 3.0 或星核板。"
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
        "action": "upload",
        "success": success,
        "firmware_written": success,
        "reset_requested_by_uploader": success,
        "board_restart_observed": False,
        "hardware_runtime_verified": False,
        "physical_effect_verified": False,
        "board": BOARD_ID,
        "backend": context["backend"],
        "fqbn": str(context["fqbn"]),
        "port": port,
        **flashed,
    }


def compile_upload_result(context: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    compiled = compile_result(context, request)
    if not compiled.get("success"):
        return {"action": "compile-upload", "success": False, "stage": "compile", "compile": compiled, "upload": None}
    uploaded = upload_result(context, request, compiled)
    if uploaded.get("success"):
        stage = "complete"
    elif uploaded.get("error") in {
        "no_wired_upload_port_found",
        "mpython_classic_identity_confirmation_required",
    }:
        stage = "awaiting-hardware"
    else:
        stage = "upload"
    return {
        "action": "compile-upload",
        "success": bool(uploaded.get("success")),
        "stage": stage,
        "compile": compiled,
        "upload": uploaded,
        "hardware_connection_required": stage == "awaiting-hardware",
    }


def _pyserial_factory(**kwargs: Any):
    import serial

    return serial.Serial(**kwargs)


def reset_result(
    request: dict[str, Any],
    *,
    serial_factory: Callable[..., Any] = _pyserial_factory,
) -> dict[str, Any]:
    port, error, ports = _select_port(request, identity_required=True)
    if error or not port:
        return {"action": "reset", "success": False, "error": error, "reset_executed": False, "ports": ports}
    try:
        handle = serial_factory(port=port, baudrate=115200, timeout=0.1)
        try:
            handle.dtr = False
            handle.rts = True
            time.sleep(0.1)
            handle.rts = False
            time.sleep(0.05)
        finally:
            handle.close()
    except Exception as exc:
        return {
            "action": "reset",
            "success": False,
            "error": "board_reset_failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "reset_executed": True,
            "port": port,
        }
    return {
        "action": "reset",
        "success": True,
        "board": BOARD_ID,
        "port": port,
        "reset_executed": True,
        "board_restart_observed": False,
        "serial_evidence": False,
        "physical_effect_verified": False,
    }


def serial_read_result(
    request: dict[str, Any],
    *,
    manager: Any | None = None,
) -> dict[str, Any]:
    port, error, ports = _select_port(request, identity_required=False)
    if error or not port:
        return {"action": "serial-read", "success": False, "error": error, "ports": ports}
    selected_manager = manager or serial_monitor.SerialManager(port_provider=scan_ports)
    opened = selected_manager.open(
        port,
        baudrate=int(request.get("baudrate", 115200)),
        timeout=0.1,
    )
    if not opened.get("success"):
        return {"action": "serial-read", **opened}
    session_id = str(opened["session_id"])
    try:
        read = selected_manager.read(
            session_id,
            timeout=float(request.get("timeout", 3.0)),
            max_lines=int(request.get("max_lines", 100)),
        )
    finally:
        closed = selected_manager.close(session_id)
    return {
        "action": "serial-read",
        "board": BOARD_ID,
        **read,
        "closed": closed,
        "physical_effect_verified": False,
    }


def _prepare_environment_result() -> dict[str, Any]:
    result = managed_mpython.prepare_environment_result(runner=shared._run)
    environment = _normalize_managed_context(result.get("environment"))
    return {
        **result,
        "backend": MANAGED_BACKEND,
        "environment": environment,
        "toolchain_lock": toolchain_lock(),
        "shared_mpython_artifacts": True,
    }


def doctor_result(request: dict[str, Any] | None = None) -> dict[str, Any]:
    context = _current_context()
    selected_port, upload_error, ports = _select_port(
        request or {},
        identity_required=True,
    )
    return {
        "action": "doctor",
        "success": context is not None,
        "ready_for_compile": context is not None,
        "ready_for_upload": context is not None and selected_port is not None and upload_error is None,
        "upload_port": selected_port,
        "upload_blocked_by": upload_error,
        "identity_confirmed": bool((request or {}).get("board_confirmed")),
        "board": BOARD_ID,
        "preferred_fqbn": V2_FQBN,
        "fallback_fqbn": V1_FQBN,
        "selected_backend": context.get("backend") if context else None,
        "selected_fqbn": context.get("fqbn") if context else None,
        "environment": context,
        "ports": ports,
        "managed_toolchain": _normalize_managed_context(managed_mpython.managed_context()),
        "toolchain_lock": toolchain_lock(),
        "evidence_gates": {
            "environment": "verified" if context else "unverified",
            "source": "unverified",
            "compile": "unverified",
            "upload": "unverified",
            "serial": "unverified",
            "power_cycle": "unverified",
            "physical_effect": "unverified",
        },
    }


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action == "prepare-environment":
        result = _prepare_environment_result()
    elif action == "doctor":
        result = doctor_result(request)
    elif action == "ports":
        result = {"action": "ports", "success": True, "board": BOARD_ID, "ports": scan_ports()}
    elif action == "reset":
        result = reset_result(request)
    elif action == "serial-read":
        result = serial_read_result(request)
    elif action in {"compile", "compile-upload"}:
        context = _current_context()
        if not context:
            result = {
                "action": action,
                "success": False,
                "error": "mpython_classic_toolchain_missing",
                "next_action": "prepare-environment",
            }
        elif action == "compile":
            result = compile_result(context, request)
        else:
            result = compile_upload_result(context, request)
    else:
        raise ValueError(
            "action_must_be_prepare-environment_doctor_ports_compile_compile-upload_reset_or_serial-read"
        )
    result.setdefault("bridge", BRIDGE_NAME)
    result.setdefault("schema_version", SCHEMA_VERSION)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ChatMaker classic mPython V2.x bridge")
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

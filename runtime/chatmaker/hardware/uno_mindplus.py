#!/usr/bin/env python3
"""Mind+ Arduino Uno Rev3 environment, compile, and upload bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Optional

try:
    from . import nano_mindplus as shared
except ImportError:  # Allow direct execution from a checked-out release folder.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from chatmaker.hardware import nano_mindplus as shared


BRIDGE_NAME = "arduino-uno-mindplus"
SCHEMA_VERSION = 1
BOARD_ID = "arduino-uno-r3"
V1_FQBN = "arduino:avr:uno"
V2_FQBN = "mindplus:avr:uno"
UPLOAD_BAUD = 115200


def fqbn_for_backend(backend: str) -> str:
    if backend == "mindplus-1-builder":
        return V1_FQBN
    if backend == "mindplus-2-cli":
        return V2_FQBN
    raise ValueError(f"unsupported_backend: {backend}")


def _safe_project_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    return (cleaned or "uno-project")[:48]


def prepare_code(code: str, project_name: str = "uno-project") -> Path:
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code_required")
    safe_name = _safe_project_name(project_name)
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]
    sketch_dir = Path(tempfile.gettempdir()) / "uno-mindplus-sketches" / f"{safe_name}-{digest}"
    sketch_dir.mkdir(parents=True, exist_ok=True)
    (sketch_dir / f"{sketch_dir.name}.ino").write_text(code, encoding="utf-8")
    return sketch_dir


def _validate_sketch(path_value: str) -> tuple[Optional[Path], Optional[str]]:
    path = Path(path_value).expanduser().resolve()
    sketch_dir = path.parent if path.is_file() and path.suffix.casefold() == ".ino" else path
    if not sketch_dir.is_dir():
        return None, "sketch_path_not_found"
    expected = sketch_dir / f"{sketch_dir.name}.ino"
    if not expected.is_file():
        return None, f"arduino_sketch_missing: expected {expected.name}"
    return sketch_dir, None


def build_compile_command(
    context: dict[str, Any], sketch_file: Path, build_dir: Path
) -> list[str]:
    backend = context["backend"]
    if backend == "mindplus-2-cli":
        command = [str(context["cli"]), "compile"]
        if context.get("config"):
            command.extend(["--config-file", str(context["config"])])
        command.extend(
            [
                "--no-color",
                "--fqbn",
                V2_FQBN,
                "--build-path",
                str(build_dir),
                str(sketch_file.parent),
            ]
        )
        return command
    if backend == "mindplus-1-builder":
        arduino = Path(context["arduino"])
        return [
            str(context["builder"]),
            "-compile",
            "-logger=machine",
            "-hardware",
            str(arduino / "hardware"),
            "-tools",
            str(arduino / "arduino-builder"),
            "-tools",
            str(arduino / "hardware" / "tools" / "avr"),
            "-built-in-libraries",
            str(arduino / "libraries"),
            "-libraries",
            str(arduino / "libraries"),
            f"-fqbn={V1_FQBN}",
            "-ide-version=10819",
            "-build-path",
            str(build_dir),
            str(sketch_file),
        ]
    raise ValueError(f"unsupported_backend: {backend}")


def compile_result(context: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    try:
        if request.get("code") is not None:
            sketch_dir = prepare_code(request["code"], request.get("project_name", "uno-project"))
        elif request.get("sketch"):
            sketch_dir, error = _validate_sketch(str(request["sketch"]))
            if error or not sketch_dir:
                return {"action": "compile", "success": False, "error": error}
        else:
            return {"action": "compile", "success": False, "error": "sketch_or_code_required"}
    except (OSError, ValueError) as exc:
        return {"action": "compile", "success": False, "error": str(exc)}

    build_hash = hashlib.sha256(
        f"uno:{context['backend']}:{sketch_dir}".encode("utf-8")
    ).hexdigest()[:12]
    build_dir = Path(tempfile.gettempdir()) / "uno-mindplus-builds" / build_hash
    build_dir.mkdir(parents=True, exist_ok=True)
    sketch_file = sketch_dir / f"{sketch_dir.name}.ino"
    command = build_compile_command(context, sketch_file, build_dir)
    execution = shared._run(command, timeout=int(request.get("timeout", 600)))
    hex_files = sorted(build_dir.glob("*.hex"))
    application_hex = [path for path in hex_files if not path.name.endswith("with_bootloader.hex")]
    success = execution.get("returncode") == 0 and bool(application_hex)
    result = {
        "action": "compile",
        "success": success,
        "board": BOARD_ID,
        "backend": context["backend"],
        "fqbn": fqbn_for_backend(context["backend"]),
        "sketch": str(sketch_dir),
        "build_dir": str(build_dir),
        "hex_files": [str(path) for path in hex_files],
        "application_hex": str(application_hex[0]) if application_hex else None,
        "execution": execution,
    }
    if not success:
        result["error"] = "compile_failed"
        result["diagnostics"] = shared._compile_diagnostics(execution)
    return result


def scan_ports() -> list[dict[str, Any]]:
    ports: list[dict[str, Any]] = []
    for original in shared.scan_ports():
        item = dict(original)
        combined = " ".join(
            str(item.get(key, ""))
            for key in ("device_name", "label", "pnp_device_id")
        ).casefold()
        item.pop("nano_likely", None)
        item["uno_likely"] = any(
            marker in combined
            for marker in (
                "arduino uno",
                "vid_2341&pid_0043",
                "vid_2341&pid_0001",
                "vid_2a03&pid_0043",
                "vid_2341&pid_0243",
            )
        )
        ports.append(item)
    return ports


def select_upload_port(
    ports: list[dict[str, Any]], requested: Optional[str] = None
) -> tuple[Optional[str], Optional[str]]:
    by_address = {str(item.get("address", "")).upper(): item for item in ports}
    if requested:
        normalized = requested.strip().upper()
        item = by_address.get(normalized)
        if not item:
            return None, "upload_port_not_currently_enumerated"
        if item.get("is_bluetooth"):
            return None, "bluetooth_port_rejected"
        if not item.get("eligible_for_upload"):
            return None, "upload_port_not_eligible"
        return normalized, None
    eligible = [item for item in ports if item.get("eligible_for_upload")]
    likely = [item for item in eligible if item.get("uno_likely")]
    if len(likely) == 1:
        return str(likely[0]["address"]).upper(), None
    if len(likely) > 1:
        return None, "multiple_likely_uno_ports_require_selection"
    if len(eligible) == 1:
        return str(eligible[0]["address"]).upper(), None
    if not eligible:
        return None, "no_wired_upload_port_found"
    return None, "multiple_wired_ports_require_selection"


def _avrdude_command(
    avrdude: str, config: str, hex_file: Path, port: str
) -> list[str]:
    return [
        str(avrdude),
        "-C",
        str(config),
        "-v",
        "-p",
        "atmega328p",
        "-c",
        "arduino",
        "-P",
        str(port).upper(),
        "-b",
        str(UPLOAD_BAUD),
        "-D",
        "-U",
        f"flash:w:{hex_file}:i",
    ]


def _upload_diagnostics(execution: dict[str, Any]) -> dict[str, Any]:
    raw = "\n".join(
        value for value in (execution.get("stdout", ""), execution.get("stderr", "")) if value
    )
    lowered = raw.casefold()
    if "ser_open" in lowered or "can't open device" in lowered or "access is denied" in lowered:
        error_type = "serial_port_unavailable"
        suggestions = ["关闭串口监视器和其他占用该 COM 口的软件，再重试。"]
    elif "getsync" in lowered or "not in sync" in lowered or "programmer is not responding" in lowered:
        error_type = "bootloader_sync_failed"
        suggestions = ["确认板型为 Arduino Uno Rev3，并检查 USB 数据线、端口和复位状态。"]
    elif "device signature" in lowered:
        error_type = "unexpected_mcu_signature"
        suggestions = ["停止烧录；当前设备可能不是 ATmega328P Uno。"]
    else:
        error_type = "upload_failed"
        suggestions = ["检查 Uno 驱动、数据线、端口和板卡身份。"]
    return {
        "error_type": error_type,
        "diagnostic_excerpt": raw[-12000:],
        "suggestions": suggestions,
    }


def run_upload_attempt(
    *,
    avrdude: str,
    config: str,
    hex_file: Path,
    port: str,
    runner=shared._run,
    timeout: int = 180,
) -> dict[str, Any]:
    execution = runner(
        _avrdude_command(avrdude, config, hex_file, port), timeout=timeout
    )
    raw = "\n".join(
        value for value in (execution.get("stdout", ""), execution.get("stderr", "")) if value
    )
    success = execution.get("returncode") == 0 and (
        "verified" in raw.casefold() or "avrdude done" in raw.casefold()
    )
    result = {
        "action": "upload",
        "success": success,
        "upload_executed": True,
        "firmware_written": success,
        "hardware_runtime_verified": False,
        "board": BOARD_ID,
        "port": str(port).upper(),
        "baud": UPLOAD_BAUD,
        "bootloader_profile": "uno_optiboot_115200",
        "attempts": [execution],
        "hex_sha256": (
            hashlib.sha256(hex_file.read_bytes()).hexdigest() if hex_file.is_file() else None
        ),
    }
    if success:
        result["note"] = "固件写入并校验成功；板载灯和外设效果仍需现场观察。"
    else:
        result["diagnostics"] = _upload_diagnostics(execution)
    return result


def upload_result(
    context: dict[str, Any], request: dict[str, Any], compiled: dict[str, Any]
) -> dict[str, Any]:
    ports = scan_ports()
    selected, error = select_upload_port(ports, request.get("port"))
    if error or not selected:
        return {
            "action": "upload",
            "success": False,
            "error": error,
            "upload_executed": False,
            "ports": ports,
        }
    hex_file = Path(str(compiled.get("application_hex", "")))
    if not hex_file.is_file():
        return {
            "action": "upload",
            "success": False,
            "error": "compiled_hex_not_found",
            "upload_executed": False,
        }
    avrdude, avrdude_config = shared._find_avrdude(context)
    if not avrdude or not avrdude.is_file() or not avrdude_config or not avrdude_config.is_file():
        return {
            "action": "upload",
            "success": False,
            "error": "avrdude_toolchain_not_found",
            "upload_executed": False,
        }
    return run_upload_attempt(
        avrdude=str(avrdude),
        config=str(avrdude_config),
        hex_file=hex_file,
        port=selected,
        timeout=int(request.get("upload_timeout", 180)),
    )


def compile_upload_result(
    context: dict[str, Any],
    request: dict[str, Any],
    *,
    compile_fn=compile_result,
    upload_fn=upload_result,
) -> dict[str, Any]:
    compiled = compile_fn(context, request)
    if not compiled.get("success"):
        return {
            "action": "compile-upload",
            "success": False,
            "stage": "compile",
            "compile": compiled,
            "upload": None,
            "automatic_upload": True,
            "hardware_detected": False,
            "auto_repair_recommended": True,
            "repair_scope": "code",
            "max_agent_repair_attempts": 2,
            "teacher_message": "Uno 程序没有通过编译检查；请根据报错修改完整程序，然后自动重试。",
        }
    uploaded = upload_fn(context, request, compiled)
    hardware_missing = uploaded.get("error") == "no_wired_upload_port_found"
    if uploaded.get("success"):
        stage = "complete"
        teacher_message = "已检测到 Arduino Uno，程序已按 115200 自动上传并完成写入校验。"
    elif hardware_missing:
        stage = "awaiting-hardware"
        teacher_message = (
            "未检测到有线 Arduino Uno。请用可传数据的 USB 线接入硬件；"
            "接入后再次运行即可自动上传，不需要重新确认。"
        )
    else:
        stage = "upload"
        teacher_message = "已进入 Uno 自动上传，但遇到硬件或串口问题；请按诊断提示处理后重试。"
    return {
        "action": "compile-upload",
        "success": bool(uploaded.get("success")),
        "stage": stage,
        "automatic_upload": True,
        "hardware_detected": not hardware_missing,
        "hardware_connection_required": hardware_missing,
        "retry_when_hardware_connected": hardware_missing,
        "teacher_message": teacher_message,
        "compile": compiled,
        "upload": uploaded,
    }


def doctor_result() -> dict[str, Any]:
    installations = shared.discover_installations()
    decision = shared.choose_environment(installations)
    ports = scan_ports()
    selected_port, port_error = select_upload_port(ports)
    return {
        "action": "doctor",
        "success": not decision["install_needed"],
        "ready_for_compile": not decision["install_needed"],
        "ready_for_upload": not decision["install_needed"] and selected_port is not None,
        "hardware_pending": selected_port is None,
        "board": BOARD_ID,
        "fqbn": {
            "mindplus-1-builder": V1_FQBN,
            "mindplus-2-cli": V2_FQBN,
        },
        "system": shared.detect_system(),
        "installations": installations,
        "environment": decision,
        "ports": ports,
        "recommended_port": selected_port,
        "port_status": port_error,
        "upload_baud": UPLOAD_BAUD,
    }


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action == "doctor":
        result = doctor_result()
    elif action == "prepare-environment":
        result = shared.prepare_environment(
            execute_download=bool(request.get("download", False)),
            launch_after_download=bool(request.get("launch_installer", False)),
            download_dir=(Path(request["download_dir"]) if request.get("download_dir") else None),
        )
        result["board"] = BOARD_ID
    elif action == "ports":
        ports = scan_ports()
        selected, error = select_upload_port(ports, request.get("port"))
        result = {
            "action": "ports",
            "success": True,
            "board": BOARD_ID,
            "ports": ports,
            "recommended_port": selected,
            "port_status": error,
        }
    elif action in {"compile", "compile-upload"}:
        decision = shared.choose_environment(shared.discover_installations())
        context = shared._selected_context(decision)
        if not context:
            result = {
                "action": action,
                "success": False,
                "error": "mindplus_not_installed_or_toolchain_missing",
                "environment": decision,
            }
        elif action == "compile":
            result = compile_result(context, request)
        else:
            result = compile_upload_result(context, request)
    else:
        raise ValueError(
            "action_must_be_prepare-environment_doctor_ports_compile_or_compile-upload"
        )
    result.setdefault("bridge", BRIDGE_NAME)
    result.setdefault("schema_version", SCHEMA_VERSION)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Arduino Uno Mind+ bridge")
    parser.add_argument("--request-json", required=True, help="JSON object or '-' for stdin")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.request_json == "-" else args.request_json
        result = execute_request(json.loads(raw))
    except Exception as exc:
        result = {
            "success": False,
            "error": "unexpected_bridge_error",
            "detail": f"{type(exc).__name__}: {exc}",
            "bridge": BRIDGE_NAME,
            "schema_version": SCHEMA_VERSION,
        }
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

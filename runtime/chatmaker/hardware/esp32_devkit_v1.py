#!/usr/bin/env python3
"""Strict DOIT ESP32 DEVKIT V1 / ESP-WROOM-32 toolchain contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Optional


BOARD_ID = "esp32-devkit-v1"
TARGET_PROFILE_ID = "doit-esp32-devkit-v1-wroom32"
TARGET_FQBN = "esp32:esp32:esp32doit-devkit-v1"
TARGET_CORE_ID = "esp32:esp32"
REQUIRED_CORE_VERSION = "3.3.11"
ESP32_PACKAGE_INDEX_URL = "https://espressif.github.io/arduino-esp32/package_esp32_index.json"
PROCESS_TREE_CLEANUP_TIMEOUT = 5.0


def _wait_for_process_exit(process, wait_timeout: float) -> None:
    try:
        process.wait(timeout=wait_timeout)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=wait_timeout)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _terminate_process_tree(
    process,
    *,
    platform: str = os.name,
    taskkill_runner=None,
    wait_timeout: float = PROCESS_TREE_CLEANUP_TIMEOUT,
) -> None:
    if platform == "nt":
        runner = taskkill_runner or subprocess.run
        try:
            completed = runner(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                text=True,
                capture_output=True,
                timeout=wait_timeout,
                check=False,
            )
            if completed.returncode != 0:
                process.kill()
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass
    else:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except OSError:
            try:
                process.kill()
            except OSError:
                pass
    _wait_for_process_exit(process, wait_timeout)


def _run(command: list[str], timeout: int = 30) -> dict[str, Any]:
    popen_options: dict[str, Any] = {}
    if os.name == "nt":
        popen_options["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
        )
    else:
        popen_options["start_new_session"] = True
    try:
        process = subprocess.Popen(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            **popen_options,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            _terminate_process_tree(process)
            return {
                "command": command,
                "returncode": None,
                "stdout": "",
                "stderr": f"{type(exc).__name__}: {exc}",
                "timed_out": True,
            }
        return {
            "command": command,
            "returncode": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
        }
    except OSError as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "timed_out": False,
        }


def discover_cli_candidates() -> list[dict[str, Any]]:
    local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    locations: list[tuple[str, Path, Optional[Path]]] = []
    path_cli = shutil.which("arduino-cli")
    if path_cli:
        locations.append(("path-arduino-cli", Path(path_cli), None))
    locations.extend(
        [
            (
                "arduino-ide-cli",
                Path("E:/Arduino IDE/resources/app/node_modules/arduino-ide-extension/build/arduino-cli.exe"),
                None,
            ),
            (
                "mindplus-2-cli",
                Path("E:/Mind+2/applications/deps/mind-link/tool/arduino-cli.exe"),
                local_appdata / "mind+" / "Arduino" / "arduino-cli.yaml",
            ),
        ]
    )
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for backend, cli, config in locations:
        if not cli.is_file():
            continue
        resolved = str(cli.resolve())
        if resolved.casefold() in seen:
            continue
        seen.add(resolved.casefold())
        candidate: dict[str, Any] = {"backend": backend, "cli": resolved}
        if config and config.is_file():
            candidate["config"] = str(config.resolve())
        candidates.append(candidate)
    return candidates


def scan_ports() -> list[dict[str, Any]]:
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    ports: list[dict[str, Any]] = []
    for port in list_ports.comports():
        combined = " ".join(
            str(value or "")
            for value in (port.device, port.description, port.hwid, port.manufacturer)
        ).casefold()
        bluetooth = "bluetooth" in combined or "bth" in combined
        usb_uart = any(
            marker in combined
            for marker in ("cp210", "ch340", "ch341", "ch910", "ftdi", "usb serial")
        )
        ports.append(
            {
                "address": str(port.device).upper(),
                "label": str(port.description or port.device),
                "pnp_device_id": str(port.hwid or ""),
                "is_bluetooth": bluetooth,
                "usb_uart_likely": usb_uart,
                "eligible_for_upload": bool(port.device) and not bluetooth,
            }
        )
    return sorted(ports, key=lambda item: item["address"])


def select_exact_core(inventory: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    for item in inventory:
        if (
            isinstance(item, dict)
            and
            str(item.get("id", "")) == TARGET_CORE_ID
            and str(item.get("installed", "")) == REQUIRED_CORE_VERSION
        ):
            return item
    return None


def _with_config(command: list[str], candidate: dict[str, Any]) -> list[str]:
    if candidate.get("config"):
        command.extend(["--config-file", str(candidate["config"])])
    return command


def _execution_summary(execution: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "returncode": execution.get("returncode"),
        "stderr": str(execution.get("stderr", ""))[-4000:],
    }
    if execution.get("command"):
        summary["command"] = execution["command"]
    return summary


def _core_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item[key]
        for key in ("id", "installed", "name")
        if key in item
    }


def probe_candidate(
    candidate: dict[str, Any],
    *,
    runner,
    timeout: int = 30,
) -> dict[str, Any]:
    cli = str(candidate["cli"])
    core_command = _with_config(
        [cli, "core", "list", "--format", "jsonmini"], candidate
    )
    core_execution = runner(core_command, timeout=timeout)
    try:
        raw_inventory = json.loads(core_execution.get("stdout", ""))
    except (json.JSONDecodeError, TypeError):
        raw_inventory = None
    inventory_valid = (
        core_execution.get("returncode") == 0 and isinstance(raw_inventory, list)
    )
    inventory_items = raw_inventory if inventory_valid else []
    exact_core = select_exact_core(inventory_items)
    inventory = [
        _core_summary(item) for item in inventory_items if isinstance(item, dict)
    ]
    result = {
        **candidate,
        "core_inventory": inventory,
        "core_inventory_valid": inventory_valid,
        "core_execution": _execution_summary(core_execution),
        "required_core": f"{TARGET_CORE_ID}@{REQUIRED_CORE_VERSION}",
        "required_fqbn": TARGET_FQBN,
        "ready_for_compile": False,
        "fqbn_details_verified": False,
    }
    if not inventory_valid:
        result["error"] = "esp32_core_inventory_unavailable"
        return result
    if exact_core is None:
        result["error"] = "exact_esp32_core_not_found"
        return result
    board_command = _with_config(
        [
            cli,
            "board",
            "details",
            "-b",
            TARGET_FQBN,
            "--format",
            "jsonmini",
        ],
        candidate,
    )
    board_execution = runner(board_command, timeout=timeout)
    try:
        details = json.loads(board_execution.get("stdout", ""))
    except (json.JSONDecodeError, TypeError):
        details = {}
    verified = (
        board_execution.get("returncode") == 0
        and isinstance(details, dict)
        and details.get("fqbn") == TARGET_FQBN
        and details.get("name") == "DOIT ESP32 DEVKIT V1"
    )
    result.update(
        {
            "core": _core_summary(exact_core),
            "core_version": str(exact_core.get("installed", "")),
            "board_details": details,
            "board_details_execution": _execution_summary(board_execution),
            "fqbn_details_verified": verified,
            "ready_for_compile": verified,
        }
    )
    if not verified:
        result["error"] = "exact_esp32_fqbn_details_not_verified"
    return result


def _probe_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "backend": result.get("backend"),
        "cli": result.get("cli"),
        "config": result.get("config"),
        "core_inventory": result.get("core_inventory", []),
        "core_inventory_valid": bool(result.get("core_inventory_valid")),
        "core_version": result.get("core_version"),
        "ready_for_compile": bool(result.get("ready_for_compile")),
        "fqbn_details_verified": bool(result.get("fqbn_details_verified")),
        "error": result.get("error"),
        "core_execution": result.get("core_execution"),
        "board_details_execution": result.get("board_details_execution"),
    }


def _is_mindplus_candidate(candidate: dict[str, Any]) -> bool:
    combined = " ".join(
        str(candidate.get(key, ""))
        for key in ("backend", "cli", "config")
    ).casefold()
    return (
        "mindplus" in combined
        or "mind+" in combined
        or "mind plus" in combined
    )


def _parse_numeric_version(value: Any) -> Optional[tuple[int, ...]]:
    normalized = str(value or "").strip()
    if not re.fullmatch(r"\d+(?:\.\d+)*", normalized):
        return None
    return tuple(int(part) for part in normalized.split("."))


def _compare_core_versions(installed: Any, required: str) -> Optional[int]:
    installed_parts = _parse_numeric_version(installed)
    required_parts = _parse_numeric_version(required)
    if installed_parts is None or required_parts is None:
        return None
    length = max(len(installed_parts), len(required_parts))
    left = installed_parts + (0,) * (length - len(installed_parts))
    right = required_parts + (0,) * (length - len(required_parts))
    if left < right:
        return -1
    if left > right:
        return 1
    return 0


def _select_install_candidate(
    candidates: list[dict[str, Any]],
    probed: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    by_cli = {str(item.get("cli")): item for item in probed}
    older_cli = None
    for candidate in candidates:
        summary = by_cli.get(str(candidate.get("cli")))
        if not summary:
            continue
        for core in summary.get("core_inventory", []):
            if str(core.get("id")) != TARGET_CORE_ID:
                continue
            if _compare_core_versions(core.get("installed"), REQUIRED_CORE_VERSION) == -1:
                older_cli = str(candidate.get("cli"))
                break
        if older_cli:
            break
    if older_cli:
        return next(
            (candidate for candidate in candidates if str(candidate.get("cli")) == older_cli),
            None,
        )
    return candidates[0] if candidates else None


def _check_auto_install_blockers(probed: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    for candidate in probed:
        for core in candidate.get("core_inventory", []):
            if str(core.get("id")) != TARGET_CORE_ID:
                continue
            installed = str(core.get("installed", ""))
            comparison = _compare_core_versions(installed, REQUIRED_CORE_VERSION)
            evidence = {
                "backend": candidate.get("backend"),
                "cli": candidate.get("cli"),
                "installed_core": _core_summary(core),
            }
            if comparison is None or (
                comparison == 0 and installed != REQUIRED_CORE_VERSION
            ):
                return {
                    "error": "installed_core_version_not_auto_replaceable",
                    "environment": evidence,
                }
            if comparison == 1:
                return {
                    "error": "installed_core_newer_than_verified_target",
                    "environment": evidence,
                }
    return None


def _prepare_command(
    candidate: dict[str, Any],
    *parts: str,
) -> list[str]:
    command = [str(candidate["cli"]), *parts]
    if candidate.get("config"):
        command.extend(["--config-file", str(candidate["config"])])
    command.extend(["--additional-urls", ESP32_PACKAGE_INDEX_URL])
    return command


def prepare_environment_result(
    source_candidates: list[dict[str, Any]],
    *,
    runner,
) -> dict[str, Any]:
    official_candidates = [
        candidate for candidate in source_candidates if not _is_mindplus_candidate(candidate)
    ]
    probed = [probe_candidate(candidate, runner=runner) for candidate in official_candidates]
    official_probed = probed
    base = {
        "action": "prepare-environment",
        "board": BOARD_ID,
        "profile_id": TARGET_PROFILE_ID,
        "required_core": f"{TARGET_CORE_ID}@{REQUIRED_CORE_VERSION}",
        "required_fqbn": TARGET_FQBN,
        "update_checked": False,
        "update_performed": False,
        "installation_performed": False,
        "ready_for_compile": False,
        "probe_before": [_probe_summary(candidate) for candidate in probed],
        "probe_after": [],
    }
    ready = next(
        (candidate for candidate in official_probed if candidate.get("ready_for_compile")),
        None,
    )
    if ready is not None:
        return {
            **base,
            "success": True,
            "ready_for_compile": True,
            "fqbn_details_verified": bool(ready.get("fqbn_details_verified")),
            "environment": _probe_summary(ready),
        }
    if any(not candidate.get("core_inventory_valid") for candidate in official_probed):
        return {
            **base,
            "success": False,
            "error": "esp32_core_inventory_unavailable",
        }

    if not official_candidates:
        return {
            **base,
            "success": False,
            "error": "official_arduino_cli_not_found",
        }

    valid_probed = [
        candidate for candidate in official_probed if candidate.get("core_inventory_valid")
    ]

    blocker = _check_auto_install_blockers(valid_probed)
    if blocker is not None:
        return {
            **base,
            "success": False,
            "error": blocker["error"],
            "blocked_environment": blocker["environment"],
        }

    valid_cli = {str(candidate.get("cli")) for candidate in valid_probed}
    install_candidates = [
        candidate for candidate in official_candidates
        if str(candidate.get("cli")) in valid_cli
    ]
    install_candidate = _select_install_candidate(install_candidates, valid_probed)
    if install_candidate is None:
        return {
            **base,
            "success": False,
            "error": "official_arduino_cli_not_found",
        }

    update_execution = runner(
        _prepare_command(install_candidate, "core", "update-index"),
        timeout=120,
    )
    result = {
        **base,
        "success": False,
        "update_checked": True,
        "update_performed": update_execution.get("returncode") == 0,
        "update_execution": _execution_summary(update_execution),
        "selected_cli": {
            "backend": install_candidate.get("backend"),
            "cli": install_candidate.get("cli"),
            "config": install_candidate.get("config"),
        },
    }
    if update_execution.get("returncode") != 0:
        result["error"] = "esp32_core_index_update_failed"
        return result

    install_execution = runner(
        _prepare_command(
            install_candidate,
            "core",
            "install",
            f"{TARGET_CORE_ID}@{REQUIRED_CORE_VERSION}",
        ),
        timeout=900,
    )
    result["install_execution"] = _execution_summary(install_execution)
    result["installation_performed"] = install_execution.get("returncode") == 0
    reprobe = probe_candidate(install_candidate, runner=runner)
    result["probe_after"] = [_probe_summary(reprobe)]
    if install_execution.get("returncode") != 0:
        result["ready_for_compile"] = False
        result["fqbn_details_verified"] = False
        result["error"] = "esp32_core_install_failed"
        return result
    result["ready_for_compile"] = bool(reprobe.get("ready_for_compile"))
    result["fqbn_details_verified"] = bool(reprobe.get("fqbn_details_verified"))
    if not reprobe.get("ready_for_compile"):
        result["error"] = str(reprobe.get("error") or "exact_esp32_toolchain_not_ready_after_install")
        result["environment"] = _probe_summary(reprobe)
        return result
    result.update(
        {
            "success": True,
            "environment": _probe_summary(reprobe),
        }
    )
    return result


def confirm_board_identity(value: Optional[str]) -> dict[str, Any]:
    normalized = str(value or "").strip().casefold()
    if normalized == TARGET_PROFILE_ID:
        return {
            "status": "confirmed",
            "profile_id": TARGET_PROFILE_ID,
            "board": BOARD_ID,
            "module": "ESP-WROOM-32",
        }
    known_mismatches = {
        "firebeetleesp32",
        "firebeetleesp32e",
        "mpython",
        "esp32-devkitc",
        "esp32 dev module",
    }
    if normalized in known_mismatches or any(
        marker in normalized for marker in ("esp32-c3", "esp32-s2", "esp32-s3")
    ):
        return {"status": "mismatch", "profile_id": None, "observed": value}
    return {
        "status": "unresolved",
        "profile_id": None,
        "observed": value,
        "reason": "carrier_board_identity_not_confirmed",
    }


def select_upload_port(
    ports: list[dict[str, Any]],
    *,
    board_profile: Optional[str],
    requested: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    if confirm_board_identity(board_profile)["status"] != "confirmed":
        return None, "board_identity_confirmation_required"
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
    if len(eligible) == 1:
        return str(eligible[0]["address"]).upper(), None
    if not eligible:
        return None, "no_wired_upload_port_found"
    return None, "multiple_wired_ports_require_selection"


def _build_cache_key(core_version: str) -> str:
    return hashlib.sha256(
        b"\0".join(
            [
                TARGET_FQBN.encode("utf-8"),
                core_version.encode("utf-8"),
            ]
        )
    ).hexdigest()[:12]


def build_cache_dir_for_sketch(sketch_dir: Path, core_version: str) -> Path:
    return sketch_dir.parent / ".chatmaker-esp32-cache" / _build_cache_key(core_version)


def prepare_build_cache_dir(sketch_dir: Path, core_version: str) -> Path:
    cache_dir = build_cache_dir_for_sketch(sketch_dir, core_version)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def build_compile_command(
    context: dict[str, Any],
    sketch_dir: Path,
    build_dir: Path,
    build_cache_dir: Optional[Path] = None,
) -> list[str]:
    command = [str(context["cli"]), "compile"]
    if context.get("config"):
        command.extend(["--config-file", str(context["config"])])
    command.extend(["--no-color", "--fqbn", TARGET_FQBN])
    if build_cache_dir is not None:
        command.extend(["--build-cache-path", str(build_cache_dir)])
    command.extend(["--build-path", str(build_dir), str(sketch_dir)])
    return command


def find_application_binary(build_dir: Path) -> Optional[Path]:
    candidates = sorted(Path(build_dir).glob("*.ino.bin"))
    return candidates[0] if candidates else None


def _validate_sketch(path_value: str) -> tuple[Optional[Path], Optional[str]]:
    path = Path(path_value).expanduser().resolve()
    sketch_dir = path.parent if path.is_file() and path.suffix.casefold() == ".ino" else path
    if not sketch_dir.is_dir():
        return None, "sketch_path_not_found"
    expected = sketch_dir / f"{sketch_dir.name}.ino"
    if not expected.is_file():
        return None, f"arduino_sketch_missing: expected {expected.name}"
    return sketch_dir, None


def prepare_code(code: str, project_name: str = "esp32-project") -> Path:
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code_required")
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(project_name).strip()).strip("-")
    safe_name = (cleaned or "esp32-project")[:48]
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]
    sketch_dir = (
        Path(tempfile.gettempdir())
        / "chatmaker-esp32-sketches"
        / f"{safe_name}-{digest}"
    )
    sketch_dir.mkdir(parents=True, exist_ok=True)
    (sketch_dir / f"{sketch_dir.name}.ino").write_text(code, encoding="utf-8")
    return sketch_dir


def _build_digest(sketch_file: Path, core_version: str) -> str:
    return hashlib.sha256(
        b"\0".join(
            [
                sketch_file.read_bytes(),
                TARGET_FQBN.encode("utf-8"),
                core_version.encode("utf-8"),
            ]
        )
    ).hexdigest()[:12]


def build_dir_for_sketch(sketch_dir: Path, digest: str) -> Path:
    return sketch_dir.parent / ".chatmaker-esp32-builds" / digest


def prepare_build_dir(sketch_dir: Path, digest: str) -> Path:
    build_dir = build_dir_for_sketch(sketch_dir, digest)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    return build_dir


def compile_result(
    context: dict[str, Any],
    request: dict[str, Any],
    *,
    runner=_run,
) -> dict[str, Any]:
    if _is_mindplus_candidate(context):
        return {
            "action": "compile",
            "success": False,
            "error": "official_arduino_cli_required",
            "board": BOARD_ID,
        }
    if confirm_board_identity(request.get("board_profile"))["status"] != "confirmed":
        return {
            "action": "compile",
            "success": False,
            "error": "board_identity_confirmation_required",
            "board": BOARD_ID,
            "required_profile": TARGET_PROFILE_ID,
        }
    if not context.get("ready_for_compile") or not context.get("fqbn_details_verified"):
        return {
            "action": "compile",
            "success": False,
            "error": "exact_esp32_toolchain_missing",
            "board": BOARD_ID,
            "required_core": f"{TARGET_CORE_ID}@{REQUIRED_CORE_VERSION}",
            "required_fqbn": TARGET_FQBN,
        }
    try:
        if request.get("code") is not None:
            sketch_dir = prepare_code(
                request["code"], request.get("project_name", "esp32-project")
            )
            error = None
        else:
            sketch_dir, error = _validate_sketch(str(request.get("sketch", "")))
        if error or sketch_dir is None:
            return {"action": "compile", "success": False, "error": error}
    except (OSError, ValueError) as exc:
        return {"action": "compile", "success": False, "error": str(exc)}
    sketch_file = sketch_dir / f"{sketch_dir.name}.ino"
    digest = _build_digest(sketch_file, str(context.get("core_version", "")))
    core_version = str(context.get("core_version", ""))
    build_dir = prepare_build_dir(sketch_dir, digest)
    build_cache_dir = prepare_build_cache_dir(sketch_dir, core_version)
    command = build_compile_command(
        context,
        sketch_dir,
        build_dir,
        build_cache_dir,
    )
    execution = runner(command, timeout=int(request.get("timeout", 1200)))
    application_bin = find_application_binary(build_dir)
    success = execution.get("returncode") == 0 and application_bin is not None
    result = {
        "action": "compile",
        "success": success,
        "board": BOARD_ID,
        "profile_id": TARGET_PROFILE_ID,
        "fqbn": TARGET_FQBN,
        "core_version": str(context.get("core_version", "")),
        "sketch": str(sketch_dir),
        "build_dir": str(build_dir),
        "build_cache_dir": str(build_cache_dir),
        "application_bin": str(application_bin) if application_bin else None,
        "execution": execution,
    }
    if not success:
        result["error"] = "compile_failed"
    return result


def build_upload_command(
    context: dict[str, Any], build_dir: Path, port: str
) -> list[str]:
    command = [
        str(context["cli"]),
        "upload",
        "-p",
        str(port).upper(),
        "-b",
        TARGET_FQBN,
        "--input-dir",
        str(build_dir),
    ]
    if context.get("config"):
        command.extend(["--config-file", str(context["config"])])
    return command


def upload_result(
    context: dict[str, Any],
    request: dict[str, Any],
    compiled: dict[str, Any],
    *,
    ports: list[dict[str, Any]],
    runner=_run,
) -> dict[str, Any]:
    if _is_mindplus_candidate(context):
        return {
            "action": "upload",
            "success": False,
            "error": "official_arduino_cli_required",
            "upload_executed": False,
        }
    selected, error = select_upload_port(
        ports,
        board_profile=request.get("board_profile"),
        requested=request.get("port"),
    )
    if error or not selected:
        return {
            "action": "upload",
            "success": False,
            "error": error,
            "upload_executed": False,
            "ports": ports,
        }
    application_bin = Path(str(compiled.get("application_bin", "")))
    build_dir = Path(str(compiled.get("build_dir", "")))
    if not application_bin.is_file() or not build_dir.is_dir():
        return {
            "action": "upload",
            "success": False,
            "error": "compiled_esp32_binary_not_found",
            "upload_executed": False,
        }
    command = build_upload_command(context, build_dir, selected)
    execution = runner(command, timeout=int(request.get("upload_timeout", 300)))
    success = execution.get("returncode") == 0
    return {
        "action": "upload",
        "success": success,
        "upload_executed": True,
        "firmware_uploaded": success,
        "hardware_runtime_verified": False,
        "reboot_verified": False,
        "board": BOARD_ID,
        "profile_id": TARGET_PROFILE_ID,
        "fqbn": TARGET_FQBN,
        "port": selected,
        "application_bin": str(application_bin),
        "execution": execution,
        **({} if success else {"error": "upload_failed"}),
    }


def compile_upload_result(
    context: dict[str, Any],
    request: dict[str, Any],
    *,
    ports: list[dict[str, Any]],
    compile_fn=None,
    upload_fn=None,
    runner=_run,
) -> dict[str, Any]:
    if _is_mindplus_candidate(context):
        return {
            "action": "compile-upload",
            "success": False,
            "stage": "compile",
            "compile": {
                "action": "compile",
                "success": False,
                "error": "official_arduino_cli_required",
            },
            "upload": None,
            "automatic_upload": True,
            "hardware_connection_required": False,
        }
    compiled = (
        compile_fn(context, request)
        if compile_fn is not None
        else compile_result(context, request, runner=runner)
    )
    if not compiled.get("success"):
        return {
            "action": "compile-upload",
            "success": False,
            "stage": "compile",
            "compile": compiled,
            "upload": None,
            "automatic_upload": True,
            "hardware_connection_required": False,
        }
    uploaded = (
        upload_fn(context, request, compiled, ports)
        if upload_fn is not None
        else upload_result(context, request, compiled, ports=ports, runner=runner)
    )
    hardware_missing = uploaded.get("error") == "no_wired_upload_port_found"
    if uploaded.get("success"):
        stage = "uploaded"
        message = "固件已写入并由上传工具返回成功；启动、串口、Wi-Fi 和实体效果仍需继续验证。"
    elif hardware_missing:
        stage = "awaiting-hardware"
        message = "未检测到有线且已确认身份的 DOIT ESP32 DevKit V1；接入后再次运行即可继续。"
    else:
        stage = "upload"
        message = "ESP32 编译通过，但上传端口或开发板身份仍需处理。"
    return {
        "action": "compile-upload",
        "success": bool(uploaded.get("success")),
        "stage": stage,
        "automatic_upload": True,
        "hardware_connection_required": hardware_missing,
        "teacher_message": message,
        "compile": compiled,
        "upload": uploaded,
    }


def doctor_result(
    *,
    candidates: list[dict[str, Any]],
    ports: list[dict[str, Any]],
) -> dict[str, Any]:
    official_candidates = [
        candidate for candidate in candidates if not _is_mindplus_candidate(candidate)
    ]
    selected = None
    for candidate in official_candidates:
        core = select_exact_core(list(candidate.get("core_inventory", [])))
        fqbn_verified = candidate.get("fqbn_details_verified", True)
        candidate_ready = candidate.get("ready_for_compile", True)
        inventory_valid = candidate.get("core_inventory_valid", True)
        if core and fqbn_verified and candidate_ready and inventory_valid:
            selected = {**candidate, "core": core}
            break
    if selected is None:
        return {
            "action": "doctor",
            "success": False,
            "error": "exact_esp32_toolchain_missing",
            "ready_for_compile": False,
            "ready_for_upload": False,
            "installation_performed": False,
            "board": BOARD_ID,
            "profile_id": TARGET_PROFILE_ID,
            "required_core": f"{TARGET_CORE_ID}@{REQUIRED_CORE_VERSION}",
            "required_fqbn": TARGET_FQBN,
            "candidates": official_candidates,
            "ports": ports,
        }
    return {
        "action": "doctor",
        "success": True,
        "ready_for_compile": True,
        "ready_for_upload": False,
        "installation_performed": False,
        "board": BOARD_ID,
        "profile_id": TARGET_PROFILE_ID,
        "required_core": f"{TARGET_CORE_ID}@{REQUIRED_CORE_VERSION}",
        "required_fqbn": TARGET_FQBN,
        "environment": selected,
        "ports": ports,
    }


def execute_request(
    request: dict[str, Any],
    *,
    candidates: Optional[list[dict[str, Any]]] = None,
    ports: Optional[list[dict[str, Any]]] = None,
    runner=_run,
) -> dict[str, Any]:
    action = request.get("action")
    source_candidates = candidates if candidates is not None else discover_cli_candidates()
    official_candidates = [
        candidate for candidate in source_candidates if not _is_mindplus_candidate(candidate)
    ]
    if action == "prepare-environment":
        return prepare_environment_result(official_candidates, runner=runner)
    probed = [probe_candidate(candidate, runner=runner) for candidate in official_candidates]
    current_ports = ports if ports is not None else scan_ports()
    if action == "doctor":
        return doctor_result(candidates=probed, ports=current_ports)
    if action in {"compile", "compile-upload"}:
        selected = next(
            (candidate for candidate in probed if candidate.get("ready_for_compile")),
            None,
        )
        if selected is None:
            result = doctor_result(candidates=probed, ports=current_ports)
            result.update({"action": action, "success": False})
            return result
        if action == "compile":
            return compile_result(selected, request, runner=runner)
        return compile_upload_result(
            selected,
            request,
            ports=current_ports,
            runner=runner,
        )
    if action == "ports":
        selected, error = select_upload_port(
            current_ports,
            board_profile=request.get("board_profile"),
            requested=request.get("port"),
        )
        return {
            "action": "ports",
            "success": error is None,
            "board": BOARD_ID,
            "profile_id": TARGET_PROFILE_ID,
            "ports": current_ports,
            "recommended_port": selected,
            "port_status": error,
            "installation_performed": False,
        }
    raise ValueError("action_must_be_prepare-environment_doctor_ports_compile_or_compile-upload")


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict DOIT ESP32 DevKit V1 bridge")
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
            "board": BOARD_ID,
        }
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

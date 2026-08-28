#!/usr/bin/env python3
"""Independent Windows x64 Arduino bridge for mPython Board 3.0."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
from typing import Any, Callable
import zipfile

from chatmaker.installers import downloads
from . import nano_mindplus as shared


BOARD_ID = "mpython-v3"
BRIDGE_NAME = "chatmaker-mpython-v3"
BACKEND = "chatmaker-managed-mpython-v3"
ARDUINO_CLI_VERSION = "0.33.1"
ARDUINO_CLI = {
    "filename": "arduino-cli_0.33.1_Windows_64bit.zip",
    "url": "https://github.com/arduino/arduino-cli/releases/download/0.33.1/arduino-cli_0.33.1_Windows_64bit.zip",
    "size": 14311609,
    "sha256": "58e7474a5873dbd7cad811ed4193223497d90445a6312397a65c08156b6c96d3",
    "source_id": "arduino-github",
    "source_kind": "official_fallback",
    "sources": [
        {
            "id": "arduino-github",
            "kind": "official_fallback",
            "url": "https://github.com/arduino/arduino-cli/releases/download/0.33.1/arduino-cli_0.33.1_Windows_64bit.zip",
        }
    ],
}
PACKAGE_INDEX_URL = "https://labplus-cn.github.io/arduino-esp32/package_esp32_mpython_index_cn.json"
CORE_ID = "mpython:esp32"
CORE_VERSION = "3.0.0"
FQBN = "mpython:esp32:labplus_mpython_v3"
CORE_ARTIFACT = {
    "filename": "esp32_3.0.0.zip",
    "url": "https://github.com/labplus-cn/arduino-esp32/releases/download/v3.0.0/esp32_3.0.0.zip",
    "size": 44968645,
    "sha256": "51262c2e6b456ef80695119d8d0104a8cef42d6574abcc3d15650b8d510e611d",
}
WINDOWS_X64_DEPENDENCIES = (
    {
        "name": "esp32-arduino-libs",
        "version": "idf-release_v5.1-442a798083",
        "filename": "esp32-arduino-libs-3.0.0.zip",
        "url": "https://github.com/labplus-cn/arduino-esp32/releases/download/v3.0.0/esp32-arduino-libs-3.0.0.zip",
        "size": 79063774,
        "sha256": "009cba97f4a165e91280080fbb0b44345694473186386b64d6192c782026061f",
    },
    {
        "name": "xtensa-esp32s3-elf-gcc",
        "version": "esp-12.2.0_20230208",
        "filename": "xtensa-esp32s3-elf-12.2.0_20230208-x86_64-w64-mingw32.zip",
        "url": "https://github.com/espressif/crosstool-NG/releases/download/esp-12.2.0_20230208/xtensa-esp32s3-elf-12.2.0_20230208-x86_64-w64-mingw32.zip",
        "size": 135381926,
        "sha256": "1d15ca65e3508388a86d8bed3048c46d07538f5bc88d3e4296f9c03152087cd1",
    },
    {
        "name": "esptool_py",
        "version": "4.6",
        "filename": "esptool-v4.6-win64.zip",
        "url": "https://github.com/espressif/arduino-esp32/releases/download/2.0.9/esptool-v4.6-win64.zip",
        "size": 6638480,
        "sha256": "c7c68cd1aa520cbfce488ff6a77818ece272272eb012831b9d9ab1280a7c393f",
    },
    {
        "name": "mkspiffs",
        "version": "0.2.3",
        "filename": "mkspiffs-0.2.3-arduino-esp32-win32.zip",
        "url": "https://github.com/igrr/mkspiffs/releases/download/0.2.3/mkspiffs-0.2.3-arduino-esp32-win32.zip",
        "size": 249809,
        "sha256": "b647f2c2efe6949819c85ea9404271b55c7c9c25bcb98d3b98a1d0ba771adf56",
    },
    {
        "name": "mklittlefs",
        "version": "3.0.0-gnu12-dc7f933",
        "filename": "x86_64-w64-mingw32.mklittlefs-c41e51a.200706.zip",
        "url": "https://github.com/earlephilhower/esp-quick-toolchain/releases/download/3.0.0-gnu12/x86_64-w64-mingw32.mklittlefs-c41e51a.200706.zip",
        "size": 345132,
        "sha256": "2e319077491f8e832e96eb4f2f7a70dd919333cee4b388c394e0e848d031d542",
    },
)
WINDOWS_CPP_COMPAT = (
    'compiler.cpp.extra_flags=-MMD -c -isystem "{compiler.path}'
    '../xtensa-esp32s3-elf/include/c++/12.2.0/'
    'xtensa-esp32s3-elf/no-rtti"\n'
)


def default_root() -> Path:
    override = os.environ.get("CHATMAKER_MPYTHON_V3_HOME")
    if override:
        return Path(override).expanduser().resolve()
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return (base / "ChatMaker" / "toolchains" / "mpython-v3").resolve()


def _paths(root: Path | None = None) -> dict[str, Path]:
    selected = (root or default_root()).resolve()
    return {
        "root": selected,
        "cli": selected / "tool" / "arduino-cli.exe",
        "config": selected / "arduino-cli.yaml",
        "data": selected / "data",
        "downloads": selected / "downloads",
        "user": selected / "user",
        "manifest": selected / "manifest.json",
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_locked(item: dict[str, Any], destination: Path, *, timeout: int = 300) -> dict[str, Any]:
    return downloads.download_locked(
        downloads.legacy_artifact(item), destination, timeout=timeout
    ).to_dict()


def _install_cli(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as bundle:
        entries = [entry for entry in bundle.infolist() if Path(entry.filename).name.casefold() == "arduino-cli.exe"]
        if len(entries) != 1 or Path(entries[0].filename).parts != ("arduino-cli.exe",):
            raise ValueError("arduino_cli_archive_layout_invalid")
        executable = bundle.read(entries[0])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(executable)


def _write_config(paths: dict[str, Path]) -> None:
    for key in ("data", "downloads", "user"):
        paths[key].mkdir(parents=True, exist_ok=True)
    config = {
        "board_manager": {"additional_urls": [PACKAGE_INDEX_URL]},
        "directories": {
            "data": paths["data"].as_posix(),
            "downloads": paths["downloads"].as_posix(),
            "user": paths["user"].as_posix(),
        },
        "metrics": {"enabled": False},
        "updater": {"enable_notification": False},
    }
    paths["config"].write_text(json.dumps(config, ensure_ascii=True, indent=2) + "\n", encoding="ascii")


def _command(paths: dict[str, Path], *parts: str) -> list[str]:
    return [str(paths["cli"]), *parts, "--config-file", str(paths["config"]), "--no-color"]


def managed_context(root: Path | None = None) -> dict[str, Any] | None:
    paths = _paths(root)
    try:
        manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    except (OSError, json.JSONDecodeError):
        return None
    board_file = paths["data"] / "packages" / "mpython" / "hardware" / "esp32" / CORE_VERSION / "boards.txt"
    compatibility_file = board_file.parent / "platform.local.txt"
    if (
        manifest.get("backend") != BACKEND
        or manifest.get("core") != f"{CORE_ID}@{CORE_VERSION}"
        or manifest.get("fqbn") != FQBN
        or not paths["cli"].is_file()
        or _sha256(paths["cli"]) != manifest.get("arduino_cli_executable_sha256")
        or not paths["config"].is_file()
        or not board_file.is_file()
        or "labplus_mpython_v3.name=mPython V3" not in board_file.read_text(encoding="utf-8", errors="replace")
        or not compatibility_file.is_file()
        or compatibility_file.read_text(encoding="ascii", errors="replace") != WINDOWS_CPP_COMPAT
    ):
        return None
    return {
        "backend": BACKEND,
        "root": str(paths["root"]),
        "cli": str(paths["cli"]),
        "config": str(paths["config"]),
        "core": f"{CORE_ID}@{CORE_VERSION}",
        "fqbn": FQBN,
        "ready_for_compile": True,
    }


def toolchain_lock() -> dict[str, Any]:
    return {
        "arduino_cli": dict(ARDUINO_CLI),
        "package_index": PACKAGE_INDEX_URL,
        "core": {"id": CORE_ID, "version": CORE_VERSION, **CORE_ARTIFACT},
        "windows_x64_dependencies": [dict(item) for item in WINDOWS_X64_DEPENDENCIES],
        "fqbn": FQBN,
        "redistribution_boundary": (
            "Install from the official package index into the user's isolated "
            "ChatMaker toolchain; do not bundle these third-party archives into "
            "the ChatMaker source distribution."
        ),
    }


def prepare_environment_result(
    *, root: Path | None = None, runner: Callable[..., dict[str, Any]] = shared._run,
    downloader: Callable[..., None] = _download_locked,
) -> dict[str, Any]:
    paths = _paths(root)
    base = {"action": "prepare-environment", "board": BOARD_ID, "backend": BACKEND, "toolchain_lock": toolchain_lock(), "managed_root": str(paths["root"]), "ready_for_compile": False}
    ready = managed_context(paths["root"])
    if ready:
        return {**base, "success": True, "ready_for_compile": True, "installation_performed": False, "environment": ready}
    if os.name != "nt" or platform.machine().casefold() not in {"amd64", "x86_64", "x64"}:
        return {**base, "success": False, "error": "managed_mpython_v3_platform_not_supported"}
    try:
        archive = paths["downloads"] / ARDUINO_CLI["filename"]
        downloader(ARDUINO_CLI, archive)
        _install_cli(archive, paths["cli"])
        _write_config(paths)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return {**base, "success": False, "error": str(exc), "stage": "arduino-cli"}
    executions = []
    for stage, command, timeout in (
        ("index", _command(paths, "core", "update-index"), 180),
        ("core", _command(paths, "core", "install", f"{CORE_ID}@{CORE_VERSION}", "--skip-post-install"), 1200),
    ):
        execution = runner(command, timeout=timeout)
        executions.append({"stage": stage, **execution})
        if execution.get("returncode") != 0:
            return {**base, "success": False, "error": f"managed_mpython_v3_{stage}_failed", "stage": stage, "executions": executions}
    platform_root = paths["data"] / "packages" / "mpython" / "hardware" / "esp32" / CORE_VERSION
    compatibility_file = platform_root / "platform.local.txt"
    try:
        compatibility_file.write_text(WINDOWS_CPP_COMPAT, encoding="ascii")
    except OSError as exc:
        return {
            **base,
            "success": False,
            "error": str(exc),
            "stage": "windows-cpp-compatibility",
            "executions": executions,
        }
    manifest = {
        "schema_version": 1,
        "backend": BACKEND,
        "arduino_cli_version": ARDUINO_CLI_VERSION,
        "arduino_cli_executable_sha256": _sha256(paths["cli"]),
        "core": f"{CORE_ID}@{CORE_VERSION}",
        "fqbn": FQBN,
    }
    paths["manifest"].write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="ascii")
    ready = managed_context(paths["root"])
    if not ready:
        return {**base, "success": False, "error": "managed_mpython_v3_verification_failed", "stage": "verify", "executions": executions}
    return {**base, "success": True, "ready_for_compile": True, "installation_performed": True, "environment": ready, "executions": executions}


def _safe_name(value: str) -> str:
    return (re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-") or "mpython-v3-project")[:48]


def compile_result(context: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    code = request.get("code")
    if not isinstance(code, str) or not code.strip():
        return {"action": "compile", "success": False, "error": "code_required", "board": BOARD_ID}
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]
    sketch = Path(tempfile.gettempdir()) / "chatmaker-mpython-v3-sketches" / f"{_safe_name(request.get('project_name', 'mpython-v3-project'))}-{digest}"
    sketch.mkdir(parents=True, exist_ok=True)
    (sketch / f"{sketch.name}.ino").write_text(code, encoding="utf-8")
    build = Path(tempfile.gettempdir()) / "chatmaker-mpython-v3-builds" / digest
    build.mkdir(parents=True, exist_ok=True)
    execution = shared._run([str(context["cli"]), "compile", "--config-file", str(context["config"]), "--no-color", "--fqbn", FQBN, "--build-path", str(build), str(sketch)], timeout=int(request.get("timeout", 1200)))
    binaries = sorted(build.glob("*.ino.bin"))
    success = execution.get("returncode") == 0 and bool(binaries)
    return {"action": "compile", "success": success, "board": BOARD_ID, "backend": BACKEND, "fqbn": FQBN, "sketch": str(sketch), "build_dir": str(build), "application_bin": str(binaries[0]) if binaries else None, "execution": execution, **({} if success else {"error": "compile_failed"})}


def _select_port(request: dict[str, Any]) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    ports = shared.scan_ports()
    if request.get("board_confirmed") is not True:
        return None, "mpython_v3_identity_confirmation_required", ports
    eligible = [row for row in ports if row.get("eligible_for_upload")]
    requested = str(request.get("port", "")).upper()
    if requested:
        match = next((row for row in eligible if str(row.get("address", "")).upper() == requested), None)
        return (requested, None, ports) if match else (None, "upload_port_not_eligible", ports)
    if len(eligible) == 1:
        return str(eligible[0]["address"]).upper(), None, ports
    return (None, "no_wired_upload_port_found" if not eligible else "multiple_wired_ports_require_selection", ports)


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action == "prepare-environment":
        result = prepare_environment_result()
    else:
        context = managed_context()
        if action == "doctor":
            result = {"action": action, "success": context is not None, "board": BOARD_ID, "ready_for_compile": context is not None, "ready_for_upload": False, "environment": context, "ports": shared.scan_ports()}
        elif action == "ports":
            port, error, ports = _select_port(request)
            result = {"action": action, "success": error is None, "board": BOARD_ID, "ports": ports, "recommended_port": port, "port_status": error}
        elif action in {"compile", "compile-upload"}:
            if context is None:
                result = {"action": action, "success": False, "error": "mpython_v3_toolchain_missing", "next_action": "prepare-environment", "board": BOARD_ID}
            else:
                compiled = compile_result(context, request)
                if action == "compile" or not compiled.get("success"):
                    result = compiled
                else:
                    port, error, ports = _select_port(request)
                    if error or not port:
                        result = {"action": action, "success": False, "stage": "awaiting-hardware", "compile": compiled, "upload": {"success": False, "error": error, "upload_executed": False, "ports": ports}}
                    else:
                        command = [str(context["cli"]), "upload", "--config-file", str(context["config"]), "--no-color", "--fqbn", FQBN, "--port", port, "--input-dir", str(compiled["build_dir"])]
                        execution = shared._run(command, timeout=int(request.get("upload_timeout", 300)))
                        uploaded = execution.get("returncode") == 0
                        result = {"action": action, "success": uploaded, "stage": "uploaded" if uploaded else "upload", "compile": compiled, "upload": {"success": uploaded, "upload_executed": True, "firmware_uploaded": uploaded, "port": port, "execution": execution}}
        else:
            raise ValueError("action_must_be_prepare-environment_doctor_ports_compile_or_compile-upload")
    result.setdefault("bridge", BRIDGE_NAME)
    result.setdefault("schema_version", 1)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="mPython Board 3.0 bridge")
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.request_json == "-" else args.request_json
        result = execute_request(json.loads(raw))
    except Exception as exc:
        result = {"success": False, "error": "unexpected_bridge_error", "detail": f"{type(exc).__name__}: {exc}", "board": BOARD_ID}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

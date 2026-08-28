#!/usr/bin/env python3
"""BBC micro:bit V2 MicroPython HEX packaging and safe DAPLink copy chain."""

from __future__ import annotations

import argparse
import ast
import ctypes
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Iterable

from chatmaker.installers import downloads


BOARD_ID = "microbit-v2"
MICROPYTHON_VERSION = "2.1.1"
MICROPYTHON_URL = (
    "https://github.com/microbit-foundation/micropython-microbit-v2/"
    "releases/download/v2.1.1/micropython-microbit-v2.1.1.hex"
)
MICROPYTHON_SIZE = 1_239_726
MICROPYTHON_SHA256 = "5bd5d4584a5caae740a66d38f93651968569dd4b52f4bc132ebf3c6fdf3847ac"
MICROPYTHON_ARTIFACT = {
    "filename": "micropython-microbit-v2.1.1.hex",
    "url": MICROPYTHON_URL,
    "size": MICROPYTHON_SIZE,
    "sha256": MICROPYTHON_SHA256,
    "source_id": "microbit-github",
    "source_kind": "official_fallback",
    "sources": [
        {
            "id": "microbit-github",
            "kind": "official_fallback",
            "url": MICROPYTHON_URL,
        }
    ],
}
MICROBIT_FS_VERSION = "0.10.0"
MICROBIT_FS_INTEGRITY = "sha512-n6DEVqqaQAL/EDLyXh+1nsdRV16ePFqROeFeNlOoTS23eB8zF8qhA+IaNHRT07sy0zgCGg3YCZgP+zcCIRzP6A=="
_RUNTIME_ROOT = Path(os.environ.get("CHATMAKER_RUNTIME_ROOT", Path.home() / ".chatmaker"))
DEFAULT_TOOL_ROOT = _RUNTIME_ROOT / "toolchains" / "microbit-v2" / MICROPYTHON_VERSION
_TOOL_SOURCE = Path(__file__).with_name("microbit_tool")
_INTERFACE_VERSION = re.compile(r"(?:Interface Version|Version|Build ID)[^0-9]*v?(0[0-9]{3})", re.IGNORECASE)


@dataclass(frozen=True)
class MicrobitVolume:
    mount: Path
    label: str
    details: str
    interface_version: int | None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: list[str], *, timeout: int = 300, cwd: Path | None = None
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            cwd=str(cwd) if cwd is not None else None,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def _download(url: str, destination: Path, *, downloader: Callable | None = None) -> dict[str, Any] | None:
    if downloader is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        downloader(url, temporary)
        os.replace(temporary, destination)
        return None
    return downloads.download_locked(
        downloads.legacy_artifact(MICROPYTHON_ARTIFACT), destination, timeout=60
    ).to_dict()


def _runtime_hex(tool_root: Path) -> Path:
    return tool_root / f"micropython-microbit-v{MICROPYTHON_VERSION}.hex"


def _environment_status(tool_root: Path, *, node: str | None = None, npm: str | None = None) -> dict[str, Any]:
    runtime = _runtime_hex(tool_root)
    package = tool_root / "node_modules" / "@microbit" / "microbit-fs" / "package.json"
    portable_node = _RUNTIME_ROOT / "node" / "node.exe"
    portable_npm = _RUNTIME_ROOT / "node" / "npm.cmd"
    actual_node = node or shutil.which("node") or (str(portable_node) if portable_node.is_file() else None)
    actual_npm = npm or shutil.which("npm") or (str(portable_npm) if portable_npm.is_file() else None)
    runtime_ok = (
        runtime.is_file()
        and runtime.stat().st_size == MICROPYTHON_SIZE
        and _sha256(runtime) == MICROPYTHON_SHA256
    )
    package_ok = False
    if package.is_file():
        try:
            package_ok = json.loads(package.read_text(encoding="utf-8")).get("version") == MICROBIT_FS_VERSION
        except (OSError, UnicodeError, json.JSONDecodeError):
            package_ok = False
    return {
        "tool_root": str(tool_root),
        "node": actual_node,
        "npm": actual_npm,
        "runtime_hex": str(runtime),
        "runtime_verified": runtime_ok,
        "microbit_fs_verified": package_ok,
        "ready_for_packaging": bool(actual_node and actual_npm and runtime_ok and package_ok),
    }


def prepare_environment_result(
    *,
    tool_root: Path = DEFAULT_TOOL_ROOT,
    runner: Callable = _run,
    downloader: Callable | None = None,
) -> dict[str, Any]:
    tool_root = Path(tool_root).resolve()
    before = _environment_status(tool_root)
    if not before["node"] or not before["npm"]:
        return {"success": False, "action": "prepare-environment", "error": "node_or_npm_missing", **before}
    tool_root.mkdir(parents=True, exist_ok=True)
    bundled_changed = False
    for name in ("package.json", "package-lock.json", "package_hex.cjs"):
        source = _TOOL_SOURCE / name
        if not source.is_file():
            return {"success": False, "action": "prepare-environment", "error": "bundled_tool_file_missing", "file": name}
        destination = tool_root / name
        if not destination.is_file() or destination.read_bytes() != source.read_bytes():
            shutil.copy2(source, destination)
            bundled_changed = True
    refreshed = _environment_status(
        tool_root, node=str(before["node"]), npm=str(before["npm"])
    )
    if refreshed["ready_for_packaging"] and not bundled_changed:
        return {"success": True, "action": "prepare-environment", "changed": False, **refreshed}
    runtime = _runtime_hex(tool_root)
    download_receipt = None
    if not runtime.is_file() or runtime.stat().st_size != MICROPYTHON_SIZE or _sha256(runtime) != MICROPYTHON_SHA256:
        try:
            download_receipt = _download(MICROPYTHON_URL, runtime, downloader=downloader)
        except (OSError, TimeoutError, downloads.DownloadError) as exc:
            return {"success": False, "action": "prepare-environment", "error": "micropython_download_failed", "detail": str(exc)}
    if runtime.stat().st_size != MICROPYTHON_SIZE or _sha256(runtime) != MICROPYTHON_SHA256:
        runtime.unlink(missing_ok=True)
        return {"success": False, "action": "prepare-environment", "error": "micropython_identity_mismatch"}
    execution = None
    npm_source = None
    for registry in downloads.package_sources("npm_registries"):
        execution = runner(
            [str(before["npm"]), "ci", "--ignore-scripts", "--no-audit", "--no-fund", f"--registry={registry['url']}"],
            timeout=300,
            cwd=tool_root,
        )
        if execution.get("returncode") == 0:
            npm_source = registry
            break
    if execution is None or execution.get("returncode") != 0:
        return {"success": False, "action": "prepare-environment", "error": "microbit_fs_install_failed", "execution": execution}
    after = _environment_status(tool_root, node=str(before["node"]), npm=str(before["npm"]))
    return {
        "success": bool(after["ready_for_packaging"]),
        "action": "prepare-environment",
        "changed": True,
        "execution": execution,
        "npm_source": npm_source,
        "download": download_receipt,
        **after,
        **({} if after["ready_for_packaging"] else {"error": "environment_not_ready_after_install"}),
    }


def source_check(code: str) -> dict[str, Any]:
    if not isinstance(code, str) or not code.strip():
        return {"success": False, "source_checked": False, "error": "source_required"}
    try:
        ast.parse(code, filename="main.py")
    except SyntaxError as exc:
        return {
            "success": False,
            "source_checked": False,
            "error": "python_syntax_invalid",
            "line": exc.lineno,
            "offset": exc.offset,
            "detail": exc.msg,
        }
    return {
        "success": True,
        "source_checked": True,
        "source_sha256": hashlib.sha256(code.encode("utf-8")).hexdigest(),
        "source_bytes": len(code.encode("utf-8")),
    }


def package_hex_result(
    code: str,
    *,
    output: Path | None = None,
    tool_root: Path = DEFAULT_TOOL_ROOT,
    runner: Callable = _run,
) -> dict[str, Any]:
    checked = source_check(code)
    if not checked["success"]:
        return {"action": "package-hex", **checked, "success": False}
    status = _environment_status(Path(tool_root).resolve())
    if not status["ready_for_packaging"]:
        return {"action": "package-hex", **status, **checked, "success": False, "error": "microbit_environment_not_ready"}
    if output is None:
        digest = checked["source_sha256"][:12]
        output = Path(tempfile.gettempdir()) / "chatmaker-microbit-v2" / digest / "MICROBIT.hex"
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    source_path = output.with_name("main.py")
    source_path.write_text(code, encoding="utf-8", newline="\n")
    execution = runner(
        [
            str(status["node"]),
            str(Path(tool_root).resolve() / "package_hex.cjs"),
            str(_runtime_hex(Path(tool_root).resolve())),
            str(source_path),
            str(output),
        ],
        timeout=120,
    )
    packaged = execution.get("returncode") == 0 and output.is_file()
    return {
        "action": "package-hex",
        **checked,
        "success": packaged,
        "hex_packaged": packaged,
        "code_compiled": False,
        "hex": str(output) if packaged else None,
        "hex_size": output.stat().st_size if packaged else None,
        "hex_sha256": _sha256(output) if packaged else None,
        "execution": execution,
        **({} if packaged else {"error": "hex_packaging_failed"}),
    }


def _parse_interface_version(details: str) -> int | None:
    match = _INTERFACE_VERSION.search(details)
    return int(match.group(1)) if match else None


def inspect_volume(mount: Path, *, label: str) -> MicrobitVolume | None:
    mount = Path(mount)
    if label.upper() != "MICROBIT" or not mount.is_dir():
        return None
    details_path = mount / "DETAILS.TXT"
    if not details_path.is_file():
        return None
    try:
        details = details_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    version = _parse_interface_version(details)
    if version is None or version < 255:
        return None
    return MicrobitVolume(mount=mount.resolve(), label="MICROBIT", details=details, interface_version=version)


def _windows_volume_label(root: Path) -> str:
    if os.name != "nt":
        return ""
    volume_name = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        str(root), volume_name, len(volume_name), None, None, None, None, 0
    )
    return volume_name.value if ok else ""


def discover_microbit_volumes() -> list[MicrobitVolume]:
    if os.name != "nt":
        return []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    discovered: list[MicrobitVolume] = []
    for index in range(26):
        if not bitmask & (1 << index):
            continue
        root = Path(f"{chr(65 + index)}:\\")
        volume = inspect_volume(root, label=_windows_volume_label(root))
        if volume is not None:
            discovered.append(volume)
    return discovered


def select_volume(volumes: Iterable[MicrobitVolume], requested: str | None = None) -> tuple[MicrobitVolume | None, str | None]:
    items = list(volumes)
    if requested:
        target = os.path.normcase(str(Path(requested).resolve()))
        matches = [item for item in items if os.path.normcase(str(item.mount)) == target]
        if len(matches) == 1:
            return matches[0], None
        return None, "requested_microbit_not_found"
    if len(items) == 1:
        return items[0], None
    if not items:
        return None, "no_microbit_v2_volume_found"
    return None, "multiple_microbits_require_selection"


def flash_hex_to_volume(hex_path: Path, volume: MicrobitVolume) -> dict[str, Any]:
    hex_path = Path(hex_path).resolve()
    if not hex_path.is_file() or hex_path.suffix.casefold() != ".hex":
        return {"success": False, "error": "hex_file_invalid", "write_completed": False}
    destination = volume.mount / "CHATMAKER.HEX"
    try:
        with hex_path.open("rb") as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target, length=64 * 1024)
            target.flush()
    except OSError as exc:
        return {"success": False, "error": "microbit_write_failed", "write_completed": False, "detail": str(exc)}
    fail_path = volume.mount / "FAIL.TXT"
    fail_txt_checked = volume.mount.is_dir()
    fail_text = ""
    if fail_path.is_file():
        try:
            fail_text = fail_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            fail_text = "FAIL.TXT unreadable"
    return {
        "success": not bool(fail_text),
        "write_completed": True,
        "daplink_failure_reported": bool(fail_text),
        "daplink_failure_checked": fail_txt_checked,
        "fail_text": fail_text or None,
        "mount": str(volume.mount),
        "destination": str(destination),
        "reenumeration_verified": False,
        "serial_verified": False,
        "physical_effect_verified": False,
        **({} if not fail_text else {"error": "daplink_reported_failure"}),
    }


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    tool_root = Path(request.get("tool_root", DEFAULT_TOOL_ROOT))
    if action == "prepare-environment":
        return prepare_environment_result(tool_root=tool_root)
    if action == "doctor":
        status = _environment_status(tool_root.resolve())
        volumes = discover_microbit_volumes()
        return {"success": status["ready_for_packaging"], "action": "doctor", "board": BOARD_ID, **status, "volumes": [str(item.mount) for item in volumes], "hardware_connected": bool(volumes)}
    if action == "package-hex":
        code = request.get("code")
        if code is None and request.get("source"):
            code = Path(str(request["source"])).read_text(encoding="utf-8")
        return package_hex_result(str(code or ""), output=Path(request["output"]) if request.get("output") else None, tool_root=tool_root)
    if action == "volumes":
        volumes = discover_microbit_volumes()
        selected, error = select_volume(volumes, request.get("mount"))
        return {"success": error is None, "action": "volumes", "board": BOARD_ID, "volumes": [{"mount": str(item.mount), "interface_version": item.interface_version} for item in volumes], "recommended_mount": str(selected.mount) if selected else None, "volume_status": error}
    if action == "flash":
        volumes = discover_microbit_volumes()
        selected, error = select_volume(volumes, request.get("mount"))
        if error or selected is None:
            return {"success": False, "action": "flash", "error": error, "write_completed": False}
        result = flash_hex_to_volume(Path(str(request.get("hex", ""))), selected)
        return {"action": "flash", "board": BOARD_ID, **result}
    raise ValueError("action_must_be_prepare-environment_doctor_package-hex_volumes_or_flash")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.request_json == "-" else args.request_json
        result = execute_request(json.loads(raw))
    except Exception as exc:
        result = {"success": False, "error": "unexpected_microbit_error", "detail": f"{type(exc).__name__}: {exc}", "board": BOARD_ID}
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

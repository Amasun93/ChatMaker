#!/usr/bin/env python3
"""Mind+ Arduino Nano environment, compile, and upload bridge.

The bridge uses only Python's standard library and prints one JSON document for
each request. Existing Mind+ 1.x or 2.x installations are reused. Installation
is recommended only when neither usable environment is present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import locale
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen


BRIDGE_NAME = "arduino-nano-mindplus"
SCHEMA_VERSION = 1
V1_FQBN = "arduino:avr:nano:cpu=atmega328"
V2_FQBN = "mindplus:avr:nano:cpu=atmega328"
OFFICIAL_DOWNLOAD_PAGE = "https://mindplus.cc/download.html"
WINDOWS_V1_URL = "https://download3.dfrobot.com.cn/MindPlus_Win_V1.8.1_RC3.0.exe"


def _decode(data: bytes) -> str:
    encodings = ["utf-8", locale.getpreferredencoding(False), "gb18030", "mbcs"]
    for encoding in dict.fromkeys(encodings):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _run(command: list[str], timeout: int = 600) -> dict[str, Any]:
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
        return {
            "command": command,
            "returncode": process.returncode,
            "stdout": _decode(process.stdout).strip(),
            "stderr": _decode(process.stderr).strip(),
            "duration_seconds": round(time.monotonic() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": _decode(exc.stdout or b"").strip(),
            "stderr": _decode(exc.stderr or b"").strip(),
            "duration_seconds": round(time.monotonic() - started, 3),
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "duration_seconds": round(time.monotonic() - started, 3),
            "launch_error": True,
        }


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def merge_discovery_roots(
    defaults: Iterable[Path], discovered: Iterable[Path]
) -> list[Path]:
    return _unique_paths([Path(path) for path in [*discovered, *defaults]])


def _windows_registered_mindplus_roots() -> list[Path]:
    if os.name != "nt":
        return []
    roots: list[Path] = []
    try:
        import winreg

        locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, key_path in locations:
            try:
                key = winreg.OpenKey(hive, key_path)
            except OSError:
                continue
            with key:
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)
                    except OSError:
                        break
                    index += 1
                    try:
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            display, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if not str(display).lower().startswith("mind+"):
                                continue
                            try:
                                location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                if location:
                                    roots.append(Path(str(location)))
                                    continue
                            except OSError:
                                pass
                            uninstall, _ = winreg.QueryValueEx(subkey, "UninstallString")
                            match = re.search(r'"([^"]+)[\\/]Uninstall Mind\+\.exe"', str(uninstall), re.I)
                            if match:
                                roots.append(Path(match.group(1)))
                    except OSError:
                        continue
    except OSError:
        return []
    return _unique_paths(roots)


def _bounded_windows_mindplus_roots() -> list[Path]:
    """Inspect a small set of common install parents without scanning a drive."""
    if os.name != "nt":
        return []
    home = Path(os.environ.get("USERPROFILE", Path.home()))
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    parents = [
        local / "Programs",
        home / "Applications",
        home / "Programs",
    ]
    for drive in "CDE":
        root = Path(f"{drive}:\\")
        parents.extend(
            root / name
            for name in (
                "Apps",
                "Applications",
                "Programs",
                "Software",
                "Tools",
                "开发工具",
                "软件",
            )
        )
    names = {"mind+", "mindplus", "mind+2", "mindplus2", "mind-plus", "mind-plus2"}
    roots: list[Path] = []
    for parent in parents:
        try:
            if not parent.is_dir():
                continue
            for child in parent.iterdir():
                if child.is_dir() and child.name.casefold().replace(" ", "") in names:
                    roots.append(child)
        except OSError:
            continue
    return _unique_paths(roots)


def default_v1_roots() -> list[Path]:
    roots = [
        Path(r"C:\Program Files (x86)\Mind+"),
        Path(r"C:\Program Files\Mind+"),
    ]
    explicit = os.environ.get("MINDPLUS1_ROOT")
    if explicit:
        roots.insert(0, Path(explicit).expanduser())
    for drive in "CDE":
        roots.extend([Path(f"{drive}:\\Mind+"), Path(f"{drive}:\\MindPlus")])
    discovered = [*_windows_registered_mindplus_roots(), *_bounded_windows_mindplus_roots()]
    return merge_discovery_roots(roots, discovered)


def default_v2_roots() -> list[Path]:
    roots = [
        Path(r"C:\Program Files (x86)\Mind+2"),
        Path(r"C:\Program Files\Mind+2"),
    ]
    explicit = os.environ.get("MINDPLUS2_ROOT")
    if explicit:
        roots.insert(0, Path(explicit).expanduser())
    for drive in "CDE":
        roots.extend([Path(f"{drive}:\\Mind+2"), Path(f"{drive}:\\MindPlus2")])
    discovered = [*_windows_registered_mindplus_roots(), *_bounded_windows_mindplus_roots()]
    return merge_discovery_roots(roots, discovered)


def default_v2_configs() -> list[Path]:
    local = os.environ.get("LOCALAPPDATA")
    candidates = []
    if local:
        candidates.append(Path(local) / "mind+" / "Arduino" / "arduino-cli.yaml")
    candidates.append(Path.home() / "AppData" / "Local" / "mind+" / "Arduino" / "arduino-cli.yaml")
    for root in default_v2_roots():
        candidates.extend(
            (
                root / "Arduino" / "arduino-cli.yaml",
                root / "resources" / "app" / "Arduino" / "arduino-cli.yaml",
                root / "applications" / "deps" / "mind-link" / "tool" / "arduino-cli.yaml",
            )
        )
    return _unique_paths(candidates)


def discover_installations(
    *,
    v1_roots: Optional[Iterable[Path]] = None,
    v2_roots: Optional[Iterable[Path]] = None,
    v2_config_candidates: Optional[Iterable[Path]] = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for root in v1_roots if v1_roots is not None else default_v1_roots():
        root = Path(root)
        arduino = root / "Arduino"
        builder = arduino / "arduino-builder" / "arduino-builder.exe"
        avrdude = arduino / "hardware" / "tools" / "avr" / "bin" / "avrdude.exe"
        boards = arduino / "hardware" / "arduino" / "avr" / "boards.txt"
        if builder.is_file() and avrdude.is_file() and boards.is_file():
            results.append(
                {
                    "backend": "mindplus-1-builder",
                    "root": str(root.resolve()),
                    "builder": str(builder.resolve()),
                    "avrdude": str(avrdude.resolve()),
                    "boards": str(boards.resolve()),
                    "version_family": "1.x",
                    "toolchain_present": True,
                }
            )

    configs = [Path(path) for path in (
        v2_config_candidates if v2_config_candidates is not None else default_v2_configs()
    ) if Path(path).is_file()]
    config = configs[0].resolve() if configs else None
    for root in v2_roots if v2_roots is not None else default_v2_roots():
        root = Path(root)
        cli = root / "applications" / "deps" / "mind-link" / "tool" / "arduino-cli.exe"
        if cli.is_file() and config:
            results.append(
                {
                    "backend": "mindplus-2-cli",
                    "root": str(root.resolve()),
                    "cli": str(cli.resolve()),
                    "config": str(config),
                    "version_family": "2.x",
                    "toolchain_present": True,
                }
            )
    return results


def discover_installation_report(
    *,
    v1_roots: Optional[Iterable[Path]] = None,
    v2_roots: Optional[Iterable[Path]] = None,
    v2_config_candidates: Optional[Iterable[Path]] = None,
) -> dict[str, Any]:
    """Return beginner-readable installed, incomplete, and usable states."""
    first_roots = [Path(path) for path in (v1_roots if v1_roots is not None else default_v1_roots())]
    second_roots = [Path(path) for path in (v2_roots if v2_roots is not None else default_v2_roots())]
    config_paths = [Path(path) for path in (
        v2_config_candidates if v2_config_candidates is not None else default_v2_configs()
    )]
    usable = discover_installations(
        v1_roots=first_roots,
        v2_roots=second_roots,
        v2_config_candidates=config_paths,
    )
    usable_roots = {str(Path(item["root"])).casefold() for item in usable}
    partial: list[dict[str, Any]] = []

    for version, roots in (("1.x", first_roots), ("2.x", second_roots)):
        for root in _unique_paths(roots):
            try:
                if not root.is_dir() or str(root.resolve()).casefold() in usable_roots:
                    continue
            except OSError:
                continue
            if version == "1.x":
                required = {
                    "builder": root / "Arduino" / "arduino-builder" / "arduino-builder.exe",
                    "uploader": root / "Arduino" / "hardware" / "tools" / "avr" / "bin" / "avrdude.exe",
                    "board_definition": root / "Arduino" / "hardware" / "arduino" / "avr" / "boards.txt",
                }
            else:
                required = {
                    "cli": root / "applications" / "deps" / "mind-link" / "tool" / "arduino-cli.exe",
                }
            missing = [name for name, path in required.items() if not path.is_file()]
            if version == "2.x" and not any(path.is_file() for path in config_paths):
                missing.append("arduino_cli_config")
            partial.append(
                {
                    "root": str(root.resolve()),
                    "version_family": version,
                    "toolchain_present": False,
                    "missing": missing,
                }
            )

    if len(usable) > 1:
        status = "multiple-usable"
    elif usable:
        status = "usable"
    elif partial:
        status = "installed-toolchain-incomplete"
    else:
        status = "not-installed"
    return {
        "status": status,
        "available": bool(usable),
        "installations": usable,
        "partial_installations": partial,
    }


def choose_environment(installations: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [item for item in installations if item.get("toolchain_present")]
    if not usable:
        system = detect_system()
        return {
            "selected_backend": None,
            "selected": None,
            "install_needed": True,
            "install_recommendation": recommend_mindplus_1x(system),
        }
    # Keep existing environments. Prefer 2.x when both are present because its
    # CLI exposes discovery and upload as stable structured commands.
    selected = next(
        (item for item in usable if item["backend"] == "mindplus-2-cli"), usable[0]
    )
    return {
        "selected_backend": selected["backend"],
        "selected": selected,
        "install_needed": False,
        "install_recommendation": None,
        "available_backends": [item["backend"] for item in usable],
    }


def _normalize_architecture(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"amd64", "x86_64", "x64"}:
        return "x86_64"
    if lowered in {"arm64", "aarch64"}:
        return "arm64"
    if "loong" in lowered:
        return "loongarch64"
    if "mips" in lowered:
        return "mips64"
    return lowered or "unknown"


def detect_system() -> dict[str, str]:
    system_name = platform.system().lower()
    architecture = _normalize_architecture(platform.machine())
    distribution = system_name
    version = platform.release()
    if system_name == "linux":
        try:
            os_release = Path("/etc/os-release").read_text(encoding="utf-8")
        except OSError:
            os_release = ""
        match = re.search(r"(?m)^ID=[\"']?([^\"'\n]+)", os_release)
        distribution = match.group(1).lower() if match else "linux"
        pretty = re.search(r"(?m)^VERSION_ID=[\"']?([^\"'\n]+)", os_release)
        version = pretty.group(1) if pretty else version
    elif system_name == "darwin":
        system_name = "macos"
        distribution = "macos"
        version = platform.mac_ver()[0] or version
    elif system_name == "windows":
        distribution = "windows"
        version = platform.version()
    return {
        "os_family": system_name,
        "os_version": version,
        "architecture": architecture,
        "distribution": distribution,
    }


def recommend_mindplus_1x(system: dict[str, str]) -> dict[str, Any]:
    family = system.get("os_family", "unknown").lower()
    arch = _normalize_architecture(system.get("architecture", "unknown"))
    distro = system.get("distribution", family).lower()
    base = {
        "official_page": OFFICIAL_DOWNLOAD_PAGE,
        "architecture": arch,
        "distribution": distro,
        "priority": "prefer_1x_only_when_no_existing_mindplus",
    }
    if family == "windows" and arch == "x86_64":
        return {
            **base,
            "status": "official_direct_download",
            "version": "1.8.1 RC3.0",
            "package_type": "exe",
            "url": WINDOWS_V1_URL,
            "auto_download_allowed": True,
        }
    if family == "windows":
        return {
            **base,
            "status": "compatibility_confirmation_required",
            "version": "1.x",
            "package_type": None,
            "url": OFFICIAL_DOWNLOAD_PAGE,
            "auto_download_allowed": False,
            "reason": "Mind+ 1.x official page does not confirm a native Windows ARM package.",
        }
    if family == "macos" and arch == "x86_64":
        return {
            **base,
            "status": "official_direct_download",
            "version": "1.7.3 RC2.0",
            "package_type": "dmg",
            "url": "https://download3.dfrobot.com.cn/Mind+_Mac_V1.7.3_RC2.0.dmg",
            "auto_download_allowed": True,
        }
    if family == "macos":
        return {
            **base,
            "status": "compatibility_confirmation_required",
            "version": "1.x",
            "package_type": None,
            "url": OFFICIAL_DOWNLOAD_PAGE,
            "auto_download_allowed": False,
            "reason": "Mind+ 1.x official page does not confirm a native Apple Silicon package.",
        }
    if family == "linux":
        if "kylin" in distro:
            version = "1.7.4"
            route = "kylin"
        elif "uos" in distro or "uniontech" in distro:
            version = "1.7.4"
            route = "uos"
        elif arch.startswith("loong"):
            version = "1.7.3"
            route = "loongarch"
        elif arch.startswith("mips"):
            version = "1.7.1"
            route = "loongson-mips"
        else:
            version = "1.7.3"
            route = distro
        supported_arch = arch in {"x86_64", "arm64", "loongarch64", "mips64"}
        return {
            **base,
            "distribution": route,
            "status": "official_linux_selection_required",
            "version": version,
            "package_type": "deb_or_vendor_package",
            "url": "https://mindplus.dfrobot.com.cn/linux",
            "auto_download_allowed": False,
            "architecture_supported_by_official_route": supported_arch,
        }
    return {
        **base,
        "status": "unsupported_or_unknown_system",
        "version": "1.x",
        "package_type": None,
        "url": OFFICIAL_DOWNLOAD_PAGE,
        "auto_download_allowed": False,
    }


def download_policy(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    allowed = (
        parsed.scheme == "https"
        and parsed.hostname == "download3.dfrobot.com.cn"
        and parsed.path == "/MindPlus_Win_V1.8.1_RC3.0.exe"
    )
    return {
        "allowed": allowed,
        "url": url,
        "reason": (
            "official_allowlisted_mindplus_1x_package"
            if allowed else "download_url_not_allowlisted"
        ),
    }


def _download_file(url: str, destination: Path, timeout: int = 300) -> dict[str, Any]:
    policy = download_policy(url)
    if not policy["allowed"]:
        return {"success": False, "error": policy["reason"], "download_executed": False}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    size = 0
    started = time.monotonic()
    try:
        request = Request(url, headers={"User-Agent": "ArduinoNanoMindPlusSkill/1.0"})
        with urlopen(request, timeout=timeout) as response, temporary.open("wb") as output:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        os.replace(temporary, destination)
        return {
            "success": True,
            "download_executed": True,
            "path": str(destination.resolve()),
            "bytes": size,
            "sha256": digest.hexdigest(),
            "duration_seconds": round(time.monotonic() - started, 3),
            "installer_started": False,
            "note": "已下载官方安装包；启动安装仍需用户允许外部安装程序运行。",
        }
    except (OSError, ValueError) as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return {
            "success": False,
            "error": "official_download_failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "download_executed": True,
        }


def _visible_installer_launcher(path: Path) -> dict[str, Any]:
    if os.name != "nt":
        return {
            "success": False,
            "process_started": False,
            "error": "visible_installer_launch_only_implemented_on_windows",
        }
    try:
        # ShellExecute preserves the normal visible installer and UAC flow.
        os.startfile(str(path))  # type: ignore[attr-defined]
        return {"success": True, "process_started": True}
    except OSError as exc:
        return {
            "success": False,
            "process_started": False,
            "error": "installer_launch_failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }


def launch_installer(path: Path, launcher=_visible_installer_launcher) -> dict[str, Any]:
    installer = Path(path).expanduser().resolve()
    if not installer.is_file():
        return {
            "success": False,
            "process_started": False,
            "error": "installer_file_not_found",
            "path": str(installer),
        }
    result = launcher(installer)
    return {
        **result,
        "path": str(installer),
        "installation_completed": False,
        "note": "安装器已可见启动；请老师处理系统/UAC/安装界面，完成后重新运行环境检查。",
    }


def prepare_environment(
    *,
    installations: Optional[list[dict[str, Any]]] = None,
    system: Optional[dict[str, str]] = None,
    execute_download: bool = False,
    launch_after_download: bool = False,
    download_dir: Optional[Path] = None,
) -> dict[str, Any]:
    found = installations if installations is not None else discover_installations()
    decision = choose_environment(found)
    if not decision["install_needed"]:
        return {
            "action": "prepare-environment",
            "success": True,
            "status": "existing_mindplus_reused",
            "download_executed": False,
            "environment": decision,
        }
    detected = system or detect_system()
    recommendation = recommend_mindplus_1x(detected)
    if not recommendation.get("auto_download_allowed"):
        return {
            "action": "prepare-environment",
            "success": False,
            "status": recommendation["status"],
            "download_executed": False,
            "system": detected,
            "recommendation": recommendation,
        }
    if not execute_download:
        return {
            "action": "prepare-environment",
            "success": True,
            "status": "official_download_ready",
            "download_executed": False,
            "system": detected,
            "recommendation": recommendation,
        }
    target_dir = download_dir or (Path.home() / "Downloads")
    downloaded = _download_file(
        recommendation["url"], target_dir / "MindPlus_Win_V1.8.1_RC3.0.exe"
    )
    launched = None
    if downloaded.get("success") and launch_after_download:
        launched = launch_installer(Path(downloaded["path"]))
    return {
        "action": "prepare-environment",
        "status": (
            "installer_started"
            if launched and launched.get("success")
            else "official_package_downloaded"
            if downloaded.get("success")
            else "download_failed"
        ),
        "system": detected,
        "recommendation": recommendation,
        **downloaded,
        "installer": launched,
        "installer_started": bool(launched and launched.get("success")),
    }


def fqbn_for_backend(backend: str) -> str:
    if backend == "mindplus-1-builder":
        return V1_FQBN
    if backend == "mindplus-2-cli":
        return V2_FQBN
    raise ValueError(f"unsupported_backend: {backend}")


def _windows_port_details() -> dict[str, dict[str, str]]:
    if os.name != "nt":
        return {}
    command = [
        "powershell.exe", "-NoProfile", "-Command",
        "Get-CimInstance Win32_SerialPort | Select-Object DeviceID,Name,PNPDeviceID | ConvertTo-Json -Compress",
    ]
    execution = _run(command, timeout=20)
    if execution.get("returncode") != 0 or not execution.get("stdout"):
        return {}
    try:
        parsed = json.loads(execution["stdout"])
    except json.JSONDecodeError:
        return {}
    rows = parsed if isinstance(parsed, list) else [parsed]
    return {
        str(row.get("DeviceID", "")).upper(): {
            "name": str(row.get("Name", "")),
            "pnp_device_id": str(row.get("PNPDeviceID", "")),
        }
        for row in rows if isinstance(row, dict) and row.get("DeviceID")
    }


def scan_ports() -> list[dict[str, Any]]:
    details = _windows_port_details()
    ports: dict[str, dict[str, Any]] = {}
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM"
            ) as key:
                index = 0
                while True:
                    try:
                        device, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    index += 1
                    address = str(value).upper()
                    extra = details.get(address, {})
                    combined = " ".join(
                        [device, extra.get("name", ""), extra.get("pnp_device_id", "")]
                    ).lower()
                    bluetooth = "bth" in combined or "bluetooth" in combined
                    nano_likely = any(
                        marker in combined
                        for marker in ("ch340", "ch341", "ft232", "cp210", "usb serial", "arduino nano")
                    )
                    ports[address] = {
                        "address": address,
                        "device_name": device,
                        "label": extra.get("name") or address,
                        "pnp_device_id": extra.get("pnp_device_id"),
                        "is_bluetooth": bluetooth,
                        "nano_likely": nano_likely,
                        "eligible_for_upload": bool(address) and not bluetooth,
                    }
        except OSError:
            pass
    return sorted(ports.values(), key=lambda item: item["address"])


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
    likely = [item for item in eligible if item.get("nano_likely")]
    if len(likely) == 1:
        return str(likely[0]["address"]).upper(), None
    if len(likely) > 1:
        return None, "multiple_likely_nano_ports_require_selection"
    if len(eligible) == 1:
        return str(eligible[0]["address"]).upper(), None
    if not eligible:
        return None, "no_wired_upload_port_found"
    return None, "multiple_wired_ports_require_selection"


def _pin_name(value: Any) -> str:
    text = str(value).strip().upper()
    if text.isdigit():
        return f"D{text}"
    return text


def validate_pin_assignments(assignments: list[dict[str, Any]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    seen: dict[str, str] = {}
    pwm = {"D3", "D5", "D6", "D9", "D10", "D11"}
    for item in assignments:
        module = str(item.get("module", "module"))
        pin = _pin_name(item.get("pin", ""))
        mode = str(item.get("mode", "")).lower()
        if pin in {"A6", "A7"} and mode != "analog_input":
            errors.append({"code": "a6_a7_analog_input_only", "module": module, "pin": pin})
        if mode == "pwm_output" and pin not in pwm:
            errors.append({"code": "pin_has_no_pwm", "module": module, "pin": pin})
        if pin in {"D0", "D1"}:
            errors.append({"code": "usb_serial_pin_conflict", "module": module, "pin": pin})
        if pin in seen:
            errors.append({
                "code": "duplicate_pin_assignment", "module": module, "pin": pin,
                "conflicts_with": seen[pin],
            })
        else:
            seen[pin] = module
    return errors


def _safe_project_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    return (cleaned or "nano-project")[:48]


def prepare_code(code: str, project_name: str = "nano-project") -> Path:
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code_required")
    safe_name = _safe_project_name(project_name)
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]
    sketch_dir = Path(tempfile.gettempdir()) / "nano-mindplus-sketches" / f"{safe_name}-{digest}"
    sketch_dir.mkdir(parents=True, exist_ok=True)
    (sketch_dir / f"{sketch_dir.name}.ino").write_text(code, encoding="utf-8")
    return sketch_dir


def _validate_sketch(path_value: str) -> tuple[Optional[Path], Optional[str]]:
    path = Path(path_value).expanduser().resolve()
    sketch_dir = path.parent if path.is_file() and path.suffix.lower() == ".ino" else path
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
                "--fqbn", V2_FQBN,
                "--build-path", str(build_dir),
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
            "-hardware", str(arduino / "hardware"),
            "-tools", str(arduino / "arduino-builder"),
            "-tools", str(arduino / "hardware" / "tools" / "avr"),
            "-built-in-libraries", str(arduino / "libraries"),
            "-libraries", str(arduino / "libraries"),
            f"-fqbn={V1_FQBN}",
            "-ide-version=10819",
            "-build-path", str(build_dir),
            str(sketch_file),
        ]
    raise ValueError(f"unsupported_backend: {backend}")


def _compile_diagnostics(execution: dict[str, Any]) -> dict[str, Any]:
    raw = "\n".join(
        value for value in (execution.get("stdout", ""), execution.get("stderr", "")) if value
    )
    lines = [
        line.strip() for line in raw.splitlines()
        if re.search(r"(?i)(fatal error|error:|undefined reference|multiple definition)", line)
    ][:20]
    if re.search(r"(?i)fatal error:.*No such file", raw):
        error_type = "missing_library_or_header"
        suggestions = ["先在 Mind+ 扩展或库环境中补齐对应模块库，再重新编译。"]
    elif re.search(r"(?i)was not declared|expected .+ before|no matching function", raw):
        error_type = "cpp_syntax_or_api_error"
        suggestions = ["从第一条编译错误开始修正代码或模块 API。"]
    elif execution.get("timed_out"):
        error_type = "compile_timeout"
        suggestions = ["关闭占用构建目录的程序并重试。"]
    else:
        error_type = "compile_failed"
        suggestions = ["保留 error_lines，修改完整程序后重新编译。"]
    return {
        "error_type": error_type,
        "error_lines": lines,
        "diagnostic_excerpt": raw[-12000:],
        "suggestions": suggestions,
    }


def _selected_context(decision: dict[str, Any]) -> Optional[dict[str, Any]]:
    selected = decision.get("selected")
    if not selected:
        return None
    context = dict(selected)
    if context["backend"] == "mindplus-1-builder":
        context["arduino"] = str(Path(context["root"]) / "Arduino")
    return context


def compile_result(context: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    try:
        if request.get("code") is not None:
            sketch_dir = prepare_code(
                request["code"], request.get("project_name", "nano-project")
            )
        elif request.get("sketch"):
            sketch_dir, error = _validate_sketch(str(request["sketch"]))
            if error or not sketch_dir:
                return {"action": "compile", "success": False, "error": error}
        else:
            return {"action": "compile", "success": False, "error": "sketch_or_code_required"}
    except (OSError, ValueError) as exc:
        return {"action": "compile", "success": False, "error": str(exc)}

    build_hash = hashlib.sha256(
        f"{context['backend']}:{sketch_dir}".encode("utf-8")
    ).hexdigest()[:12]
    build_dir = Path(tempfile.gettempdir()) / "nano-mindplus-builds" / build_hash
    build_dir.mkdir(parents=True, exist_ok=True)
    sketch_file = sketch_dir / f"{sketch_dir.name}.ino"
    command = build_compile_command(context, sketch_file, build_dir)
    execution = _run(command, timeout=int(request.get("timeout", 600)))
    hex_files = sorted(build_dir.glob("*.hex"))
    application_hex = [path for path in hex_files if not path.name.endswith("with_bootloader.hex")]
    success = execution.get("returncode") == 0 and bool(application_hex)
    result = {
        "action": "compile",
        "success": success,
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
        result["diagnostics"] = _compile_diagnostics(execution)
    return result


def _upload_diagnostics(execution: dict[str, Any]) -> dict[str, Any]:
    raw = "\n".join(
        value for value in (execution.get("stdout", ""), execution.get("stderr", "")) if value
    )
    lowered = raw.lower()
    if "ser_open" in lowered or "can't open device" in lowered or "access is denied" in lowered:
        error_type = "serial_port_unavailable"
        suggestions = ["关闭 Mind+ 串口监视器和其他占用该 COM 口的软件，再重试。"]
    elif "getsync" in lowered or "not in sync" in lowered or "programmer is not responding" in lowered:
        error_type = "bootloader_sync_failed"
        suggestions = ["确认板型为经典 Nano ATmega328P，并检查 USB 数据线和 Bootloader。"]
    elif "invalid device signature" in lowered or "device signature" in lowered:
        error_type = "unexpected_mcu_signature"
        suggestions = ["停止烧录；当前设备可能不是 ATmega328P Nano。"]
    else:
        error_type = "upload_failed"
        suggestions = ["检查 Nano 驱动、数据线、端口和复位状态。"]
    return {
        "error_type": error_type,
        "diagnostic_excerpt": raw[-12000:],
        "suggestions": suggestions,
    }


def _avrdude_command(
    avrdude: str, config: str, hex_file: Path, port: str, baud: int
) -> list[str]:
    return [
        str(avrdude),
        "-C", str(config),
        "-v",
        "-p", "atmega328p",
        "-c", "arduino",
        "-P", str(port).upper(),
        "-b", str(baud),
        "-D",
        "-U", f"flash:w:{hex_file}:i",
    ]


def run_upload_attempts(
    *,
    avrdude: str,
    config: str,
    hex_file: Path,
    port: str,
    runner=_run,
    timeout: int = 180,
    baud_order: tuple[int, ...] = (57600, 115200),
) -> dict[str, Any]:
    if not baud_order or any(baud not in {57600, 115200} for baud in baud_order):
        raise ValueError("bootloader_baud_order_invalid")
    attempts: list[dict[str, Any]] = []
    for baud in baud_order:
        execution = runner(
            _avrdude_command(avrdude, config, hex_file, port, baud), timeout=timeout
        )
        attempts.append(execution)
        raw = "\n".join(
            value for value in (execution.get("stdout", ""), execution.get("stderr", "")) if value
        )
        success = execution.get("returncode") == 0 and (
            "verified" in raw.lower() or "avrdude done" in raw.lower()
        )
        if success:
            return {
                "action": "upload",
                "success": True,
                "upload_executed": True,
                "firmware_written": True,
                "hardware_runtime_verified": False,
                "port": str(port).upper(),
                "baud": baud,
                "bootloader_profile": (
                    "classic_nano_57600" if baud == 57600 else "new_bootloader_compatible"
                ),
                "attempts": attempts,
                "hex_sha256": (
                    hashlib.sha256(hex_file.read_bytes()).hexdigest()
                    if hex_file.is_file() else None
                ),
                "note": "固件写入并校验成功；传感器和执行器效果仍需现场观察。",
            }
        diagnostics = _upload_diagnostics(execution)
        if diagnostics["error_type"] != "bootloader_sync_failed":
            return {
                "action": "upload", "success": False, "upload_executed": True,
                "firmware_written": False, "port": str(port).upper(),
                "attempts": attempts, "diagnostics": diagnostics,
            }
    return {
        "action": "upload", "success": False, "upload_executed": True,
        "firmware_written": False, "port": str(port).upper(),
        "attempts": attempts, "diagnostics": _upload_diagnostics(attempts[-1]),
    }


def _find_avrdude(context: dict[str, Any]) -> tuple[Optional[Path], Optional[Path]]:
    if context["backend"] == "mindplus-1-builder":
        arduino = Path(context["arduino"])
        tool_root = arduino / "hardware" / "tools" / "avr"
        return tool_root / "bin" / "avrdude.exe", tool_root / "etc" / "avrdude.conf"
    config = Path(context["config"])
    data_root = config.parent
    package_root = data_root / "packages" / "mindplus" / "tools"
    avrdudes = sorted(package_root.glob("avrdude/*/bin/avrdude.exe"), reverse=True)
    if not avrdudes:
        avrdudes = sorted(package_root.glob("avr-gcc/*/bin/avrdude.exe"), reverse=True)
    if not avrdudes:
        return None, None
    avrdude = avrdudes[0]
    candidates = [avrdude.parents[1] / "etc" / "avrdude.conf", avrdude.parents[2] / "etc" / "avrdude.conf"]
    return avrdude, next((path for path in candidates if path.is_file()), candidates[0])


def upload_result(
    context: dict[str, Any], request: dict[str, Any], compiled: dict[str, Any]
) -> dict[str, Any]:
    ports = scan_ports()
    selected, error = select_upload_port(ports, request.get("port"))
    if error or not selected:
        return {
            "action": "upload", "success": False, "error": error,
            "upload_executed": False, "ports": ports,
        }
    hex_file = Path(str(compiled.get("application_hex", "")))
    if not hex_file.is_file():
        return {
            "action": "upload", "success": False,
            "error": "compiled_hex_not_found", "upload_executed": False,
        }
    avrdude, avrdude_config = _find_avrdude(context)
    if not avrdude or not avrdude.is_file() or not avrdude_config or not avrdude_config.is_file():
        return {
            "action": "upload", "success": False,
            "error": "avrdude_toolchain_not_found", "upload_executed": False,
        }
    return run_upload_attempts(
        avrdude=str(avrdude), config=str(avrdude_config), hex_file=hex_file,
        port=selected, timeout=int(request.get("upload_timeout", 180)),
        baud_order=tuple(request.get("bootloader_baud_order", (57600, 115200))),
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
            "action": "compile-upload", "success": False,
            "stage": "compile", "compile": compiled, "upload": None,
            "automatic_upload": True,
            "hardware_detected": False,
            "auto_repair_recommended": True,
            "repair_scope": "code",
            "max_agent_repair_attempts": 2,
            "teacher_message": "程序没有通过编译检查；请根据报错修改完整程序，然后自动重试。",
        }
    uploaded = upload_fn(context, request, compiled)
    hardware_missing = uploaded.get("error") == "no_wired_upload_port_found"
    hardware_detected = not hardware_missing
    if uploaded.get("success"):
        stage = "complete"
        teacher_message = "已检测到 Arduino Nano，程序已自动上传并完成写入校验。"
    elif hardware_missing:
        stage = "awaiting-hardware"
        teacher_message = (
            "未检测到有线 Arduino Nano。请用可传数据的 USB 线接入硬件；"
            "接入后再次运行即可自动上传，不需要重新确认。"
        )
    else:
        stage = "upload"
        teacher_message = "已进入自动上传，但遇到硬件或串口问题；请按诊断提示处理后重试。"
    return {
        "action": "compile-upload",
        "success": bool(uploaded.get("success")),
        "stage": stage,
        "automatic_upload": True,
        "hardware_detected": hardware_detected,
        "hardware_connection_required": hardware_missing,
        "retry_when_hardware_connected": hardware_missing,
        "teacher_message": teacher_message,
        "compile": compiled,
        "upload": uploaded,
    }


def doctor_result() -> dict[str, Any]:
    installations = discover_installations()
    decision = choose_environment(installations)
    ports = scan_ports()
    selected_port, port_error = select_upload_port(ports)
    return {
        "action": "doctor",
        "success": not decision["install_needed"],
        "ready_for_compile": not decision["install_needed"],
        "ready_for_upload": not decision["install_needed"] and selected_port is not None,
        "hardware_pending": selected_port is None,
        "system": detect_system(),
        "installations": installations,
        "environment": decision,
        "ports": ports,
        "recommended_port": selected_port,
        "port_status": port_error,
    }


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action == "doctor":
        result = doctor_result()
    elif action == "prepare-environment":
        result = prepare_environment(
            execute_download=bool(request.get("download", False)),
            launch_after_download=bool(request.get("launch_installer", False)),
            download_dir=(Path(request["download_dir"]) if request.get("download_dir") else None),
        )
    elif action == "ports":
        ports = scan_ports()
        selected, error = select_upload_port(ports, request.get("port"))
        result = {
            "action": "ports", "success": True, "ports": ports,
            "recommended_port": selected, "port_status": error,
        }
    elif action in {"compile", "compile-upload"}:
        decision = choose_environment(discover_installations())
        context = _selected_context(decision)
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
    parser = argparse.ArgumentParser(description="Arduino Nano Mind+ bridge")
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
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Discover and explicitly prepare the local OpenSCAD dependency."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence


OFFICIAL_DOWNLOAD_URL = "https://openscad.org/downloads.html"
WINGET_PACKAGE_ID = "OpenSCAD.OpenSCAD"
_VERSION_PATTERN = re.compile(r"OpenSCAD(?:\s+version)?\s+([^\s]+)", re.IGNORECASE)

Runner = Callable[..., subprocess.CompletedProcess[str]]
Which = Callable[[str], str | None]


def _run(command: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, **kwargs)


def _candidate_paths(
    platform_name: str,
    environ: Mapping[str, str],
    which: Which,
) -> list[Path]:
    names = ["openscad.com", "openscad.exe", "openscad"] if platform_name.startswith("win") else ["openscad"]
    candidates: list[Path] = []
    override = environ.get("OPENSCAD_BINARY", "").strip()
    if override:
        candidates.append(Path(override).expanduser())
    for name in names:
        found = which(name)
        if found:
            candidates.append(Path(found))
    if platform_name.startswith("win"):
        for variable in ("ProgramFiles", "ProgramW6432", "LOCALAPPDATA"):
            root = environ.get(variable, "").strip()
            if not root:
                continue
            base = Path(root)
            if variable == "LOCALAPPDATA":
                base = base / "Programs"
            candidates.extend((base / "OpenSCAD" / "openscad.com", base / "OpenSCAD" / "openscad.exe"))
    elif platform_name == "darwin":
        candidates.append(Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"))

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def status(
    *,
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    which: Which = shutil.which,
    runner: Runner = _run,
) -> dict[str, Any]:
    """Return a compact, non-mutating OpenSCAD dependency probe."""
    platform_name = platform_name or sys.platform
    environ = environ if environ is not None else os.environ
    for candidate in _candidate_paths(platform_name, environ, which):
        if not candidate.is_file():
            continue
        version = None
        version_detail = None
        try:
            completed = runner(
                [str(candidate), "--version"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            raw = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip())
            match = _VERSION_PATTERN.search(raw)
            version = match.group(1) if match else None
            if completed.returncode != 0:
                version_detail = f"version_probe_exit_{completed.returncode}"
            elif not version:
                version_detail = "version_unreadable"
        except (OSError, subprocess.SubprocessError) as exc:
            version_detail = f"{type(exc).__name__}: {exc}"
        result: dict[str, Any] = {
            "success": True,
            "action": "openscad-status",
            "installed": True,
            "state": "ready",
            "path": str(candidate.resolve()),
            "version": version,
            "official_download_url": OFFICIAL_DOWNLOAD_URL,
        }
        if version_detail:
            result["version_detail"] = version_detail
        return result
    return {
        "success": True,
        "action": "openscad-status",
        "installed": False,
        "state": "missing",
        "path": None,
        "version": None,
        "official_download_url": OFFICIAL_DOWNLOAD_URL,
    }


def prepare(
    *,
    allow_install: bool = False,
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    which: Which = shutil.which,
    runner: Runner = _run,
) -> dict[str, Any]:
    """Install OpenSCAD through its documented WinGet package after consent."""
    platform_name = platform_name or sys.platform
    environ = environ if environ is not None else os.environ
    before = status(platform_name=platform_name, environ=environ, which=which, runner=runner)
    if before["installed"]:
        return {
            **before,
            "action": "openscad-prepare",
            "changed": False,
            "install_method": "existing-installation",
        }
    if not allow_install:
        return {
            "success": False,
            "action": "openscad-prepare",
            "installed": False,
            "changed": False,
            "state": "awaiting-install-confirmation",
            "confirmation_required": True,
            "install_method": "winget" if platform_name.startswith("win") else "manual",
            "official_download_url": OFFICIAL_DOWNLOAD_URL,
            "beginner_message": "电脑还没有 OpenSCAD。确认要安装后，我才能启动官方安装流程。",
        }
    if not platform_name.startswith("win"):
        return {
            "success": False,
            "action": "openscad-prepare",
            "installed": False,
            "changed": False,
            "state": "manual-install-required",
            "error": "automatic_openscad_install_only_supported_on_windows",
            "official_download_url": OFFICIAL_DOWNLOAD_URL,
        }
    winget = which("winget")
    if not winget:
        return {
            "success": False,
            "action": "openscad-prepare",
            "installed": False,
            "changed": False,
            "state": "manual-install-required",
            "error": "winget_not_found",
            "official_download_url": OFFICIAL_DOWNLOAD_URL,
            "beginner_message": "这台电脑没有 WinGet，请从 OpenSCAD 官网手动安装。",
        }

    command = [
        winget,
        "install",
        "--id",
        WINGET_PACKAGE_ID,
        "-e",
        "--source",
        "winget",
        "--accept-source-agreements",
        "--accept-package-agreements",
    ]
    try:
        completed = runner(command, capture_output=True, text=True, timeout=900, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "success": False,
            "action": "openscad-prepare",
            "installed": False,
            "changed": False,
            "state": "install-failed",
            "error": "winget_launch_failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "official_download_url": OFFICIAL_DOWNLOAD_URL,
        }
    after = status(platform_name=platform_name, environ=environ, which=which, runner=runner)
    if completed.returncode == 0 and after["installed"]:
        return {
            **after,
            "action": "openscad-prepare",
            "changed": True,
            "install_method": "winget",
            "package_id": WINGET_PACKAGE_ID,
        }
    detail = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip()
    )[-4000:]
    return {
        "success": False,
        "action": "openscad-prepare",
        "installed": bool(after["installed"]),
        "changed": False,
        "state": "install-failed",
        "error": "winget_install_failed" if completed.returncode else "openscad_not_found_after_install",
        "exit_code": completed.returncode,
        "detail": detail,
        "official_download_url": OFFICIAL_DOWNLOAD_URL,
    }

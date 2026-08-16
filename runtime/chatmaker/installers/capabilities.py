"""Bounded, read-only host capability detection for the universal installer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import shutil
import sys
from typing import Any, Mapping

from chatmaker.hardware import nano_mindplus


def _family(system_name: str) -> str:
    lowered = system_name.strip().casefold()
    if lowered == "windows":
        return "windows"
    if lowered in {"darwin", "macos"}:
        return "macos"
    if lowered == "linux":
        return "linux"
    return lowered or "unknown"


def _architecture(machine: str) -> str:
    lowered = machine.strip().casefold()
    if lowered in {"amd64", "x86_64", "x64"}:
        return "x86_64"
    if lowered in {"arm64", "aarch64"}:
        return "arm64"
    return lowered or "unknown"


def _safe_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _safe_is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _unique_paths(paths: list[Path], family: str) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).casefold() if family == "windows" else str(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def _path_from_environ(environ: Mapping[str, str], key: str) -> Path | None:
    value = environ.get(key)
    return Path(value).expanduser() if value else None


def _mindplus_roots(home: Path, environ: Mapping[str, str], family: str) -> tuple[list[Path], list[Path], list[Path]]:
    v1 = [path for path in (_path_from_environ(environ, "MINDPLUS1_ROOT"),) if path]
    v2 = [path for path in (_path_from_environ(environ, "MINDPLUS2_ROOT"),) if path]
    configs: list[Path] = []
    if family == "windows":
        v1.extend([Path(r"C:\Program Files (x86)\Mind+"), Path(r"C:\Program Files\Mind+")])
        v2.extend([Path(r"C:\Program Files (x86)\Mind+2"), Path(r"C:\Program Files\Mind+2")])
        local = _path_from_environ(environ, "LOCALAPPDATA") or home / "AppData" / "Local"
        configs.append(local / "mind+" / "Arduino" / "arduino-cli.yaml")
    elif family == "macos":
        v1.append(Path("/Applications/Mind+.app"))
        v2.append(Path("/Applications/Mind+2.app"))
        configs.append(home / "Library" / "Application Support" / "mind+" / "Arduino" / "arduino-cli.yaml")
    else:
        v1.append(home / ".local" / "share" / "Mind+")
        v2.append(home / ".local" / "share" / "Mind+2")
        configs.append(home / ".config" / "mind+" / "Arduino" / "arduino-cli.yaml")
    explicit_config = _path_from_environ(environ, "MINDPLUS2_CONFIG")
    if explicit_config:
        configs.insert(0, explicit_config)
    return (
        _unique_paths(v1, family),
        _unique_paths(v2, family),
        _unique_paths(configs, family),
    )


def _first_command(commands: tuple[str, ...]) -> tuple[str | None, str | None]:
    for command in commands:
        found = shutil.which(command)
        if found:
            return command, found
    return None, None


def _candidate_skill_roots(home: Path, environ: Mapping[str, str], family: str) -> list[dict[str, Any]]:
    codex_home = _path_from_environ(environ, "CODEX_HOME") or home / ".codex"
    workbuddy_home = _path_from_environ(environ, "WORKBUDDY_HOME")
    workbuddy_config = _path_from_environ(environ, "WORKBUDDY_CONFIG")
    if workbuddy_home is None:
        workbuddy_home = workbuddy_config.parent if workbuddy_config else home / ".workbuddy"
    roots: list[tuple[str, Path, bool]] = [("codex", codex_home / "skills", "CODEX_HOME" in environ)]
    explicit_root = _path_from_environ(environ, "CHATMAKER_SKILL_ROOT")
    if explicit_root:
        roots.insert(0, ("explicit", explicit_root, True))
    roots.append(("workbuddy", workbuddy_home / "skills", bool(workbuddy_config or "WORKBUDDY_HOME" in environ)))
    return [
        {"host": host, "path": str(path), "available": _safe_is_dir(path), "explicit": explicit}
        for host, path, explicit in roots
    ]


def _mcp_configs(home: Path, environ: Mapping[str, str]) -> list[dict[str, Any]]:
    workbuddy = _path_from_environ(environ, "WORKBUDDY_CONFIG") or home / ".workbuddy" / "mcp.json"
    codex_home = _path_from_environ(environ, "CODEX_HOME") or home / ".codex"
    configs: list[tuple[str, Path, bool]] = [
        ("workbuddy", workbuddy, "WORKBUDDY_CONFIG" in environ),
        ("codex", codex_home / "config.toml", "CODEX_HOME" in environ),
    ]
    explicit = _path_from_environ(environ, "CHATMAKER_MCP_CONFIG")
    if explicit:
        configs.insert(0, ("explicit", explicit, True))
    return [
        {"host": host, "path": str(path), "available": _safe_is_file(path), "explicit": is_explicit}
        for host, path, is_explicit in configs
    ]


@dataclass(frozen=True)
class CapabilityReport:
    """Serializable snapshot of optional local capabilities.

    Missing optional dependencies are reported as unavailable; they do not make
    the capability probe itself fail.
    """

    value: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.value,
            "skill_roots": [dict(item) for item in self.value["skill_roots"]],
            "candidate_skill_roots": [dict(item) for item in self.value["skill_roots"]],
            "mcp_configs": [dict(item) for item in self.value["mcp_configs"]],
        }


def probe_environment(
    *,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> CapabilityReport:
    """Inspect a bounded set of host prerequisites without changing local state."""
    environment = dict(os_environ() if environ is None else environ)
    selected_home = Path(home).expanduser() if home is not None else Path.home()
    system_name = platform.system()
    family = _family(system_name)
    terminal_env = environment.get("COMSPEC") if family == "windows" else environment.get("SHELL")
    terminal_command, terminal_path = _first_command(
        ("pwsh", "powershell", "cmd") if family == "windows" else ("zsh", "bash", "sh")
    )
    browser_command, browser_path = _first_command(
        ("chrome", "msedge", "firefox")
        if family == "windows"
        else ("google-chrome", "chrome", "firefox", "safari")
    )
    explicit_cli = _path_from_environ(environment, "ARDUINO_CLI")
    cli_path = str(explicit_cli) if explicit_cli and _safe_is_file(explicit_cli) else shutil.which("arduino-cli")
    v1_roots, v2_roots, configs = _mindplus_roots(selected_home, environment, family)
    try:
        installations = nano_mindplus.discover_installations(
            v1_roots=v1_roots,
            v2_roots=v2_roots,
            v2_config_candidates=configs,
        )
    except OSError:
        installations = []
    try:
        ports = nano_mindplus.scan_ports()
    except OSError:
        ports = []
    skill_roots = _candidate_skill_roots(selected_home, environment, family)
    mcp_configs = _mcp_configs(selected_home, environment)
    value = {
        "success": True,
        "home": str(selected_home),
        "os": {"family": family, "name": system_name, "version": platform.release()},
        "cpu": {"architecture": _architecture(platform.machine())},
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "terminal": {
            "available": bool(terminal_env or terminal_path),
            "command": terminal_command or terminal_env,
            "path": terminal_path or terminal_env,
        },
        "browser": {"available": bool(browser_path), "command": browser_command, "path": browser_path},
        "serial": {"available": bool(ports), "ports": ports},
        "mindplus": {"available": bool(installations), "installations": installations},
        "arduino_cli": {"available": bool(cli_path), "path": cli_path},
        "skill_roots": skill_roots,
        "mcp_configs": mcp_configs,
    }
    return CapabilityReport(value)


def os_environ() -> Mapping[str, str]:
    """Keep environment access in one place so a supplied mapping is isolated."""
    import os

    return os.environ


__all__ = ["CapabilityReport", "probe_environment"]

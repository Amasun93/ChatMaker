#!/usr/bin/env python3
"""Install ChatMaker Skills and the Nano stdio MCP without replacing unrelated settings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from chatmaker.installers.skill_bundle import (
    doctor_bundle,
)
from chatmaker.installers.transaction import InstallTransaction


SERVER_KEY = "arduino-nano-mindplus"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILL_MANIFEST_NAME = "chatmaker-workbuddy-skills.json"
OPERATION_MANIFEST_NAME = "chatmaker-workbuddy-install.json"
CONTENT_MANAGER = "chatmaker-pack"


def _with_content_boundary(result: dict[str, Any]) -> dict[str, Any]:
    result["content_manager"] = CONTENT_MANAGER
    result["knowledge_packs_installed"] = []
    return result


def default_config_path() -> Path:
    return Path.home() / ".workbuddy" / "mcp.json"


def install(
    config_path: Path,
    python_executable: str = sys.executable,
    source_skills: Path = PROJECT_ROOT / "skills",
) -> dict[str, Any]:
    config_path = config_path.expanduser().absolute()
    workbuddy_home = config_path.parent
    server_module = PACKAGE_ROOT / "integrations" / "mcp.py"
    if not server_module.is_file():
        raise FileNotFoundError("generic_mcp_server.py is missing")
    data = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be an object")
    previous = servers.get(SERVER_KEY)
    server = {
        "type": "stdio",
        "command": str(Path(python_executable).resolve()) if Path(python_executable).exists() else python_executable,
        "args": ["-m", "chatmaker.integrations.mcp"],
        "cwd": str(PACKAGE_ROOT.parent.resolve()),
        "env": {"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"},
        "defer_loading": False,
        "disabled": False,
    }
    transaction = InstallTransaction(
        root=workbuddy_home / ".chatmaker",
        installation_id=f"workbuddy:{config_path}",
    )
    result = transaction.apply(
        [
            {
                "kind": "skill_bundle",
                "source": Path(source_skills).expanduser().absolute(),
                "path": workbuddy_home / "skills",
                "names": ["chatmaker", "chatduino", "chatweb"],
            },
            {
                "kind": "mcp_server",
                "path": config_path,
                "server_key": SERVER_KEY,
                "server": server,
            },
        ]
    )
    value = result.to_dict()
    backup = next(
        (
            path
            for identity, path in result.details.get("backups", {}).items()
            if identity.startswith("mcp:")
        ),
        None,
    )
    return _with_content_boundary(
        {
            **value,
            "config": str(config_path),
            "backup": str(backup) if backup else None,
            "server": SERVER_KEY,
            "installed_skills": ["chatmaker", "chatduino", "chatweb"],
            "replaced_existing_entry": previous is not None,
            "preserved_other_servers": len(servers) - (1 if SERVER_KEY in servers else 0),
            "restart_workbuddy": True,
        }
    )


def uninstall(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().absolute()
    workbuddy_home = config_path.parent
    result = InstallTransaction(
        root=workbuddy_home / ".chatmaker",
        installation_id=f"workbuddy:{config_path}",
    ).uninstall()
    return {
        **result.to_dict(),
        "config": str(config_path),
        "restart_workbuddy": True,
    }


def doctor(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    skills = doctor_bundle(config_path.parent)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        server = config.get("mcpServers", {}).get(SERVER_KEY)
    except (OSError, json.JSONDecodeError, AttributeError):
        server = None
    return _with_content_boundary(
        {
            "success": skills["success"] and isinstance(server, dict),
            "config": str(config_path),
            "mcp_server_ready": isinstance(server, dict),
            "skills": skills["skills"],
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Install, inspect, or uninstall ChatMaker for WorkBuddy")
    parser.add_argument("action", nargs="?", choices=("install", "doctor", "uninstall"), default="install")
    parser.add_argument("--config", default=str(default_config_path()))
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    try:
        if args.action == "install":
            result = install(Path(args.config), args.python)
        elif args.action == "uninstall":
            result = uninstall(Path(args.config))
        else:
            result = doctor(Path(args.config))
    except Exception as exc:
        result = {
            "success": False, "error": "workbuddy_mcp_install_failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

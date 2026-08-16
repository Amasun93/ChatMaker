#!/usr/bin/env python3
"""Install ChatMaker Skills and the Nano stdio MCP without replacing unrelated settings."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any

from chatmaker.installers.skill_bundle import (
    _write_json_atomic,
    doctor_bundle,
    install_bundle,
    uninstall_bundle,
)


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
    config_path = config_path.expanduser().resolve()
    workbuddy_home = config_path.parent
    operation_manifest = workbuddy_home / OPERATION_MANIFEST_NAME
    if operation_manifest.exists():
        raise FileExistsError(
            f"existing ChatMaker install manifest must be uninstalled first: {operation_manifest}"
        )
    server_module = PACKAGE_ROOT / "integrations" / "mcp.py"
    if not server_module.is_file():
        raise FileNotFoundError("generic_mcp_server.py is missing")
    data = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be an object")
    previous = servers.get(SERVER_KEY)
    servers[SERVER_KEY] = {
        "type": "stdio",
        "command": str(Path(python_executable).resolve()) if Path(python_executable).exists() else python_executable,
        "args": ["-m", "chatmaker.integrations.mcp"],
        "cwd": str(PACKAGE_ROOT.parent.resolve()),
        "env": {"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"},
        "defer_loading": False,
        "disabled": False,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    config_existed = config_path.is_file()
    if config_path.is_file():
        backup = config_path.with_name(f"mcp.json.backup-{time.time_ns()}")
        shutil.copy2(config_path, backup)
    skill_result = install_bundle(workbuddy_home, source_skills, SKILL_MANIFEST_NAME)
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, dir=config_path.parent,
            prefix="mcp-", suffix=".json.tmp"
        ) as temporary:
            json.dump(data, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
            temporary_name = temporary.name
        os.replace(temporary_name, config_path)
        _write_json_atomic(
            operation_manifest,
            {
                "schema_version": "1.0",
                "config": str(config_path),
                "config_existed": config_existed,
                "config_backup": str(backup) if backup else None,
                "skill_manifest": skill_result["manifest"],
            },
        )
    except Exception:
        uninstall_bundle(workbuddy_home, SKILL_MANIFEST_NAME)
        raise
    return _with_content_boundary(
        {
            "success": True,
            "config": str(config_path),
            "backup": str(backup) if backup else None,
            "manifest": str(operation_manifest),
            "server": SERVER_KEY,
            "installed_skills": skill_result["installed_skills"],
            "replaced_existing_entry": previous is not None,
            "preserved_other_servers": len(servers) - 1,
            "restart_workbuddy": True,
        }
    )


def uninstall(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    workbuddy_home = config_path.parent
    operation_manifest = workbuddy_home / OPERATION_MANIFEST_NAME
    if not operation_manifest.is_file():
        raise FileNotFoundError(f"install manifest not found: {operation_manifest}")
    manifest = json.loads(operation_manifest.read_text(encoding="utf-8"))
    recorded_config = Path(manifest["config"]).resolve()
    if recorded_config != config_path:
        raise ValueError(f"manifest belongs to another config: {recorded_config}")

    backup_value = manifest.get("config_backup")
    if manifest.get("config_existed"):
        backup = Path(backup_value).resolve() if backup_value else None
        if backup is None or not backup.is_file():
            raise FileNotFoundError(f"WorkBuddy config backup not found: {backup}")
        shutil.copy2(backup, config_path)
        config_restored = True
    else:
        if config_path.exists():
            config_path.unlink()
        config_restored = False

    skills = uninstall_bundle(workbuddy_home, SKILL_MANIFEST_NAME)
    operation_manifest.unlink()
    return {
        "success": True,
        "config": str(config_path),
        "config_restored": config_restored,
        "restored_skills": skills["restored_skills"],
        "removed_skills": skills["removed_skills"],
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

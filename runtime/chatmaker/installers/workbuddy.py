#!/usr/bin/env python3
"""Install the Nano stdio MCP entry while preserving existing servers."""

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


SERVER_KEY = "arduino-nano-mindplus"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SERVER = PACKAGE_ROOT / "integrations" / "workbuddy_mcp.py"


def default_config_path() -> Path:
    return Path.home() / ".workbuddy" / "mcp.json"


def install(config_path: Path, python_executable: str = sys.executable) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    if not SERVER.is_file():
        raise FileNotFoundError("workbuddy_mcp_server.py is missing")
    data = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be an object")
    previous = servers.get(SERVER_KEY)
    servers[SERVER_KEY] = {
        "type": "stdio",
        "command": str(Path(python_executable).resolve()) if Path(python_executable).exists() else python_executable,
        "args": [str(SERVER.resolve())],
        "cwd": str(PACKAGE_ROOT.resolve()),
        "env": {"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"},
        "defer_loading": False,
        "disabled": False,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if config_path.is_file():
        backup = config_path.with_name(f"mcp.json.backup-{int(time.time())}")
        shutil.copy2(config_path, backup)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=config_path.parent,
        prefix="mcp-", suffix=".json.tmp"
    ) as temporary:
        json.dump(data, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_name = temporary.name
    os.replace(temporary_name, config_path)
    return {
        "success": True,
        "config": str(config_path),
        "backup": str(backup) if backup else None,
        "server": SERVER_KEY,
        "replaced_existing_entry": previous is not None,
        "preserved_other_servers": len(servers) - 1,
        "restart_workbuddy": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Arduino Nano Mind+ WorkBuddy MCP")
    parser.add_argument("--config", default=str(default_config_path()))
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    try:
        result = install(Path(args.config), args.python)
    except Exception as exc:
        result = {
            "success": False, "error": "workbuddy_mcp_install_failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

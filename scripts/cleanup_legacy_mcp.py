#!/usr/bin/env python3
"""Remove only legacy ChatMaker MCP registrations from one explicit config file.

This migration helper never searches for Codex, WorkBuddy, or other hosts. The
user supplies the exact JSON configuration path shown by their host.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any


OWNED_KEYS = ("chatmaker", "arduino-nano-mindplus")
OWNED_MODULES = (
    "chatmaker.integrations.mcp",
    "chatmaker.integrations.workbuddy_mcp",
)


def _owned_server(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    command = str(value.get("command", "")).replace("\\", "/").casefold()
    args = [str(item) for item in value.get("args", [])] if isinstance(value.get("args", []), list) else []
    if command.endswith("chatmaker-workbuddy-mcp") or command.endswith("chatmaker-workbuddy-mcp.exe"):
        return True
    return any(module in args for module in OWNED_MODULES)


def _atomic_write(path: Path, data: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def cleanup(config: Path, *, dry_run: bool = False) -> dict[str, Any]:
    target = config.expanduser().resolve()
    if not target.is_file():
        return {"success": False, "status": "config_missing", "config": str(target), "removed": []}
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "success": False,
            "status": "config_invalid",
            "config": str(target),
            "removed": [],
            "detail": str(exc),
        }
    if not isinstance(value, dict) or not isinstance(value.get("mcpServers", {}), dict):
        return {"success": False, "status": "config_invalid", "config": str(target), "removed": []}
    servers = value.setdefault("mcpServers", {})
    removed = [key for key in OWNED_KEYS if key in servers and _owned_server(servers[key])]
    if not removed:
        return {"success": True, "status": "already_clean", "config": str(target), "removed": [], "backup": None}
    if dry_run:
        return {"success": True, "status": "planned", "config": str(target), "removed": removed, "backup": None}
    original = target.read_bytes()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = target.with_name(f"{target.name}.chatmaker-backup-{stamp}")
    counter = 1
    while backup.exists():
        backup = target.with_name(f"{target.name}.chatmaker-backup-{stamp}-{counter}")
        counter += 1
    backup.write_bytes(original)
    for key in removed:
        servers.pop(key, None)
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_write(target, data)
    return {
        "success": True,
        "status": "cleaned",
        "config": str(target),
        "removed": removed,
        "backup": str(backup),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="exact legacy host MCP JSON configuration")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = cleanup(args.config, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""WorkBuddy installation adapter."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .base import HostAdapter, first_available, selected_path


class WorkBuddyHostAdapter(HostAdapter):
    name = "workbuddy"

    def detect(self, report: Mapping[str, Any] | Any) -> dict[str, Any] | None:
        skill_root = first_available(report, "skill_roots", self.name)
        config = first_available(report, "mcp_configs", self.name)
        if skill_root is None and config is None:
            return None
        return {
            "host": self.name,
            "confidence": "high",
            "evidence": "mcp_config" if config is not None else "skill_root",
        }

    def plan(self, context: Mapping[str, Any]) -> dict[str, Any]:
        report = context["report"]
        if self.detect(report) is None:
            return {"host": self.name, "status": "unavailable", "writes": []}
        skill_dir = selected_path(report, "skill_roots", self.name)
        mcp_config = selected_path(report, "mcp_configs", self.name)
        command = str(context.get("python_executable") or sys.executable)
        mcp_server = {
            "type": "stdio",
            "command": command,
            "args": ["-m", "chatmaker.integrations.mcp"],
            "cwd": str(Path(__file__).resolve().parents[3]),
            "env": {"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"},
            "defer_loading": False,
            "disabled": False,
        }
        return {
            "host": self.name,
            "status": "ready",
            "skill_dir": skill_dir,
            "mcp_config": mcp_config,
            "mcp_server": mcp_server,
            "preserves_unrelated_mcp_servers": True,
            "installer": "chatmaker.installers.workbuddy",
            "writes": [
                {"kind": "skill_bundle", "path": skill_dir},
                {"kind": "mcp_server", "path": mcp_config},
            ],
        }

    def verify(self, context: Mapping[str, Any]) -> dict[str, Any]:
        detection = self.detect(context["report"])
        return {"success": detection is not None, "host": self.name, "detection": detection}


__all__ = ["WorkBuddyHostAdapter"]

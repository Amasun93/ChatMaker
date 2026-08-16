"""WorkBuddy installation adapter."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .base import HostAdapter, first_available, selected_path
from .. import workbuddy as workbuddy_installer


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
        writes = []
        if skill_dir:
            writes.append({"kind": "skill_bundle", "path": skill_dir})
        if mcp_config:
            writes.append({"kind": "mcp_server", "path": mcp_config})
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
            "status": "ready" if skill_dir and mcp_config else "ready_with_limits",
            "skill_dir": skill_dir,
            "mcp_config": mcp_config,
            "mcp_server": mcp_server,
            "preserves_unrelated_mcp_servers": True,
            "installer": "chatmaker.installers.workbuddy",
            "writes": writes,
            "limits": [] if skill_dir and mcp_config else ["creatable_host_paths_unavailable"],
        }

    def verify(self, context: Mapping[str, Any]) -> dict[str, Any]:
        plan = context.get("plan")
        if not isinstance(plan, Mapping):
            plan = self.plan(context)
        mcp_config = plan.get("mcp_config")
        if not mcp_config:
            return {
                "success": False,
                "status": "ready_with_limits",
                "host": self.name,
                "reason": "mcp_configuration_unavailable",
            }
        result = workbuddy_installer.doctor(Path(str(mcp_config)))
        return {
            **result,
            "host": self.name,
            "status": "healthy" if result["success"] else "needs_install",
        }


__all__ = ["WorkBuddyHostAdapter"]

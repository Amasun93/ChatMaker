"""Codex installation adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .base import HostAdapter, first_available, selected_path


class CodexHostAdapter(HostAdapter):
    name = "codex"

    def detect(self, report: Mapping[str, Any] | Any) -> dict[str, Any] | None:
        skill_root = first_available(report, "skill_roots", self.name)
        config = first_available(report, "mcp_configs", self.name)
        if skill_root is None and config is None:
            return None
        return {
            "host": self.name,
            "confidence": "high",
            "evidence": "skill_root" if skill_root is not None else "config",
        }

    def plan(self, context: Mapping[str, Any]) -> dict[str, Any]:
        report = context["report"]
        if self.detect(report) is None:
            return {"host": self.name, "status": "unavailable", "writes": []}
        skill_dir = selected_path(report, "skill_roots", self.name)
        writes = [{"kind": "skill_bundle", "path": skill_dir}] if skill_dir else []
        return {
            "host": self.name,
            "status": "ready" if skill_dir else "ready_with_limits",
            "skill_dir": skill_dir,
            "installer": "chatmaker.installers.codex",
            "writes": writes,
            "limits": [] if skill_dir else ["creatable_skill_dir_unavailable"],
        }

    def verify(self, context: Mapping[str, Any]) -> dict[str, Any]:
        detection = self.detect(context["report"])
        return {"success": detection is not None, "host": self.name, "detection": detection}


__all__ = ["CodexHostAdapter"]

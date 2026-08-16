"""Explicit target selection shared by known host adapters."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from .base import HostAdapter, entries, first_explicit
from ..skill_bundle import doctor_bundle
from ..workbuddy import SERVER_KEY


class ExplicitHostAdapter(HostAdapter):
    """Reports user-supplied paths without guessing which host owns them."""

    name = "explicit"

    def detect(self, report: Mapping[str, Any] | Any) -> dict[str, Any] | None:
        skill_root = first_explicit(report, "skill_roots")
        mcp_config = first_explicit(report, "mcp_configs")
        supplied = [
            item
            for key in ("skill_roots", "mcp_configs")
            for item in entries(report, key)
            if item.get("explicit")
        ]
        if skill_root is None and mcp_config is None and not supplied:
            return None
        return {
            "host": self.name,
            "confidence": "explicit" if skill_root or mcp_config else "invalid",
            "skill_dir": skill_root.get("path") if skill_root else None,
            "mcp_config": mcp_config.get("path") if mcp_config else None,
        }

    def plan(self, context: Mapping[str, Any]) -> dict[str, Any]:
        detection = self.detect(context["report"])
        if detection is None:
            return {"host": self.name, "status": "unavailable", "limits": []}
        if detection["confidence"] == "invalid":
            return {
                "host": self.name,
                "status": "ready_with_limits",
                "limits": ["absolute_target_required"],
            }
        return {"host": self.name, "status": "ready", "limits": [], **detection}

    def verify(self, context: Mapping[str, Any]) -> dict[str, Any]:
        plan = context.get("plan")
        if not isinstance(plan, Mapping):
            plan = self.plan(context)
        skill_dir = plan.get("skill_dir")
        mcp_config = plan.get("mcp_config")
        checks: list[bool] = []
        details: dict[str, Any] = {}
        if skill_dir:
            bundle = doctor_bundle(Path(str(skill_dir)).parent)
            checks.append(bool(bundle["success"]))
            details["skills"] = bundle["skills"]
        if mcp_config:
            try:
                config = json.loads(Path(str(mcp_config)).read_text(encoding="utf-8"))
                ready = isinstance(config.get("mcpServers", {}).get(SERVER_KEY), dict)
            except (OSError, json.JSONDecodeError, AttributeError):
                ready = False
            checks.append(ready)
            details["mcp_server_ready"] = ready
        success = bool(checks) and all(checks)
        return {
            "success": success,
            "status": "healthy" if success else "needs_install",
            "host": self.name,
            **details,
        }


__all__ = ["ExplicitHostAdapter"]

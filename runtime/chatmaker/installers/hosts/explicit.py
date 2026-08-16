"""Explicit target selection shared by known host adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .base import HostAdapter, entries, first_explicit


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
        detection = self.detect(context["report"])
        return {"success": detection is not None, "host": self.name, "detection": detection}


__all__ = ["ExplicitHostAdapter"]

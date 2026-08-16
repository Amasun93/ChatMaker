"""Declarative adapters for the supported ChatMaker hosts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .base import HostAdapter
from .codex import CodexHostAdapter
from .explicit import ExplicitHostAdapter
from .workbuddy import WorkBuddyHostAdapter


ADAPTERS: tuple[HostAdapter, ...] = (CodexHostAdapter(), WorkBuddyHostAdapter())


def detect_hosts(report: Mapping[str, Any] | Any) -> list[dict[str, Any]]:
    """Return every real supported host; explicit paths do not invent a host."""
    return [detection for adapter in ADAPTERS if (detection := adapter.detect(report))]


def plan_installation(context: Mapping[str, Any]) -> dict[str, Any]:
    """Build a no-write plan that remains useful when no host is installed."""
    report = context["report"]
    plans = [adapter.plan(context) for adapter in ADAPTERS if adapter.detect(report)]
    if not plans:
        return {
            "status": "ready_with_limits",
            "hosts": [],
            "writes": [],
            "limits": ["no_supported_host_detected"],
        }
    limited = any(plan["status"] == "ready_with_limits" for plan in plans)
    return {
        "status": "ready_with_limits" if limited else "ready",
        "hosts": plans,
        "writes": [write for plan in plans for write in plan["writes"]],
        "limits": [
            limit
            for plan in plans
            for limit in plan.get("limits", [])
        ],
    }


__all__ = [
    "ADAPTERS",
    "HostAdapter",
    "CodexHostAdapter",
    "ExplicitHostAdapter",
    "WorkBuddyHostAdapter",
    "detect_hosts",
    "plan_installation",
]

"""Shared, read-only primitives for host-specific installation plans."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


def capability_value(report: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    """Accept a capability dictionary or the report object produced by probing."""
    if isinstance(report, Mapping):
        return report
    to_dict = getattr(report, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        if isinstance(value, Mapping):
            return value
    raise TypeError("report must be a capability mapping or CapabilityReport")


def entries(report: Mapping[str, Any] | Any, key: str) -> list[dict[str, Any]]:
    value = capability_value(report).get(key, [])
    return [dict(item) for item in value if isinstance(item, Mapping)]


def first_explicit(report: Mapping[str, Any] | Any, key: str) -> dict[str, Any] | None:
    return next((item for item in entries(report, key) if item.get("explicit")), None)


def first_available(report: Mapping[str, Any] | Any, key: str, host: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in entries(report, key)
            if item.get("host") == host and bool(item.get("available"))
        ),
        None,
    )


def selected_path(report: Mapping[str, Any] | Any, key: str, host: str) -> str | None:
    """Prefer an explicitly configured target, then proven host evidence."""
    candidate = first_explicit(report, key) or first_available(report, key, host)
    path = candidate.get("path") if candidate else None
    return str(path) if path else None


class HostAdapter(ABC):
    """A host boundary that converts bounded capability evidence into a plan."""

    name: str

    @abstractmethod
    def detect(self, report: Mapping[str, Any] | Any) -> dict[str, Any] | None:
        """Return high-confidence host evidence, or ``None`` if it is absent."""

    @abstractmethod
    def plan(self, context: Mapping[str, Any]) -> dict[str, Any]:
        """Return a declarative installation plan without changing local state."""

    @abstractmethod
    def verify(self, context: Mapping[str, Any]) -> dict[str, Any]:
        """Return a read-only verification result for a planned host."""


__all__ = [
    "HostAdapter",
    "capability_value",
    "entries",
    "first_available",
    "first_explicit",
    "selected_path",
]

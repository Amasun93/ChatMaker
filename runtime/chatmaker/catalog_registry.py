"""Generated single-source registration for ChatMaker boards and components."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, Mapping


def _load_registry() -> dict[str, Any]:
    raw = files("chatmaker").joinpath("catalog_registry.json").read_text(encoding="utf-8")
    value = json.loads(raw)
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != "1.0"
        or not isinstance(value.get("boards"), dict)
        or not isinstance(value.get("components"), dict)
    ):
        raise RuntimeError("catalog_registry_invalid")
    return value


CATALOG_REGISTRY = _load_registry()
BOARD_REGISTRATIONS: Mapping[str, Mapping[str, Any]] = CATALOG_REGISTRY["boards"]
COMPONENT_REGISTRATIONS: Mapping[str, Mapping[str, Any]] = CATALOG_REGISTRY["components"]

KNOWLEDGE_BOARD_IDS = tuple(
    board_id
    for board_id, registration in BOARD_REGISTRATIONS.items()
    if registration.get("knowledge") is not None
)
KNOWLEDGE_PACK_IDS = {
    board_id: str(BOARD_REGISTRATIONS[board_id]["knowledge"]["pack_id"])
    for board_id in KNOWLEDGE_BOARD_IDS
}
KNOWLEDGE_SOURCE_REFS = {
    board_id: str(BOARD_REGISTRATIONS[board_id]["knowledge"]["source_ref"])
    for board_id in KNOWLEDGE_BOARD_IDS
}
ALLOWED_KNOWLEDGE_PACKS = {
    pack_id: board_id for board_id, pack_id in KNOWLEDGE_PACK_IDS.items()
}


__all__ = [
    "ALLOWED_KNOWLEDGE_PACKS",
    "BOARD_REGISTRATIONS",
    "CATALOG_REGISTRY",
    "COMPONENT_REGISTRATIONS",
    "KNOWLEDGE_BOARD_IDS",
    "KNOWLEDGE_PACK_IDS",
    "KNOWLEDGE_SOURCE_REFS",
]

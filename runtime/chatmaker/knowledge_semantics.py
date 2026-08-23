"""Semantic contract for governed ChatMaker Knowledge indexes, pages, and packs."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import PurePosixPath
from typing import Any, Mapping

import yaml


MAX_BODY_BYTES = 65_536
BOARD_IDS = (
    "arduino-nano-classic",
    "arduino-uno-r3",
    "esp32-devkit-v1",
    "idmc-0001-starcore-v4-2-2",
    "mpython-classic-v2x",
    "mpython-v3",
)
CONSUMERS = ("chatmaker", "chatduino", "chatweb", "chatcad")
SECTION_IDS = (
    "start-here",
    "identify-and-safety",
    "pins-and-electrical",
    "toolchains-and-upload",
    "components-and-wiring",
    "libraries-and-examples",
    "web-and-protocol",
    "troubleshooting",
)
PACK_IDS = {
    board_id: f"chatmaker-board-{board_id}-knowledge" for board_id in BOARD_IDS
}
SOURCE_REFS = {
    "arduino-nano-classic": "source-arduino-nano-classic-documentation",
    "arduino-uno-r3": "source-arduino-uno-r3-documentation",
    "esp32-devkit-v1": "source-esp32-devkit-v1-doit-board-definition",
    "idmc-0001-starcore-v4-2-2": "source-idmc-0001-starcore-v4-2-2-owned-docs",
    "mpython-classic-v2x": "source-mpython-classic-v2x-official",
    "mpython-v3": "source-mpython-v3-official",
}

_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_INDEX_KEYS = {"schema_version", "kind", "board_id", "max_section_bytes", "sections"}
_INDEX_SECTION_KEYS = {
    "section_id",
    "title",
    "summary",
    "consumers",
    "topics",
    "pack_id",
}
_PAGE_KEYS = {
    "schema_version",
    "kind",
    "stable_id",
    "board_id",
    "section_id",
    "source_refs",
}


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key ({key!r})",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


class KnowledgeSemanticError(Exception):
    """A stable semantic-contract failure shared by every trust boundary."""

    def __init__(self, reason: str, *, path: str | None = None) -> None:
        self.reason = reason
        self.path = path
        detail = reason if path is None else f"{reason}: {path}"
        super().__init__(detail)


@dataclass(frozen=True)
class ValidatedPage:
    frontmatter: dict[str, Any]
    body: str
    body_bytes: int


def _yaml_mapping(raw: bytes, *, reason: str, path: str | None = None) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise KnowledgeSemanticError(reason, path=path)
    try:
        value = yaml.load(raw.decode("utf-8"), Loader=_UniqueKeyLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise KnowledgeSemanticError(reason, path=path) from exc
    if not isinstance(value, dict):
        raise KnowledgeSemanticError(reason, path=path)
    return value


def validate_index_bytes(
    raw: bytes,
    *,
    expected_board_id: str | None = None,
    expected_pack_id: str | None = None,
) -> dict[str, Any]:
    """Validate the exact compact index identity and eight-section map."""

    path = "knowledge/index.yaml"
    value = _yaml_mapping(raw, reason="knowledge_index_invalid", path=path)
    if (
        set(value) != _INDEX_KEYS
        or value.get("schema_version") != "1.0"
        or value.get("kind") != "knowledge-index"
        or value.get("max_section_bytes") != MAX_BODY_BYTES
    ):
        raise KnowledgeSemanticError("knowledge_index_invalid", path=path)
    board_id = value.get("board_id")
    if board_id not in BOARD_IDS:
        raise KnowledgeSemanticError("knowledge_index_board_invalid", path=path)
    if expected_board_id is not None and board_id != expected_board_id:
        raise KnowledgeSemanticError("knowledge_index_board_mismatch", path=path)
    mapped_pack_id = PACK_IDS[board_id]
    if expected_pack_id is not None and mapped_pack_id != expected_pack_id:
        raise KnowledgeSemanticError("knowledge_index_pack_mismatch", path=path)

    sections = value.get("sections")
    if not isinstance(sections, list) or len(sections) != len(SECTION_IDS):
        raise KnowledgeSemanticError("knowledge_index_sections_invalid", path=path)
    seen: list[str] = []
    for section in sections:
        if not isinstance(section, dict) or set(section) != _INDEX_SECTION_KEYS:
            raise KnowledgeSemanticError("knowledge_index_section_invalid", path=path)
        section_id = section.get("section_id")
        title = section.get("title")
        summary = section.get("summary")
        consumers = section.get("consumers")
        topics = section.get("topics")
        if (
            section_id not in SECTION_IDS
            or not isinstance(title, str)
            or not 1 <= len(title) <= 120
            or not isinstance(summary, str)
            or not 1 <= len(summary) <= 280
            or not isinstance(consumers, list)
            or not consumers
            or len(consumers) != len(set(consumers))
            or any(consumer not in CONSUMERS for consumer in consumers)
            or not isinstance(topics, list)
            or not topics
            or len(topics) != len(set(topics))
            or any(not isinstance(topic, str) or _SAFE_ID.fullmatch(topic) is None for topic in topics)
            or section.get("pack_id") != mapped_pack_id
            or (expected_pack_id is not None and section.get("pack_id") != expected_pack_id)
        ):
            raise KnowledgeSemanticError("knowledge_index_section_invalid", path=path)
        seen.append(section_id)
    if tuple(seen) != SECTION_IDS:
        raise KnowledgeSemanticError("knowledge_index_sections_invalid", path=path)
    return value


def _split_page(raw: bytes, *, path: str) -> tuple[bytes, bytes]:
    if not isinstance(raw, bytes):
        raise KnowledgeSemanticError("knowledge_page_utf8_invalid", path=path)
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise KnowledgeSemanticError("knowledge_page_utf8_invalid", path=path) from exc
    if b"\r" in raw:
        raise KnowledgeSemanticError("knowledge_page_frontmatter_invalid", path=path)
    if raw.startswith(b"---\n"):
        opening, closing = len(b"---\n"), b"\n---\n"
    else:
        raise KnowledgeSemanticError("knowledge_page_frontmatter_invalid", path=path)
    boundary = raw.find(closing, opening)
    if boundary < 0:
        raise KnowledgeSemanticError("knowledge_page_frontmatter_invalid", path=path)
    return raw[opening:boundary], raw[boundary + len(closing) :]


def validate_page_bytes(
    raw: bytes,
    *,
    expected_board_id: str,
    expected_section_id: str,
    expected_source_refs: tuple[str, ...] | list[str] | None = None,
    path: str | None = None,
) -> ValidatedPage:
    """Validate exact six-field frontmatter and the body-only byte ceiling."""

    page_path = path or f"knowledge/sections/{expected_section_id}.md"
    frontmatter_raw, body_raw = _split_page(raw, path=page_path)
    if not body_raw.strip() or len(body_raw) > MAX_BODY_BYTES:
        raise KnowledgeSemanticError("knowledge_page_body_size_invalid", path=page_path)
    if expected_board_id not in BOARD_IDS or expected_section_id not in SECTION_IDS:
        raise KnowledgeSemanticError("knowledge_page_identity_invalid", path=page_path)
    frontmatter = _yaml_mapping(
        frontmatter_raw,
        reason="knowledge_page_frontmatter_invalid",
        path=page_path,
    )
    source_refs = list(expected_source_refs) if expected_source_refs is not None else [SOURCE_REFS[expected_board_id]]
    expected = {
        "schema_version": "1.0",
        "kind": "knowledge-page",
        "stable_id": f"{expected_board_id}-{expected_section_id}",
        "board_id": expected_board_id,
        "section_id": expected_section_id,
        "source_refs": source_refs,
    }
    if set(frontmatter) != _PAGE_KEYS or frontmatter != expected:
        raise KnowledgeSemanticError("knowledge_page_frontmatter_invalid", path=page_path)
    return ValidatedPage(
        frontmatter=frontmatter,
        body=body_raw.decode("utf-8"),
        body_bytes=len(body_raw),
    )


def validate_pack_payload(
    files: Mapping[str, bytes],
    *,
    expected_board_id: str,
    expected_pack_id: str,
) -> dict[str, Any]:
    """Validate one complete official knowledge pack at any storage boundary."""

    expected_paths = {
        "knowledge/index.yaml",
        *(f"knowledge/sections/{section_id}.md" for section_id in SECTION_IDS),
    }
    if set(files) != expected_paths:
        raise KnowledgeSemanticError("knowledge_page_set_mismatch")
    index = validate_index_bytes(
        files["knowledge/index.yaml"],
        expected_board_id=expected_board_id,
        expected_pack_id=expected_pack_id,
    )
    for section_id in SECTION_IDS:
        page_path = PurePosixPath("knowledge", "sections", f"{section_id}.md").as_posix()
        validate_page_bytes(
            files[page_path],
            expected_board_id=expected_board_id,
            expected_section_id=section_id,
            path=page_path,
        )
    return index


__all__ = [
    "BOARD_IDS",
    "CONSUMERS",
    "KnowledgeSemanticError",
    "MAX_BODY_BYTES",
    "PACK_IDS",
    "SECTION_IDS",
    "SOURCE_REFS",
    "ValidatedPage",
    "validate_index_bytes",
    "validate_pack_payload",
    "validate_page_bytes",
]

"""Progressive, governed access to compact board indexes and one Wiki section."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

import yaml

from .installers.pack_manager import PackManager, PackManagerError
from .resources import ResourceResolver


API_VERSION = "1"
MAX_BODY_BYTES = 65_536
BOARD_IDS = ("arduino-nano-classic", "arduino-uno-r3", "esp32-devkit-v1")
CONSUMERS = ("chatmaker", "chatduino", "chatweb")
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
PACK_IDS = {board_id: f"chatmaker-board-{board_id}-wiki" for board_id in BOARD_IDS}
SOURCE_REFS = {
    "arduino-nano-classic": "source-arduino-nano-classic-documentation",
    "arduino-uno-r3": "source-arduino-uno-r3-documentation",
    "esp32-devkit-v1": "source-esp32-devkit-v1-doit-board-definition",
}
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_INDEX_SECTION_KEYS = {
    "section_id",
    "title",
    "summary",
    "consumers",
    "topics",
    "pack_id",
}


class LLMWikiContentError(Exception):
    pass


def _project_root(project_root: Path | str | None) -> Path:
    if project_root is not None:
        return Path(project_root).resolve()
    return Path(__file__).resolve().parents[2]


def _error(
    code: str,
    message: str,
    *,
    request: Any,
    retryable: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {"success": False, "api_version": API_VERSION}
    if isinstance(request, Mapping):
        for field in ("action", "board_id", "consumer", "section_id"):
            value = request.get(field)
            if isinstance(value, str):
                result[field] = value
    result["error"] = {
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    return result


def _invalid(request: Any, message: str) -> dict[str, Any]:
    return _error("invalid_llmwiki_request", message, request=request)


def _load_index(root: Path, board_id: str) -> dict[str, Any]:
    path = root / "packs" / "llmwiki" / "boards" / f"{board_id}.yaml"
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise LLMWikiContentError("compact index is unreadable") from exc
    expected_keys = {"schema_version", "kind", "board_id", "max_section_bytes", "sections"}
    if (
        not isinstance(value, dict)
        or set(value) != expected_keys
        or value.get("schema_version") != "1.0"
        or value.get("kind") != "llmwiki-index"
        or value.get("board_id") != board_id
        or value.get("max_section_bytes") != MAX_BODY_BYTES
        or not isinstance(value.get("sections"), list)
        or len(value["sections"]) != len(SECTION_IDS)
    ):
        raise LLMWikiContentError("compact index identity is invalid")
    seen: list[str] = []
    expected_pack = PACK_IDS[board_id]
    for section in value["sections"]:
        if not isinstance(section, dict) or set(section) != _INDEX_SECTION_KEYS:
            raise LLMWikiContentError("compact index section metadata is invalid")
        section_id = section.get("section_id")
        consumers = section.get("consumers")
        topics = section.get("topics")
        if (
            section_id not in SECTION_IDS
            or _SAFE_ID.fullmatch(section_id) is None
            or section.get("pack_id") != expected_pack
            or not isinstance(section.get("title"), str)
            or not section["title"]
            or not isinstance(section.get("summary"), str)
            or not section["summary"]
            or not isinstance(consumers, list)
            or not consumers
            or len(consumers) != len(set(consumers))
            or any(consumer not in CONSUMERS for consumer in consumers)
            or not isinstance(topics, list)
            or not topics
            or len(topics) != len(set(topics))
            or any(not isinstance(topic, str) or _SAFE_ID.fullmatch(topic) is None for topic in topics)
        ):
            raise LLMWikiContentError("compact index section mapping is invalid")
        seen.append(section_id)
    if tuple(seen) != SECTION_IDS:
        raise LLMWikiContentError("compact index sections are not exact and unique")
    return value


def _section_resource(section_id: str) -> str:
    if section_id not in SECTION_IDS or _SAFE_ID.fullmatch(section_id) is None:
        raise LLMWikiContentError("unsafe section identity")
    return f"llmwiki/sections/{section_id}.md"


def _parse_page(raw: bytes, *, board_id: str, section_id: str) -> tuple[str, int]:
    if len(raw) > MAX_BODY_BYTES:
        raise LLMWikiContentError("section file exceeds the frozen byte limit")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LLMWikiContentError("section is not valid UTF-8") from exc
    if raw.startswith(b"---\r\n"):
        opening = len(b"---\r\n")
        closing = b"\r\n---\r\n"
    elif raw.startswith(b"---\n"):
        opening = len(b"---\n")
        closing = b"\n---\n"
    else:
        raise LLMWikiContentError("section frontmatter is missing")
    boundary = raw.find(closing, opening)
    if boundary < 0:
        raise LLMWikiContentError("section frontmatter is incomplete")
    try:
        frontmatter = yaml.safe_load(raw[opening:boundary].decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as exc:
        raise LLMWikiContentError("section frontmatter is malformed") from exc
    expected_frontmatter = {
        "schema_version": "1.0",
        "kind": "llmwiki-page",
        "stable_id": f"{board_id}-{section_id}",
        "board_id": board_id,
        "section_id": section_id,
        "source_refs": [SOURCE_REFS[board_id]],
    }
    if frontmatter != expected_frontmatter:
        raise LLMWikiContentError("section identity or source reference is invalid")
    body_bytes = raw[boundary + len(closing) :]
    if not body_bytes or len(body_bytes) > MAX_BODY_BYTES:
        raise LLMWikiContentError("section body size is invalid")
    return body_bytes.decode("utf-8"), len(body_bytes)


def _resolve_optional(resolver: Any, path: str, pack_id: str):
    try:
        return resolver.resolve(path, pack_id=pack_id)
    except FileNotFoundError:
        return None


def _validate_request(request: Any) -> tuple[str, str, str, str | None, bool] | dict[str, Any]:
    if not isinstance(request, dict):
        return _invalid(request, "LLMWiki request must be an object")
    action = request.get("action")
    if not isinstance(action, str):
        return _invalid(request, "action must be a string")
    if action not in {"index", "section"}:
        return _error(
            "unknown_llmwiki_action",
            f"Unknown action: {action}",
            request=request,
        )
    allowed = {"action", "board_id", "consumer"}
    if action == "section":
        allowed.update({"section_id", "auto_install"})
    if set(request) - allowed:
        return _invalid(request, "request contains unsupported fields")
    board_id = request.get("board_id")
    consumer = request.get("consumer")
    if not isinstance(board_id, str) or not isinstance(consumer, str):
        return _invalid(request, "board_id and consumer must be strings")
    if board_id not in BOARD_IDS:
        return _error(
            "llmwiki_board_not_found",
            f"Unknown board_id: {board_id}",
            request=request,
        )
    if consumer not in CONSUMERS:
        return _error(
            "llmwiki_consumer_not_supported",
            f"Unsupported consumer: {consumer}",
            request=request,
        )
    section_id: str | None = None
    auto_install = True
    if action == "section":
        section_id = request.get("section_id")
        if not isinstance(section_id, str):
            return _invalid(request, "section_id must be a string")
        if section_id not in SECTION_IDS:
            return _error(
                "llmwiki_section_not_found",
                f"Unknown section_id: {section_id}",
                request=request,
            )
        auto_install = request.get("auto_install", True)
        if not isinstance(auto_install, bool):
            return _invalid(request, "auto_install must be a boolean")
    return action, board_id, consumer, section_id, auto_install


def execute_request(
    request: Any,
    *,
    manager: Any | None = None,
    resolver: Any | None = None,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    validated = _validate_request(request)
    if isinstance(validated, dict):
        return validated
    action, board_id, consumer, section_id, auto_install = validated
    try:
        index = _load_index(_project_root(project_root), board_id)
        pack_id = PACK_IDS[board_id]
        if resolver is None:
            if manager is None:
                manager = PackManager()
            resolver = ResourceResolver(manager=manager)

        if action == "index":
            sections: list[dict[str, Any]] = []
            for metadata in index["sections"]:
                if consumer not in metadata["consumers"]:
                    continue
                resolved = _resolve_optional(
                    resolver,
                    _section_resource(metadata["section_id"]),
                    pack_id,
                )
                sections.append(
                    {
                        "section_id": metadata["section_id"],
                        "title": metadata["title"],
                        "summary": metadata["summary"],
                        "topics": list(metadata["topics"]),
                        "pack_id": pack_id,
                        "available": resolved is not None,
                        "provenance": (
                            resolved.provenance["kind"]
                            if resolved is not None
                            else "builtin_core"
                        ),
                    }
                )
            return {
                "success": True,
                "api_version": API_VERSION,
                "action": "index",
                "board_id": board_id,
                "consumer": consumer,
                "sections": sections,
            }

        assert section_id is not None
        metadata = next(item for item in index["sections"] if item["section_id"] == section_id)
        if consumer not in metadata["consumers"]:
            return _error(
                "llmwiki_consumer_not_supported",
                f"Consumer {consumer} cannot read section {section_id}",
                request=request,
            )
        resource_path = _section_resource(section_id)
        resolved = _resolve_optional(resolver, resource_path, pack_id)
        if resolved is None:
            if not auto_install:
                return _error(
                    "offline_pack_unavailable",
                    f"Pack is not installed: {pack_id}",
                    request=request,
                )
            if manager is None:
                manager = PackManager()
            manager.ensure(pack_id)
            resolved = _resolve_optional(resolver, resource_path, pack_id)
            if resolved is None:
                return _error(
                    "pack_content_invalid",
                    f"Installed pack is missing section: {section_id}",
                    request=request,
                )
        body, body_bytes = _parse_page(
            resolved.read_bytes(), board_id=board_id, section_id=section_id
        )
        return {
            "success": True,
            "api_version": API_VERSION,
            "action": "section",
            "board_id": board_id,
            "consumer": consumer,
            "section_id": section_id,
            "title": metadata["title"],
            "body": body,
            "body_bytes": body_bytes,
            "max_body_bytes": MAX_BODY_BYTES,
            "complete": True,
            "provenance": dict(resolved.provenance),
        }
    except PackManagerError as exc:
        return _error(
            exc.code,
            str(exc),
            request=request,
            retryable=exc.retryable,
        )
    except LLMWikiContentError as exc:
        return _error("pack_content_invalid", str(exc), request=request)
    except (OSError, RuntimeError, ValueError) as exc:
        return _error(
            "pack_content_invalid",
            f"LLMWiki content read failed: {type(exc).__name__}",
            request=request,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read a governed ChatMaker LLMWiki section.")
    parser.add_argument("--request-json", required=True, help="JSON object or '-' for stdin")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.request_json == "-" else args.request_json
        request = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        result = _invalid({}, f"Request JSON is invalid: {type(exc).__name__}")
    else:
        result = execute_request(request)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["execute_request", "main"]

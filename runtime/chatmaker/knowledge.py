"""Progressive, governed access to compact board indexes and one Knowledge section."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from .installers.pack_manager import PackManager, PackManagerError
from .knowledge_semantics import (
    BOARD_IDS,
    CONSUMERS,
    KnowledgeSemanticError,
    MAX_BODY_BYTES,
    PACK_IDS,
    SECTION_IDS,
    validate_index_bytes,
    validate_page_bytes,
)
from .resources import ResourceIntegrityError, ResourceResolver


API_VERSION = "1"


class KnowledgeContentError(Exception):
    pass


def _project_root(project_root: Path | str | None) -> Path:
    return Path(project_root).resolve() if project_root is not None else Path(__file__).resolve().parents[2]


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
    result["error"] = {"code": code, "message": message, "retryable": retryable}
    return result


def _invalid(request: Any, message: str) -> dict[str, Any]:
    return _error("invalid_knowledge_request", message, request=request)


def _load_index(root: Path, board_id: str) -> dict[str, Any]:
    path = root / "packs" / "knowledge" / "boards" / f"{board_id}.yaml"
    try:
        return validate_index_bytes(
            path.read_bytes(),
            expected_board_id=board_id,
            expected_pack_id=PACK_IDS[board_id],
        )
    except OSError as exc:
        raise KnowledgeContentError("compact index is unreadable") from exc
    except KnowledgeSemanticError as exc:
        raise KnowledgeContentError(str(exc)) from exc


def _section_resource(section_id: str) -> str:
    if section_id not in SECTION_IDS:
        raise KnowledgeContentError("unsafe section identity")
    return f"knowledge/sections/{section_id}.md"


def _parse_page(raw: bytes, *, board_id: str, section_id: str) -> tuple[str, int]:
    try:
        page = validate_page_bytes(
            raw,
            expected_board_id=board_id,
            expected_section_id=section_id,
        )
    except KnowledgeSemanticError as exc:
        if exc.reason == "knowledge_page_body_size_invalid":
            raise KnowledgeContentError("section body size is invalid") from exc
        raise KnowledgeContentError(str(exc)) from exc
    return page.body, page.body_bytes


def _resolve_optional(resolver: Any, path: str, pack_id: str):
    try:
        return resolver.resolve(path, pack_id=pack_id)
    except FileNotFoundError:
        return None


def _validate_request(request: Any) -> tuple[str, str, str, str | None, bool] | dict[str, Any]:
    if not isinstance(request, dict):
        return _invalid(request, "Knowledge request must be an object")
    action = request.get("action")
    if not isinstance(action, str):
        return _invalid(request, "action must be a string")
    if action not in {"index", "section"}:
        return _error("unknown_knowledge_action", f"Unknown action: {action}", request=request)
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
        return _error("knowledge_board_not_found", f"Unknown board_id: {board_id}", request=request)
    if consumer not in CONSUMERS:
        return _error("knowledge_consumer_not_supported", f"Unsupported consumer: {consumer}", request=request)
    section_id: str | None = None
    auto_install = True
    if action == "section":
        section_id = request.get("section_id")
        if not isinstance(section_id, str):
            return _invalid(request, "section_id must be a string")
        if section_id not in SECTION_IDS:
            return _error("knowledge_section_not_found", f"Unknown section_id: {section_id}", request=request)
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
    """Read a compact index or one complete Knowledge page."""

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
                    resolver, _section_resource(metadata["section_id"]), pack_id
                )
                sections.append(
                    {
                        "section_id": metadata["section_id"],
                        "title": metadata["title"],
                        "summary": metadata["summary"],
                        "topics": list(metadata["topics"]),
                        "pack_id": pack_id,
                        "available": resolved is not None,
                        "provenance": resolved.provenance["kind"] if resolved is not None else "builtin_core",
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
                "knowledge_consumer_not_supported",
                f"Consumer {consumer} cannot read section {section_id}",
                request=request,
            )
        resource_path = _section_resource(section_id)
        resolved = _resolve_optional(resolver, resource_path, pack_id)
        if resolved is None:
            if not auto_install:
                return _error("offline_pack_unavailable", f"Pack is not installed: {pack_id}", request=request)
            if manager is None:
                manager = PackManager()
            manager.ensure(pack_id)
            resolved = _resolve_optional(resolver, resource_path, pack_id)
            if resolved is None:
                return _error("pack_content_invalid", f"Installed pack is missing section: {section_id}", request=request)
        try:
            body, body_bytes = _parse_page(resolved.read_bytes(), board_id=board_id, section_id=section_id)
        except ResourceIntegrityError:
            provenance = getattr(resolved, "provenance", {})
            if not isinstance(provenance, Mapping) or provenance.get("kind") != "official_pack":
                raise
            recovery_manager = manager or getattr(resolver, "manager", None)
            version = provenance.get("version")
            if (
                recovery_manager is None
                or not isinstance(version, str)
                or not callable(getattr(recovery_manager, "quarantine_active_drift", None))
            ):
                return _error("pack_drift_detected", f"Official pack drift detected: {pack_id}", request=request)
            recovery_manager.quarantine_active_drift(pack_id, version=version)
            if not auto_install:
                return _error("pack_drift_detected", f"Official pack drift detected: {pack_id}", request=request)
            recovery_manager.ensure(pack_id)
            repaired = _resolve_optional(resolver, resource_path, pack_id)
            if repaired is None:
                return _error("pack_drift_detected", f"Official pack repair did not restore section: {section_id}", request=request)
            try:
                body, body_bytes = _parse_page(repaired.read_bytes(), board_id=board_id, section_id=section_id)
            except ResourceIntegrityError:
                return _error("pack_drift_detected", f"Official pack drift persisted after one repair: {pack_id}", request=request)
            resolved = repaired
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
        return _error(exc.code, str(exc), request=request, retryable=exc.retryable)
    except KnowledgeContentError as exc:
        return _error("pack_content_invalid", str(exc), request=request)
    except (OSError, RuntimeError, ValueError) as exc:
        return _error("pack_content_invalid", f"Knowledge content read failed: {type(exc).__name__}", request=request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read a governed ChatMaker Knowledge section.")
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

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

import yaml

try:
    from .packs import load_record
except ImportError:  # Allow direct execution from a checked-out release folder.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from chatmaker.packs import load_record


CATALOG_FOLDERS = {
    "board": "boards",
    "component": "components",
    "recipe": "recipes",
}
_ID_INDEX_CACHE: dict[Path, tuple[tuple[tuple[str, int, int], ...], dict[str, Path]]] = {}
_TOP_LEVEL_ID_PATTERN = re.compile(r"^id\s*:\s*(?P<value>.*)$")
_SEARCH_FRAGMENT_PATTERN = re.compile(r"[\s,，、。；;：:!?！？/|()（）\[\]{}]+")


def _root(project_root: Path | None = None) -> Path:
    if project_root is not None:
        return Path(project_root).resolve()
    return Path(__file__).resolve().parents[2]


def _records(project_root: Path | None = None) -> list[tuple[Path, dict[str, Any]]]:
    root = _root(project_root)
    records: list[tuple[Path, dict[str, Any]]] = []
    for folder in CATALOG_FOLDERS.values():
        for path in sorted((root / "packs" / folder).glob("*.yaml")):
            records.append((path, load_record(path)))
    return records


def _catalog_paths(project_root: Path | None = None) -> list[Path]:
    root = _root(project_root)
    paths: list[Path] = []
    for folder in CATALOG_FOLDERS.values():
        paths.extend(sorted((root / "packs" / folder).glob("*.yaml")))
    return paths


def _catalog_fingerprint(paths: list[Path], root: Path) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (
            path.relative_to(root).as_posix(),
            path.stat().st_mtime_ns,
            path.stat().st_size,
        )
        for path in paths
    )


def _record_id_from_path(path: Path) -> str | None:
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if not line or line in {"---", "..."}:
                continue
            if line[0] in {" ", "\t", "-"}:
                continue
            match = _TOP_LEVEL_ID_PATTERN.match(line)
            if match is None:
                continue
            raw_value = match.group("value").strip()
            if raw_value in {"", "|", ">"}:
                return None
            try:
                record_id = yaml.safe_load(raw_value)
            except yaml.YAMLError:
                return None
            if isinstance(record_id, str) and record_id:
                return record_id
    return None


def _id_index(project_root: Path | None = None) -> dict[str, Path]:
    root = _root(project_root)
    paths = _catalog_paths(project_root)
    fingerprint = _catalog_fingerprint(paths, root)
    cached = _ID_INDEX_CACHE.get(root)
    if cached is not None and cached[0] == fingerprint:
        return cached[1]

    index: dict[str, Path] = {}
    for path in paths:
        record_id = _record_id_from_path(path)
        if record_id is not None:
            index.setdefault(record_id, path)
    _ID_INDEX_CACHE[root] = (fingerprint, index)
    return index


def _record_path(record_id: str, project_root: Path | None = None) -> Path | None:
    return _id_index(project_root).get(record_id)


def _flatten_search_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_search_values(item))
        return flattened
    if isinstance(value, dict):
        flattened = []
        for item in value.values():
            flattened.extend(_flatten_search_values(item))
        return flattened
    return []


def _knowledge_search_text(
    record: dict[str, Any], project_root: Path | None = None
) -> list[str]:
    if record.get("kind") != "board" or not record.get("id"):
        return []
    path = _root(project_root) / "knowledge" / "boards" / f"{record['id']}.yaml"
    if not path.is_file():
        return []
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        return []
    sections = value.get("sections", [])
    if not isinstance(sections, list):
        return []
    searchable: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        searchable.extend(
            _flatten_search_values(
                {
                    "title": section.get("title"),
                    "summary": section.get("summary"),
                    "topics": section.get("topics", []),
                }
            )
        )
    return searchable


def _search_text(
    record: dict[str, Any], project_root: Path | None = None
) -> list[str]:
    identity = record.get("identity", {})
    if isinstance(identity, dict):
        identity = {
            key: value
            for key, value in identity.items()
            if not key.endswith("_is_not") and "compatibility" not in key
        }
    values: list[Any] = [
        record.get("id"),
        record.get("name"),
        record.get("category"),
        record.get("interface"),
        record.get("summary"),
        record.get("aliases", []),
        record.get("boards", []),
        record.get("supported_boards", []),
        record.get("components", []),
        identity,
        record.get("onboard_hardware", []),
    ]
    flattened: list[str] = []
    for value in values:
        flattened.extend(_flatten_search_values(value))
    flattened.extend(_knowledge_search_text(record, project_root))
    return flattened


def _board_identity_search_text(record: dict[str, Any]) -> list[str]:
    identity = record.get("identity", {})
    if isinstance(identity, dict):
        identity = {
            key: value
            for key, value in identity.items()
            if not key.endswith("_is_not") and "compatibility" not in key
        }
    values = [record.get("id"), record.get("name"), record.get("aliases", []), identity]
    flattened: list[str] = []
    for value in values:
        flattened.extend(_flatten_search_values(value))
    return flattened


def _search_candidates(texts: list[str]) -> list[str]:
    candidates: list[str] = []
    for text in texts:
        normalized = text.casefold().strip()
        if not normalized:
            continue
        candidates.append(normalized)
        candidates.extend(
            fragment
            for fragment in _SEARCH_FRAGMENT_PATTERN.split(normalized)
            if fragment and fragment != normalized
        )
    return candidates


def _score(
    record: dict[str, Any], query: str, project_root: Path | None = None
) -> int:
    if not query:
        return 1
    normalized = query.casefold().strip()
    candidates = _search_candidates(_search_text(record, project_root))
    score = 0
    for candidate in candidates:
        if candidate == normalized:
            score = max(score, 100)
        elif candidate.startswith(normalized):
            score = max(score, 60)
        elif normalized in candidate:
            score = max(score, 30)

    terms = [term for term in normalized.split() if term]
    if len(terms) > 1:
        if record.get("kind") == "board":
            identity_candidates = _search_candidates(_board_identity_search_text(record))
            if not any(
                any(term in candidate or candidate in term for candidate in identity_candidates)
                for term in terms
            ):
                return 0
        if all(any(term in candidate for candidate in candidates) for term in terms):
            score = max(score, 50)
        return score

    embedded = {
        candidate
        for candidate in candidates
        if 2 <= len(candidate) <= 64 and candidate in normalized
    }
    if len(embedded) >= 2:
        score = max(score, min(40, len(embedded) * 12))
    return score


def _summary(record: dict[str, Any]) -> dict[str, Any]:
    verification = record.get("verification", {})
    return {
        "id": record.get("id"),
        "kind": record.get("kind"),
        "name": record.get("name"),
        "aliases": record.get("aliases", []),
        "category": record.get("category"),
        "interface": record.get("interface"),
        "summary": record.get("summary"),
        "verification": {
            name: gate.get("status")
            for name, gate in verification.items()
            if isinstance(gate, dict)
        },
    }


def search_catalog(
    query: str = "",
    *,
    kind: str | None = None,
    limit: int = 20,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if kind is not None and kind not in CATALOG_FOLDERS:
        return {"success": False, "error": "unknown_catalog_kind", "kind": kind}
    bounded_limit = max(1, min(int(limit), 50))
    matches: list[tuple[int, dict[str, Any]]] = []
    for _, record in _records(project_root):
        if kind is not None and record.get("kind") != kind:
            continue
        score = _score(record, query, project_root)
        if score:
            matches.append((score, record))
    matches.sort(key=lambda item: (-item[0], str(item[1].get("id", ""))))
    summaries = [_summary(record) for _, record in matches[:bounded_limit]]
    return {
        "success": True,
        "action": "search",
        "query": query,
        "kind": kind,
        "match_count": len(matches),
        "matches": summaries,
    }


def get_catalog_record(
    record_id: str,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    path = _record_path(record_id, project_root)
    if path is not None:
        record = load_record(path)
        if record.get("id") == record_id:
            root = _root(project_root)
            return {
                "success": True,
                "action": "get",
                "record": record,
                "source_path": path.relative_to(root).as_posix(),
            }
    return {
        "success": False,
        "action": "get",
        "error": "catalog_record_not_found",
        "id": record_id,
    }


def _knowledge_sections(board_id: str, project_root: Path | None = None) -> list[dict[str, Any]]:
    root = _root(project_root)
    path = root / "knowledge" / "boards" / f"{board_id}.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("knowledge index root must be a mapping")
    sections = value.get("sections", [])
    if not isinstance(sections, list):
        raise ValueError("knowledge index sections must be a list")
    return [
        {
            "section_id": item.get("section_id"),
            "title": item.get("title"),
            "summary": item.get("summary"),
            "topics": list(item.get("topics", [])),
            "consumers": list(item.get("consumers", [])),
            "pack_id": item.get("pack_id"),
        }
        for item in sections
        if isinstance(item, dict)
    ]


def open_board(
    board_id: str,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    board = get_catalog_record(board_id, project_root=project_root)
    if not board.get("success") or board.get("record", {}).get("kind") != "board":
        return {
            "success": False,
            "action": "open_board",
            "error": "catalog_board_not_found",
            "board_id": board_id,
        }

    components: list[dict[str, Any]] = []
    recipes: list[dict[str, Any]] = []
    for _, record in _records(project_root):
        kind = record.get("kind")
        if kind == "component" and board_id in record.get("supported_boards", []):
            components.append(_summary(record))
        if kind == "recipe" and board_id in record.get("boards", []):
            recipes.append(_summary(record))

    components.sort(key=lambda item: str(item.get("id", "")))
    recipes.sort(key=lambda item: str(item.get("id", "")))
    return {
        "success": True,
        "action": "open_board",
        "board": board["record"],
        "source_path": board["source_path"],
        "components": components,
        "recipes": recipes,
        "knowledge": {
            "board_id": board_id,
            "sections": _knowledge_sections(board_id, project_root=project_root),
        },
    }


def execute_request(
    request: dict[str, Any],
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    action = request.get("action")
    if action == "search":
        return search_catalog(
            str(request.get("query", "")),
            kind=request.get("kind"),
            limit=int(request.get("limit", 20)),
            project_root=project_root,
        )
    if action == "get":
        return get_catalog_record(str(request.get("id", "")), project_root=project_root)
    if action == "open_board":
        return open_board(str(request.get("board_id", "")), project_root=project_root)
    return {"success": False, "error": "unknown_catalog_action", "action": action}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search and read the ChatMaker learning catalog.")
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request_json)
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        result = execute_request(request)
    except Exception as exc:
        result = {
            "success": False,
            "error": "catalog_request_failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

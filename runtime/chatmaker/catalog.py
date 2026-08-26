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
_MODULE_PROFILE_CACHE: dict[Path, tuple[int, int, dict[str, dict[str, Any]]]] = {}
_TOP_LEVEL_ID_PATTERN = re.compile(r"^id\s*:\s*(?P<value>.*)$")
_SEARCH_FRAGMENT_PATTERN = re.compile(r"[\s,，、。；;：:!?！？/|()（）\[\]{}]+")


def _root(project_root: Path | None = None) -> Path:
    if project_root is not None:
        return Path(project_root).resolve()
    return Path(__file__).resolve().parents[2]


def _module_profiles(project_root: Path | None = None) -> dict[str, dict[str, Any]]:
    path = _root(project_root) / "knowledge" / "hardware" / "self-developed-modules.yaml"
    if not path.is_file():
        return {}
    stat = path.stat()
    cached = _MODULE_PROFILE_CACHE.get(path)
    if cached is not None and cached[:2] == (stat.st_mtime_ns, stat.st_size):
        return cached[2]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("module_count") != 23:
        raise ValueError("self-developed module runtime index is invalid")
    modules = value.get("modules", [])
    if not isinstance(modules, list):
        raise ValueError("self-developed module runtime index modules must be a list")
    profiles = {
        str(item.get("catalog_id")): item
        for item in modules
        if isinstance(item, dict) and item.get("catalog_id")
    }
    if len(profiles) != 23:
        raise ValueError("self-developed module runtime index identities are incomplete")
    _MODULE_PROFILE_CACHE[path] = (stat.st_mtime_ns, stat.st_size, profiles)
    return profiles


def _attach_module_profile(
    record: dict[str, Any], project_root: Path | None = None
) -> dict[str, Any]:
    profile = _module_profiles(project_root).get(str(record.get("id")))
    if profile is None:
        return record
    attached = dict(record)
    attached["module_profile"] = profile
    return attached


def _records(project_root: Path | None = None) -> list[tuple[Path, dict[str, Any]]]:
    root = _root(project_root)
    records: list[tuple[Path, dict[str, Any]]] = []
    for folder in CATALOG_FOLDERS.values():
        for path in sorted((root / "packs" / folder).glob("*.yaml")):
            records.append((path, _attach_module_profile(load_record(path), project_root)))
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
        record.get("module_profile", {}) if record.get("kind") == "component" else {},
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


def _self_developed_records(
    project_root: Path | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    records = []
    for path, record in _records(project_root):
        profile = record.get("module_profile")
        if isinstance(profile, dict) and profile.get("source_ref") == "self-developed-hardware-handoff-2026-07-25":
            records.append((path, record))
    return records


def _module_card(record: dict[str, Any]) -> dict[str, Any]:
    profile = record["module_profile"]
    mechanical = profile.get("mechanical", {})
    return {
        "name": profile.get("display_name") or record.get("name"),
        "purpose": profile.get("purpose"),
        "io_role": profile.get("io_role"),
        "interface": profile.get("interface"),
        "usability": profile.get("usability"),
        "capability_gates": profile.get("capability_gates", {}),
        "historical_use": profile.get("historical_use", {}),
        "evidence_status": profile.get("evidence_status"),
        "mechanical_outline": mechanical.get("outline") if isinstance(mechanical, dict) else None,
        "identity": {
            "hardware_id": profile.get("hardware_id"),
            "catalog_id": record.get("id"),
        },
    }


def list_modules(*, project_root: Path | None = None) -> dict[str, Any]:
    records = [record for _, record in _self_developed_records(project_root)]
    records.sort(key=lambda item: str(item.get("module_profile", {}).get("hardware_id", "")))
    return {
        "success": True,
        "action": "list_modules",
        "module_count": len(records),
        "modules": [_module_card(record) for record in records],
        "status_legend": {
            "guidance_ready": "可直接生成证据约束下的指导；编译、烧录和实物效果仍按各自证据门报告。",
            "conditional": "允许生成项目指导，但版本、协议或电气条件未知的部分保持占位并要求核对。",
            "not_applicable": "该模块不需要控制程序，生成连接、使用和验收指导。",
        },
    }


def _resolve_module(
    identifier: str,
    *,
    project_root: Path | None = None,
) -> tuple[Path, dict[str, Any]] | None:
    normalized = identifier.casefold().strip()
    if not normalized:
        return None
    candidates: list[tuple[int, Path, dict[str, Any]]] = []
    for path, record in _self_developed_records(project_root):
        profile = record["module_profile"]
        identities = {
            str(record.get("id", "")).casefold(),
            str(profile.get("hardware_id", "")).casefold(),
        }
        if normalized in identities:
            return path, record
        score = _score(record, identifier, project_root)
        if score:
            candidates.append((score, path, record))
    candidates.sort(key=lambda item: (-item[0], str(item[2].get("id", ""))))
    if not candidates:
        return None
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        return None
    return candidates[0][1], candidates[0][2]


def _module_recipes(
    record: dict[str, Any], project_root: Path | None = None
) -> list[dict[str, Any]]:
    record_id = record.get("id")
    recipes = []
    for _, candidate in _records(project_root):
        if candidate.get("kind") != "recipe":
            continue
        if record.get("kind") == "board" and record_id in candidate.get("boards", []):
            recipes.append(_summary(candidate))
        elif record.get("kind") == "component" and record_id in candidate.get("components", []):
            recipes.append(_summary(candidate))
    recipes.sort(key=lambda item: str(item.get("id", "")))
    return recipes


def module_guide(
    identifier: str,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    resolved = _resolve_module(identifier, project_root=project_root)
    if resolved is None:
        return {
            "success": False,
            "action": "module_guide",
            "error": "self_developed_module_not_found_or_ambiguous",
            "query": identifier,
        }
    path, record = resolved
    profile = record["module_profile"]
    root = _root(project_root)
    return {
        "success": True,
        "action": "module_guide",
        "module": _module_card(record),
        "guidance": {
            "confirmed_wiring": profile.get("confirmed_wiring", []),
            "power": profile.get("power", {}),
            "unknowns": profile.get("unknowns", []),
            "constraints": record.get("constraints", []),
            "example_capabilities": profile.get("example_capabilities", []),
            "mechanical": profile.get("mechanical", {}),
            "capability_gates": profile.get("capability_gates", {}),
            "historical_use": profile.get("historical_use", {}),
        },
        "recipes": _module_recipes(record, project_root),
        "verification": record.get("verification", {}),
        "source_evidence": profile.get("source_evidence", []),
        "source_path": path.relative_to(root).as_posix(),
    }


def project_task(
    identifier: str,
    *,
    goal: str = "",
    project_root: Path | None = None,
) -> dict[str, Any]:
    guide = module_guide(identifier, project_root=project_root)
    if not guide.get("success"):
        guide["action"] = "project_task"
        return guide
    module = guide["module"]
    guidance = guide["guidance"]
    usability = module["usability"]
    gates = module.get("capability_gates", {})
    programming = gates.get("programming", "conditional")
    wiring = gates.get("wiring", "version_check")
    desired_goal = goal.strip() or str(module["purpose"])
    steps = [
        f"按丝印确认这是 {module['name']}；内部编号只用于匹配底层资料。",
        "断开 USB 和外部电源，先核对供电、接口、引脚标签和共地要求。",
    ]
    if wiring == "ready":
        steps.append("按返回的已确认接线连接；仍要逐一核对模块与主板丝印，并保持共地。")
    elif wiring == "assignment_required":
        steps.append("根据板卡当前占用情况分配空闲兼容引脚；保留资料已确认的接口类型、电压和有效电平。")
    else:
        steps.append("先按丝印或随附版本资料确认供电、接口或模块批次；未确认字段保持为空，不猜测。")
    if programming == "ready":
        steps.extend([
            "优先选择返回的受控配方；只使用其中已确认的接线，未分配引脚仍需结合板卡占用情况选择。",
            "生成完整程序后先编译；烧录、串口现象和实物效果分别验证，不用编译通过代替实物成功。",
        ])
    elif programming == "conditional":
        steps.extend([
            "可以生成完整项目结构和已确认部分；版本相关命令、阈值或有效电平必须保留为待确认参数。",
            "先编译不依赖未知字段的部分；执行器、电机和高于 3.3V 的信号在条件确认前不动作。",
        ])
    else:
        steps.extend([
            "这个模块不需要 Arduino 控制程序；生成供电、连接、机械安装和使用验收步骤。",
            "不要为了让项目看起来完整而虚构 GPIO、串口命令或控制代码。",
        ])
    return {
        "success": True,
        "action": "project_task",
        "title": f"{module['name']}项目任务",
        "goal": desired_goal,
        "module": module,
        "generation_level": usability,
        "capability_gates": gates,
        "steps": steps,
        "confirmed_wiring": guidance.get("confirmed_wiring", []),
        "blocked_facts": guidance.get("unknowns", []),
        "mechanical_guidance": guidance.get("mechanical", {}),
        "candidate_recipes": guide.get("recipes", []),
        "acceptance": {
            "source_or_plan": "generated",
            "code_compiled": "unverified",
            "firmware_uploaded": "unverified",
            "serial_or_runtime_observed": "unverified",
            "physical_effect_verified": "unverified",
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
        record = _attach_module_profile(load_record(path), project_root)
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
    if action == "list_modules":
        return list_modules(project_root=project_root)
    if action == "module_guide":
        return module_guide(str(request.get("module", request.get("id", ""))), project_root=project_root)
    if action == "project_task":
        return project_task(
            str(request.get("module", request.get("id", ""))),
            goal=str(request.get("goal", "")),
            project_root=project_root,
        )
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

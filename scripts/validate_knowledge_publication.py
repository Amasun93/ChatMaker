from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


BOARD_IDS = ("arduino-nano-classic", "arduino-uno-r3", "esp32-devkit-v1")
MAX_SECTION_BYTES = 65_536


def _error_path(error: Any) -> str:
    return ".".join(str(part) for part in error.absolute_path) or "manifest"


def _safe_published_path(path: Any, board_id: str) -> bool:
    if not isinstance(path, str) or not path or "\\" in path or ":" in path:
        return False
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        return False
    expected_prefix = ("published", "boards", board_id)
    return candidate.parts[:3] == expected_prefix and candidate.suffix == ".md" and len(candidate.parts) >= 4


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return None, str(exc)
    if not isinstance(value, dict):
        return None, "YAML root must be a mapping"
    return value, None


def _parse_page(path: Path) -> tuple[dict[str, Any] | None, bytes | None, str | None]:
    try:
        raw = path.read_bytes()
        raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        return None, None, str(exc)
    if raw.startswith(b"---\r\n"):
        opening_length = len(b"---\r\n")
        closing = b"\r\n---\r\n"
    elif raw.startswith(b"---\n"):
        opening_length = len(b"---\n")
        closing = b"\n---\n"
    else:
        return None, None, "missing opening YAML frontmatter delimiter"
    boundary = raw.find(closing, opening_length)
    if boundary < 0:
        return None, None, "missing closing YAML frontmatter delimiter"
    try:
        frontmatter = yaml.safe_load(raw[opening_length:boundary].decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as exc:
        return None, None, str(exc)
    if not isinstance(frontmatter, dict):
        return None, None, "frontmatter must be a mapping"
    return frontmatter, raw[boundary + len(closing) :], None


def _validate_gate(manifest_path: Path, gate_name: str, gate: Any, errors: list[str]) -> None:
    if not isinstance(gate, dict):
        return
    if gate.get("status") == "verified" and (not gate.get("date") or not gate.get("evidence")):
        errors.append(f"{manifest_path}: {gate_name}: verified status requires its own date and evidence")


def validate_knowledge_publication(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    workspace = root / "knowledge_sources"
    manifest_dir = workspace / "manifests"
    schema_path = workspace / "schemas" / "source-manifest.schema.yaml"
    errors: list[str] = []
    manifests: list[tuple[Path, dict[str, Any]]] = []

    schema, schema_error = _load_yaml(schema_path)
    if schema_error is not None or schema is None:
        errors.append(f"{schema_path}: cannot load source-manifest schema: {schema_error}")
        return {"success": False, "errors": errors, "counts": {"manifests": 0, "pages": 0}}
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    for board_id in BOARD_IDS:
        path = manifest_dir / f"{board_id}.yaml"
        if not path.is_file():
            errors.append(f"missing source manifest for board '{board_id}'")

    if manifest_dir.is_dir():
        for path in sorted(manifest_dir.glob("*.yaml")):
            manifest, manifest_error = _load_yaml(path)
            if manifest_error is not None or manifest is None:
                errors.append(f"{path}: cannot load manifest: {manifest_error}")
                continue
            manifests.append((path, manifest))
            if manifest.get("schema_version") != "1.0":
                errors.append(f"{path}: unsupported schema_version {manifest.get('schema_version')!r}")
            for error in sorted(validator.iter_errors(manifest), key=lambda item: list(item.path)):
                errors.append(f"{path}: schema {_error_path(error)}: {error.message}")
            for gate_name in ("cleaning_verified", "source_reviewed", "publication_approved"):
                _validate_gate(path, gate_name, manifest.get(gate_name), errors)

    source_ids: set[str] = set()
    declarations: dict[str, tuple[Path, dict[str, Any], dict[str, Any]]] = {}
    stable_ids: dict[str, Path] = {}
    for manifest_path, manifest in manifests:
        source_id = manifest.get("id")
        if isinstance(source_id, str):
            if source_id in source_ids:
                errors.append(f"duplicate stable_id '{source_id}' in source manifests")
            source_ids.add(source_id)
        board_id = manifest.get("board_id")
        page_declarations = manifest.get("page_declarations")
        if not isinstance(page_declarations, list):
            continue
        for declaration in page_declarations:
            if not isinstance(declaration, dict):
                continue
            page_path = declaration.get("path")
            stable_id = declaration.get("stable_id")
            if not _safe_published_path(page_path, str(board_id)):
                errors.append(f"{manifest_path}: unsafe page path {page_path!r}")
                continue
            publication_gate = manifest.get("publication_approved")
            if not isinstance(publication_gate, dict) or publication_gate.get("status") != "verified":
                errors.append(f"{manifest_path}: publication_approved must be verified before declaring pages")
            if not isinstance(stable_id, str):
                continue
            if stable_id in stable_ids:
                errors.append(f"duplicate stable_id '{stable_id}' in page declarations")
            stable_ids[stable_id] = manifest_path
            if page_path in declarations:
                errors.append(f"duplicate page declaration path '{page_path}'")
            declarations[page_path] = (manifest_path, manifest, declaration)

    pages = sorted((workspace / "published").rglob("*.md")) if (workspace / "published").is_dir() else []
    page_ids: dict[str, Path] = {}
    for page_path in pages:
        relative = page_path.relative_to(workspace).as_posix()
        frontmatter, body, page_error = _parse_page(page_path)
        if page_error is not None:
            errors.append(f"{page_path}: malformed frontmatter: {page_error}")
            continue
        if relative not in declarations:
            errors.append(f"{page_path}: page is not an approved declaration")
        if frontmatter.get("schema_version") != "1.0":
            errors.append(f"{page_path}: unsupported schema_version {frontmatter.get('schema_version')!r}")
        required = {"kind", "stable_id", "board_id", "section_id", "source_refs"}
        missing = sorted(name for name in required if name not in frontmatter)
        if frontmatter.get("kind") != "llmwiki-page" or missing:
            errors.append(f"{page_path}: malformed frontmatter: invalid page identity or missing {missing}")
        declared = declarations.get(relative)
        if declared is not None:
            _, manifest, declaration = declared
            if frontmatter.get("stable_id") != declaration.get("stable_id"):
                errors.append(f"{page_path}: stable_id does not match its approved declaration")
            if frontmatter.get("board_id") != manifest.get("board_id"):
                errors.append(f"{page_path}: board_id does not match its approved source scope")
        page_stable_id = frontmatter.get("stable_id")
        if isinstance(page_stable_id, str):
            prior_page = page_ids.get(page_stable_id)
            if prior_page is not None:
                errors.append(
                    f"duplicate stable_id '{page_stable_id}' in published pages: {prior_page}, {page_path}"
                )
            page_ids[page_stable_id] = page_path
        references = frontmatter.get("source_refs")
        if not isinstance(references, list) or not references:
            errors.append(f"{page_path}: malformed frontmatter: source_refs must be a non-empty list")
        else:
            for source_ref in references:
                if source_ref not in source_ids:
                    errors.append(f"{page_path}: missing source reference '{source_ref}'")
        if body is not None and len(body) > MAX_SECTION_BYTES:
            errors.append(f"{page_path}: UTF-8 page body exceeds frozen 65,536-byte limit")

    for declared_path in sorted(declarations):
        if not (workspace / declared_path).is_file():
            errors.append(f"declared page is missing: {declared_path}")

    return {
        "success": not errors,
        "errors": sorted(errors),
        "counts": {"manifests": len(manifests), "pages": len(pages)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check governed ChatMaker LLMWiki source publication files.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    result = validate_knowledge_publication(args.root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

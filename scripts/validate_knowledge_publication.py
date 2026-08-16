from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import stat
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.knowledge_semantics import (  # noqa: E402
    KnowledgeSemanticError,
    validate_page_bytes,
)


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
    return candidate.parts[:3] == expected_prefix and candidate.suffix == ".md" and len(candidate.parts) == 4


def _is_link_or_reparse(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return True
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))


def _safe_filesystem_path(path: Path, allowed_root: Path) -> bool:
    try:
        relative = path.relative_to(allowed_root)
    except ValueError:
        return False
    if _is_link_or_reparse(allowed_root):
        return False
    current = allowed_root
    for part in relative.parts:
        current /= part
        if _is_link_or_reparse(current):
            return False
    try:
        resolved_path = path.resolve(strict=True)
        resolved_root = allowed_root.resolve(strict=True)
        resolved_path.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError):
        return False
    return True


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

    if not _safe_filesystem_path(schema_path, workspace):
        errors.append(f"{schema_path}: unsafe schema filesystem path")
        return {"success": False, "errors": errors, "counts": {"manifests": 0, "pages": 0}}
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
            if not _safe_filesystem_path(path, workspace):
                errors.append(f"{path}: unsafe manifest filesystem path")
                continue
            manifest, manifest_error = _load_yaml(path)
            if manifest_error is not None or manifest is None:
                errors.append(f"{path}: cannot load manifest: {manifest_error}")
                continue
            manifests.append((path, manifest))
            board_id = manifest.get("board_id")
            if not isinstance(board_id, str) or path.name != f"{board_id}.yaml":
                errors.append(f"{path}: board_id {board_id!r} does not match filename")
            if manifest.get("schema_version") != "1.0":
                errors.append(f"{path}: unsupported schema_version {manifest.get('schema_version')!r}")
            for error in sorted(validator.iter_errors(manifest), key=lambda item: list(item.path)):
                errors.append(f"{path}: schema {_error_path(error)}: {error.message}")
            for gate_name in ("cleaning_verified", "source_reviewed", "publication_approved"):
                _validate_gate(path, gate_name, manifest.get(gate_name), errors)

    source_manifests: dict[str, tuple[Path, dict[str, Any]]] = {}
    declarations: dict[str, tuple[Path, dict[str, Any], dict[str, Any]]] = {}
    stable_ids: dict[str, Path] = {}
    for manifest_path, manifest in manifests:
        source_id = manifest.get("id")
        if isinstance(source_id, str):
            if source_id in source_manifests:
                errors.append(f"duplicate stable_id '{source_id}' in source manifests")
            source_manifests[source_id] = (manifest_path, manifest)
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
        if not _safe_filesystem_path(page_path, workspace):
            errors.append(f"{page_path}: unsafe page filesystem path")
            continue
        relative = page_path.relative_to(workspace).as_posix()
        frontmatter, body, page_error = _parse_page(page_path)
        if page_error is not None:
            errors.append(f"{page_path}: malformed frontmatter: {page_error}")
            continue
        if relative not in declarations:
            errors.append(f"{page_path}: page is not an approved declaration")
        declared = declarations.get(relative)
        expected_board_id = page_path.parent.name
        expected_section_id = page_path.stem
        expected_source_refs = None
        if declared is not None:
            _, declaring_manifest, _ = declared
            source_id = declaring_manifest.get("id")
            if isinstance(source_id, str):
                expected_source_refs = [source_id]
        try:
            validate_page_bytes(
                page_path.read_bytes(),
                expected_board_id=expected_board_id,
                expected_section_id=expected_section_id,
                expected_source_refs=expected_source_refs,
                path=relative,
            )
        except (OSError, KnowledgeSemanticError) as exc:
            reason = exc.reason if isinstance(exc, KnowledgeSemanticError) else "page_read_failed"
            if reason == "knowledge_page_frontmatter_invalid":
                detail = f"malformed frontmatter: Knowledge semantic validation failed: {reason}"
            elif reason == "knowledge_page_body_size_invalid":
                detail = (
                    "Knowledge semantic validation failed: UTF-8 page body exceeds "
                    "frozen 65,536-byte limit or is empty"
                )
            else:
                detail = f"Knowledge semantic validation failed: {reason}"
            errors.append(f"{page_path}: {detail}")
        if isinstance(frontmatter.get("section_id"), str) and frontmatter["section_id"] != page_path.stem:
            errors.append(f"{page_path}: section_id does not match Markdown filename stem")
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
                if not isinstance(source_ref, str) or not source_ref:
                    errors.append(f"{page_path}: malformed frontmatter: source_refs must contain source IDs")
                    continue
                source_owner = source_manifests.get(source_ref)
                if source_owner is None:
                    errors.append(f"{page_path}: missing source reference '{source_ref}'")
                    continue
                if declared is not None:
                    _, declaring_manifest, _ = declared
                    if source_ref != declaring_manifest.get("id"):
                        errors.append(
                            f"{page_path}: source reference '{source_ref}' does not belong to its declaring approved manifest"
                        )
                    elif source_owner[1].get("board_id") != declaring_manifest.get("board_id"):
                        errors.append(
                            f"{page_path}: source reference '{source_ref}' does not match the declaring board scope"
                        )

    for declared_path in sorted(declarations):
        page_path = workspace / declared_path
        if page_path.is_file() and not _safe_filesystem_path(page_path, workspace):
            errors.append(f"{page_path}: unsafe page filesystem path")
        elif not page_path.is_file():
            errors.append(f"declared page is missing: {declared_path}")

    return {
        "success": not errors,
        "errors": sorted(errors),
        "counts": {"manifests": len(manifests), "pages": len(pages)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check governed ChatMaker Knowledge source publication files.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        result = validate_knowledge_publication(args.root)
    except Exception as exc:  # Preserve the check-only JSON contract for malformed inputs.
        result = {
            "success": False,
            "errors": [f"validation_failed: {type(exc).__name__}: {exc}"],
            "counts": {"manifests": 0, "pages": 0},
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

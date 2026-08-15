from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


KINDS = ("board", "component", "recipe")
GATES = (
    "source_reviewed",
    "code_compiled",
    "firmware_uploaded",
    "physical_effect_verified",
)
_RECORD_CACHE: dict[Path, tuple[int, int, dict[str, Any]]] = {}


@dataclass(frozen=True)
class ValidationReport:
    errors: list[str]
    counts: dict[str, int]

    @property
    def ok(self) -> bool:
        return not self.errors


def load_record(path: Path) -> dict[str, Any]:
    resolved = Path(path).resolve()
    stat = resolved.stat()
    cached = _RECORD_CACHE.get(resolved)
    if cached is not None and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
        return deepcopy(cached[2])

    value = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("record root must be a mapping")
    _RECORD_CACHE[resolved] = (stat.st_mtime_ns, stat.st_size, value)
    return deepcopy(value)


def _format_path(parts: Any) -> str:
    return ".".join(str(part) for part in parts) or "record"


def validate_record(record: dict[str, Any], schema_dir: Path) -> list[str]:
    kind = record.get("kind")
    if kind not in KINDS:
        return [f"record: unknown kind {kind!r}"]

    schema_path = schema_dir / f"{kind}.schema.yaml"
    try:
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"{kind}: cannot load schema: {exc}"]

    errors = [
        f"{_format_path(error.absolute_path)}: {error.message}"
        for error in sorted(Draft202012Validator(schema).iter_errors(record), key=lambda item: list(item.path))
    ]

    verification = record.get("verification")
    if isinstance(verification, dict):
        for gate_name, gate in verification.items():
            if not isinstance(gate, dict):
                errors.append(f"verification.{gate_name}: gate must be an object")
                continue
            if gate.get("status") == "verified" and (not gate.get("checked_at") or not gate.get("evidence")):
                errors.append(
                    f"verification.{gate_name}.evidence: verified status requires checked_at and evidence"
                )
    return errors


def _record_paths(pack_root: Path) -> list[Path]:
    paths: list[Path] = []
    for folder in ("boards", "components", "recipes"):
        paths.extend(sorted((pack_root / folder).glob("*.yaml")))
    return paths


def validate_repository(pack_root: Path, schema_dir: Path) -> ValidationReport:
    errors: list[str] = []
    counts = {kind: 0 for kind in KINDS}
    records: list[tuple[Path, dict[str, Any]]] = []

    for path in _record_paths(pack_root):
        try:
            record = load_record(path)
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{path}: cannot load record: {exc}")
            continue
        records.append((path, record))
        kind = record.get("kind")
        if kind in counts:
            counts[kind] += 1
        for error in validate_record(record, schema_dir):
            errors.append(f"{path}: {error}")

    by_id: dict[str, list[Path]] = {}
    by_kind: dict[str, set[str]] = {kind: set() for kind in KINDS}
    records_by_id: dict[str, dict[str, Any]] = {}
    for path, record in records:
        record_id = record.get("id")
        kind = record.get("kind")
        if isinstance(record_id, str):
            by_id.setdefault(record_id, []).append(path)
            records_by_id.setdefault(record_id, record)
            if kind in by_kind:
                by_kind[kind].add(record_id)

    for record_id, paths in sorted(by_id.items()):
        if len(paths) > 1:
            errors.append(f"duplicate id '{record_id}': {', '.join(str(path) for path in paths)}")

    project_root = pack_root.parent if pack_root.name == "packs" else pack_root
    for path, record in records:
        if record.get("kind") == "component":
            for board_id in record.get("supported_boards", []):
                if board_id not in by_kind["board"]:
                    errors.append(f"{path}: unknown board '{board_id}'")
            for example_file in record.get("example_files", []):
                if isinstance(example_file, str) and not (project_root / example_file).is_file():
                    errors.append(f"{path}: example_file '{example_file}' does not exist")
        if record.get("kind") != "recipe":
            continue
        for board_id in record.get("boards", []):
            if board_id not in by_kind["board"]:
                errors.append(f"{path}: unknown board '{board_id}'")
        for component_id in record.get("components", []):
            if component_id not in by_kind["component"]:
                errors.append(f"{path}: unknown component '{component_id}'")

        source_file = record.get("source_file")
        if isinstance(source_file, str) and not (project_root / source_file).is_file():
            errors.append(f"{path}: source_file '{source_file}' does not exist")

        assignments: dict[str, list[dict[str, Any]]] = {}
        for wire in record.get("wiring", []):
            component_id = wire.get("component")
            if component_id not in by_kind["component"]:
                errors.append(f"{path}: wiring references unknown component '{component_id}'")
            else:
                component_record = records_by_id[component_id]
                component_pins = {pin.get("id") for pin in component_record.get("pins", [])}
                component_pin = wire.get("component_pin")
                if component_pin not in component_pins:
                    errors.append(
                        f"{path}: component '{component_id}' has no component pin '{component_pin}'"
                    )
            board_pin = wire.get("board_pin")
            if isinstance(board_pin, str):
                assignments.setdefault(board_pin, []).append(wire)
                for board_id in record.get("boards", []):
                    if board_id not in by_kind["board"]:
                        continue
                    board_record = records_by_id[board_id]
                    board_pins = {pin.get("id") for pin in board_record.get("pins", [])}
                    if board_pin not in board_pins:
                        errors.append(f"{path}: board '{board_id}' has no board pin '{board_pin}'")
        for board_pin, wires in assignments.items():
            if len(wires) > 1 and not all(wire.get("shared", False) for wire in wires):
                errors.append(f"{path}: board pin '{board_pin}' has a wiring conflict")

    return ValidationReport(errors=errors, counts=counts)

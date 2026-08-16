from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:  # Allow direct execution from a checked-out release folder.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from chatmaker.packs import canonical_verification_snapshot, validate_repository
    from chatmaker.skills import validate_skill_directory
else:
    from .packs import canonical_verification_snapshot, validate_repository
    from .skills import validate_skill_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the local ChatMaker project.")
    parser.add_argument("--packs", action="store_true", help="Validate board, component, and recipe packs.")
    parser.add_argument("--skills", action="store_true", help="Validate checked-in Skill folders.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    run_packs = args.packs or not (args.packs or args.skills)
    run_skills = args.skills or not (args.packs or args.skills)
    payload: dict[str, object] = {}
    errors: list[str] = []

    if run_packs:
        report = validate_repository(root / "packs", root / "packs" / "schemas")
        snapshot, digest = canonical_verification_snapshot(root / "packs")
        payload["packs"] = {
            "ok": report.ok,
            "counts": report.counts,
            "errors": report.errors,
            "knowledge_indexes": len(list((root / "knowledge" / "boards").glob("*.yaml"))),
            "verification_snapshot_count": len(snapshot),
            "verification_snapshot_sha256": digest,
        }
        errors.extend(report.errors)
    if run_skills:
        skill_results: dict[str, list[str]] = {}
        for skill_dir in sorted(path for path in (root / "skills").iterdir() if path.is_dir()):
            skill_results[skill_dir.name] = validate_skill_directory(skill_dir)
            errors.extend(skill_results[skill_dir.name])
        payload["skills"] = {"ok": not any(skill_results.values()), "results": skill_results}

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path
from typing import Any

from .transaction import InstallTransaction, canonical_install_path


SKILL_NAMES = ("chatmaker",)
INTERNAL_SKILL_NAMES = ("chatduino", "chatweb", "chatcad")


def _bundle_transaction(
    manifest_name: str,
    host_home: Path,
    transaction_root: Path | None,
) -> InstallTransaction:
    return InstallTransaction(
        root=transaction_root,
        installation_id=f"skill-bundle:{manifest_name}:{host_home}",
    )


def install_bundle(
    host_home: Path,
    source_skills: Path,
    manifest_name: str,
    transaction_root: Path | None = None,
) -> dict[str, Any]:
    host_home = canonical_install_path(host_home)
    source_skills = canonical_install_path(source_skills)
    result = _bundle_transaction(manifest_name, host_home, transaction_root).apply(
        [
            {
                "kind": "skill_bundle",
                "source": source_skills,
                "path": host_home / "skills",
                "names": list(SKILL_NAMES),
                "internal_names": list(INTERNAL_SKILL_NAMES),
                "retire_names": list(INTERNAL_SKILL_NAMES),
            }
        ]
    )
    value = result.to_dict()
    value.update(
        {
            "host_home": str(host_home),
            "installed_skills": list(SKILL_NAMES),
            "internal_skills": list(INTERNAL_SKILL_NAMES),
            "backed_up_skills": [
                str(entry["name"])
                for entry in result.details.get("entries", [])
                if entry.get("backup")
            ],
        }
    )
    return value


def uninstall_bundle(
    host_home: Path,
    manifest_name: str,
    transaction_root: Path | None = None,
) -> dict[str, Any]:
    host_home = canonical_install_path(host_home)
    return _bundle_transaction(
        manifest_name,
        host_home,
        transaction_root,
    ).uninstall().to_dict()


def doctor_bundle(host_home: Path) -> dict[str, Any]:
    host_home = canonical_install_path(host_home)
    skills = {
        name: {
            "path": str(host_home / "skills" / name),
            "ready": (host_home / "skills" / name / "SKILL.md").is_file(),
        }
        for name in SKILL_NAMES
    }
    internal_skills = {
        name: {
            "path": str(host_home / "skills" / "chatmaker" / "internal_skills" / name),
            "ready": (
                host_home
                / "skills"
                / "chatmaker"
                / "internal_skills"
                / name
                / "SKILL.md"
            ).is_file(),
        }
        for name in INTERNAL_SKILL_NAMES
    }
    return {
        "success": all(item["ready"] for item in (*skills.values(), *internal_skills.values())),
        "host_home": str(host_home),
        "skills": skills,
        "internal_skills": internal_skills,
    }

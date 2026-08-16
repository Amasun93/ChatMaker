from __future__ import annotations

from pathlib import Path
from typing import Any

from .transaction import InstallTransaction


SKILL_NAMES = ("chatmaker", "chatduino", "chatweb")


def _bundle_transaction(host_home: Path, manifest_name: str) -> InstallTransaction:
    return InstallTransaction(
        root=host_home / ".chatmaker",
        installation_id=f"skill-bundle:{manifest_name}",
    )


def install_bundle(
    host_home: Path,
    source_skills: Path,
    manifest_name: str,
) -> dict[str, Any]:
    host_home = Path(host_home).expanduser().absolute()
    source_skills = Path(source_skills).expanduser().absolute()
    result = _bundle_transaction(host_home, manifest_name).apply(
        [
            {
                "kind": "skill_bundle",
                "source": source_skills,
                "path": host_home / "skills",
                "names": list(SKILL_NAMES),
            }
        ]
    )
    value = result.to_dict()
    value.update(
        {
            "host_home": str(host_home),
            "installed_skills": list(SKILL_NAMES),
            "backed_up_skills": [
                str(entry["name"])
                for entry in result.details.get("entries", [])
                if entry.get("backup")
            ],
        }
    )
    return value


def uninstall_bundle(host_home: Path, manifest_name: str) -> dict[str, Any]:
    host_home = Path(host_home).expanduser().absolute()
    return _bundle_transaction(host_home, manifest_name).uninstall().to_dict()


def doctor_bundle(host_home: Path) -> dict[str, Any]:
    host_home = Path(host_home).expanduser().resolve()
    skills = {
        name: {
            "path": str(host_home / "skills" / name),
            "ready": (host_home / "skills" / name / "SKILL.md").is_file(),
        }
        for name in SKILL_NAMES
    }
    return {
        "success": all(item["ready"] for item in skills.values()),
        "host_home": str(host_home),
        "skills": skills,
    }

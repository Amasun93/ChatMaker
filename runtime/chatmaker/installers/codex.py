from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .skill_bundle import doctor_bundle, install_bundle, uninstall_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_NAME = "chatmaker-codex-install.json"
CONTENT_MANAGER = "chatmaker-pack"


def _with_content_boundary(result: dict[str, Any]) -> dict[str, Any]:
    result["content_manager"] = CONTENT_MANAGER
    result["knowledge_packs_installed"] = []
    return result


def default_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def install(
    codex_home: Path,
    source_skills: Path = PROJECT_ROOT / "skills",
    transaction_root: Path | None = None,
) -> dict[str, Any]:
    result = _with_content_boundary(
        install_bundle(
            codex_home,
            source_skills,
            MANIFEST_NAME,
            transaction_root=transaction_root,
        )
    )
    result["restart_codex"] = True
    return result


def uninstall(codex_home: Path, transaction_root: Path | None = None) -> dict[str, Any]:
    result = uninstall_bundle(
        codex_home,
        MANIFEST_NAME,
        transaction_root=transaction_root,
    )
    result["restart_codex"] = True
    return result


def doctor(codex_home: Path) -> dict[str, Any]:
    return _with_content_boundary(doctor_bundle(codex_home))


def main() -> int:
    parser = argparse.ArgumentParser(description="Install, inspect, or uninstall ChatMaker for Codex.")
    parser.add_argument("action", choices=("install", "doctor", "uninstall"))
    parser.add_argument("--home", type=Path, default=default_codex_home())
    args = parser.parse_args()
    try:
        if args.action == "install":
            result = install(args.home)
        elif args.action == "uninstall":
            result = uninstall(args.home)
        else:
            result = doctor(args.home)
    except Exception as exc:
        result = {
            "success": False,
            "error": "codex_install_operation_failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

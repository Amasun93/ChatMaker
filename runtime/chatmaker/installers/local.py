"""Read-only local capability check for ChatMaker's optional CLI layer."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .capabilities import probe_environment


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def _next_actions(environment: Mapping[str, Any]) -> list[str]:
    actions: list[str] = []
    if not bool(environment.get("mindplus", {}).get("available")):
        actions.append(
            "For Nano, Uno, or Starcore compile/upload, reuse an existing usable Mind+ 1.8.x or 2.x installation; when neither exists, install the verified Mind+ 1.8.x release."
        )
    ports = environment.get("serial", {}).get("ports", [])
    if not any(
        isinstance(port, Mapping) and port.get("eligible_for_upload")
        for port in ports
    ):
        actions.append(
            "Connect a supported wired board only when upload or serial evidence is needed."
        )
    return actions


def run(
    argv: Sequence[str] | None = None,
    *,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Inspect local tools without discovering or modifying any AI host."""
    parser = _parser()
    args = parser.parse_args(argv)
    selected_home = Path(args.home).expanduser() if args.home else home
    environment = probe_environment(
        home=selected_home,
        environ=dict(os.environ if environ is None else environ),
    ).to_dict()
    next_actions = _next_actions(environment)
    return {
        "success": True,
        "status": "local_ready" if not next_actions else "local_ready_with_limits",
        "mode": "local",
        "environment": environment,
        "next_actions": next_actions,
        "host_scan_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        description="Inspect ChatMaker local generation, hardware, and rendering capabilities."
    )
    parser.add_argument("action", choices=("local", "doctor"))
    parser.add_argument("--home", type=Path, help="advanced: profile directory used for local tool discovery")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    try:
        value = run(argv, environ=environ)
    except Exception as exc:
        value = {
            "success": False,
            "status": "failed",
            "mode": "local",
            "environment": {},
            "next_actions": [],
            "host_scan_performed": False,
            "error": type(exc).__name__,
            "detail": str(exc),
        }
    print(json.dumps(value, ensure_ascii=False))
    return 0 if value["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

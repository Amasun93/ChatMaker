"""Structured command-line interface for user-owned ChatMaker knowledge packs."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, TextIO

from .installers.pack_manager import PackManager, PackManagerError


class _StructuredArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PackManagerError(
            "pack_activation_failed",
            reason="invalid_cli_request",
            message=f"pack_activation_failed: invalid_cli_request: {message}",
        )


def _parser() -> argparse.ArgumentParser:
    parser = _StructuredArgumentParser(
        description="Manage signed ChatMaker knowledge packs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("pack_id", nargs="?")

    subparsers.add_parser("list")
    subparsers.add_parser("cache")

    ensure = subparsers.add_parser("ensure")
    ensure.add_argument("pack_id")
    ensure.add_argument("--version")
    ensure.add_argument("--offline", action="store_true")

    update = subparsers.add_parser("update")
    update.add_argument("pack_id")

    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("pack_id")
    rollback.add_argument("--version")
    return parser


def _failure(action: str, error: PackManagerError) -> dict[str, Any]:
    return {
        "success": False,
        "action": action,
        "error": error.to_dict(),
    }


def execute(
    argv: list[str] | None = None,
    *,
    manager: PackManager | None = None,
    output: TextIO | None = None,
) -> int:
    stream = output or sys.stdout
    action = argv[0] if argv else "unknown"
    try:
        args = _parser().parse_args(argv)
        action = args.command
        pack_manager = manager or PackManager()
        if args.command == "status":
            result = pack_manager.status(args.pack_id)
        elif args.command == "list":
            result = pack_manager.list()
        elif args.command == "cache":
            result = pack_manager.inspect_cache()
        elif args.command == "ensure":
            result = pack_manager.ensure(
                args.pack_id,
                version=args.version,
                offline=args.offline,
            )
        elif args.command == "update":
            result = pack_manager.update(args.pack_id)
        elif args.command == "rollback":
            result = pack_manager.rollback(args.pack_id, version=args.version)
        else:  # argparse makes this unreachable, but keep the envelope total.
            raise PackManagerError(
                "pack_activation_failed", reason="unknown_pack_command"
            )
    except PackManagerError as exc:
        result = _failure(action, exc)
    except Exception as exc:
        result = _failure(
            action,
            PackManagerError(
                "pack_activation_failed",
                reason="unexpected_cli_failure",
            ),
        )
    print(json.dumps(result, ensure_ascii=True, sort_keys=True), file=stream)
    return 0 if result.get("success") else 1


def main(argv: list[str] | None = None) -> int:
    return execute(argv)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["execute", "main"]

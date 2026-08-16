"""Capability-driven orchestration for the one public ChatMaker installer."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .capabilities import probe_environment
from .hosts import ADAPTERS, ExplicitHostAdapter, WorkBuddyHostAdapter, plan_installation
from .skill_bundle import SKILL_NAMES
from .transaction import InstallTransaction, TransactionResult
from . import workbuddy


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_SKILLS = PROJECT_ROOT / "skills"
INSTALLATION_ID = "universal-auto"


class _JsonArgumentParser(argparse.ArgumentParser):
    """Keep CLI validation failures in the installer's JSON protocol."""

    def error(self, message: str) -> None:
        raise ValueError(message)


def _result(
    *,
    success: bool,
    status: str,
    environment: Mapping[str, Any],
    hosts: Sequence[Mapping[str, Any]],
    changes: Sequence[str] = (),
    unchanged: Sequence[str] = (),
    next_actions: Sequence[str] = (),
    transaction_id: str | None = None,
    **details: Any,
) -> dict[str, Any]:
    return {
        "success": success,
        "status": status,
        "environment": dict(environment),
        "hosts": [dict(host) for host in hosts],
        "changes": list(changes),
        "unchanged": list(unchanged),
        "next_actions": list(next_actions),
        "transaction_id": transaction_id,
        **details,
    }


def _next_actions(environment: Mapping[str, Any], plan: Mapping[str, Any]) -> list[str]:
    actions: list[str] = []
    if not plan.get("hosts"):
        actions.append("Open a supported host once, then run chatmaker-install auto again.")
    if not bool(environment.get("mindplus", {}).get("available")):
        actions.append("To compile or upload Nano and Uno projects, install Mind+ and run its doctor command.")
    ports = environment.get("serial", {}).get("ports", [])
    if not any(isinstance(port, Mapping) and port.get("eligible_for_upload") for port in ports):
        actions.append("Connect a supported wired board before attempting upload or serial monitoring.")
    if any(plan_host.get("host") in {"codex", "workbuddy"} for plan_host in plan.get("hosts", [])):
        actions.append("Restart the detected host application to load newly installed Skills or MCP services.")
    return actions


def _changes(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for host in plan.get("hosts", []):
        skill_dir = host.get("skill_dir")
        if skill_dir:
            changes.append(
                {
                    "kind": "skill_bundle",
                    "source": SOURCE_SKILLS,
                    "path": Path(str(skill_dir)),
                    "names": list(SKILL_NAMES),
                }
            )
        mcp_config = host.get("mcp_config")
        mcp_server = host.get("mcp_server")
        if mcp_config and isinstance(mcp_server, Mapping):
            changes.append(
                {
                    "kind": "mcp_server",
                    "path": Path(str(mcp_config)),
                    "server_key": workbuddy.SERVER_KEY,
                    "server": dict(mcp_server),
                }
            )
    return changes


def _explicit_plan(environment: Mapping[str, Any], python_executable: str) -> dict[str, Any]:
    """Use explicit paths as one generic destination, never as guessed hosts."""
    explicit = ExplicitHostAdapter().plan({"report": environment})
    if explicit["status"] != "ready":
        return {
            "status": "ready_with_limits",
            "hosts": [explicit],
            "writes": [],
            "limits": list(explicit.get("limits", [])),
        }
    skill_dir = explicit.get("skill_dir")
    mcp_config = explicit.get("mcp_config")
    template_report = {
        "skill_roots": [
            {"host": "workbuddy", "path": skill_dir or str(Path(str(mcp_config)).parent / "skills"), "available": True, "explicit": False}
        ],
        "mcp_configs": [
            {"host": "workbuddy", "path": mcp_config or str(Path(str(skill_dir)).parent / "mcp.json"), "available": True, "explicit": False}
        ],
    }
    template = WorkBuddyHostAdapter().plan(
        {"report": template_report, "python_executable": python_executable}
    )
    host = {
        "host": "explicit",
        "status": "ready",
        "skill_dir": skill_dir,
        "mcp_config": mcp_config,
        "mcp_server": template["mcp_server"],
        "preserves_unrelated_mcp_servers": True,
        "writes": [
            *([{"kind": "skill_bundle", "path": skill_dir}] if skill_dir else []),
            *([{"kind": "mcp_server", "path": mcp_config}] if mcp_config else []),
        ],
        "limits": [],
    }
    return {"status": "ready", "hosts": [host], "writes": host["writes"], "limits": []}


def _transaction(root: Path | None) -> InstallTransaction:
    return InstallTransaction(root=root, installation_id=INSTALLATION_ID)


def _transaction_result(
    result: TransactionResult,
    *,
    environment: Mapping[str, Any],
    hosts: Sequence[Mapping[str, Any]],
    next_actions: Sequence[str],
) -> dict[str, Any]:
    return _result(
        success=result.success,
        status=result.status,
        environment=environment,
        hosts=hosts,
        changes=result.changes,
        unchanged=result.unchanged,
        next_actions=next_actions,
        transaction_id=result.transaction_id,
        conflicts=[dict(item) for item in result.conflicts],
    )


def _doctor_hosts(
    plan: Mapping[str, Any], context: Mapping[str, Any]
) -> list[dict[str, Any]]:
    checked: list[dict[str, Any]] = []
    adapters = {adapter.name: adapter for adapter in ADAPTERS}
    for host in plan.get("hosts", []):
        item = dict(host)
        adapter = (
            ExplicitHostAdapter()
            if item.get("host") == "explicit"
            else adapters.get(item.get("host"))
        )
        check = (
            adapter.verify({**context, "plan": item})
            if adapter is not None
            else {"success": False, "status": "ready_with_limits"}
        )
        item.update(check)
        checked.append(item)
    return checked


def run(
    argv: Sequence[str] | None = None,
    *,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
    transaction_root: Path | None = None,
) -> dict[str, Any]:
    """Run an installer action and return its stable JSON-compatible result."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.action == "restore" and not args.transaction_id:
        raise ValueError("restore requires the transaction_id returned by auto")
    if args.action != "restore" and args.transaction_id:
        raise ValueError("only restore accepts a transaction_id")
    if args.dry_run and args.action != "auto":
        raise ValueError("--dry-run is only valid with auto")
    environment_values = dict(os.environ if environ is None else environ)
    if args.skill_root:
        environment_values["CHATMAKER_SKILL_ROOT"] = str(args.skill_root)
    if args.mcp_config:
        environment_values["CHATMAKER_MCP_CONFIG"] = str(args.mcp_config)
    selected_home = Path(args.home).expanduser() if args.home else home
    selected_root = Path(args.state_root).expanduser() if args.state_root else transaction_root
    environment = probe_environment(home=selected_home, environ=environment_values).to_dict()
    context = {"report": environment, "python_executable": environment["python"]["executable"]}
    plan = _explicit_plan(environment, environment["python"]["executable"]) if (args.skill_root or args.mcp_config) else plan_installation(context)
    next_actions = _next_actions(environment, plan)

    if args.action == "doctor":
        hosts = _doctor_hosts(plan, context)
        ready = bool(hosts) and all(bool(host.get("success")) for host in hosts)
        return _result(
            success=ready or not hosts,
            status="healthy" if ready else "ready_with_limits" if not hosts else "needs_install",
            environment=environment,
            hosts=hosts,
            next_actions=next_actions,
        )

    if args.action == "restore":
        result = _transaction(selected_root).restore(args.transaction_id)
        return _transaction_result(
            result,
            environment=environment,
            hosts=plan.get("hosts", []),
            next_actions=next_actions,
        )

    if args.action == "uninstall":
        result = _transaction(selected_root).uninstall()
        return _transaction_result(
            result,
            environment=environment,
            hosts=plan.get("hosts", []),
            next_actions=next_actions,
        )

    changes = _changes(plan)
    if args.dry_run:
        return _result(
            success=True,
            status="planned",
            environment=environment,
            hosts=plan.get("hosts", []),
            changes=[str(change["path"]) for change in changes],
            next_actions=next_actions,
        )
    if not changes:
        return _result(
            success=True,
            status="ready_with_limits",
            environment=environment,
            hosts=plan.get("hosts", []),
            next_actions=next_actions,
        )
    result = _transaction(selected_root).apply(changes)
    return _transaction_result(
        result,
        environment=environment,
        hosts=plan.get("hosts", []),
        next_actions=next_actions,
    )


def _parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        description="Install, inspect, restore, or remove ChatMaker for detected hosts."
    )
    parser.add_argument("action", choices=("auto", "doctor", "restore", "uninstall"))
    parser.add_argument("transaction_id", nargs="?", help="transaction ID required by restore")
    parser.add_argument("--dry-run", action="store_true", help="show auto changes without writing files")
    parser.add_argument("--home", type=Path, help="advanced: home directory to inspect")
    parser.add_argument("--state-root", type=Path, help="advanced: transaction state root")
    parser.add_argument("--skill-root", type=Path, help="advanced: explicit Skill directory")
    parser.add_argument("--mcp-config", type=Path, help="advanced: explicit MCP configuration")
    return parser


def main(argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    try:
        value = run(argv, environ=environ)
    except Exception as exc:
        value = _result(
            success=False,
            status="failed",
            environment={},
            hosts=[],
            next_actions=[],
            error=type(exc).__name__,
            detail=str(exc),
        )
    print(json.dumps(value, ensure_ascii=False))
    return 0 if value["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

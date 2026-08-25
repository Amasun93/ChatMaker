#!/usr/bin/env python3
"""Reproduce the Starcore local path without registering an MCP server.

The default run performs environment discovery and a real compile. ``--upload``
adds the already guarded upload path, and ``--serial-marker`` adds a persistent
serial check after upload. The script never reads or writes host MCP config.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"


def _environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in tuple(environment):
        if key.startswith("WORKBUDDY_") or key in {
            "CHATMAKER_MCP_CONFIG",
            "CHATMAKER_SKILL_ROOT",
        }:
            environment.pop(key, None)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(RUNTIME) + (os.pathsep + existing if existing else "")
    return environment


def _request(module: str, request: dict[str, Any], environment: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            module,
            "--request-json",
            json.dumps(request, ensure_ascii=False),
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"invalid JSON from {module}: {completed.stdout or completed.stderr}"
        ) from exc
    value["process_returncode"] = completed.returncode
    return value


def _serial(port: str, marker: str, environment: dict[str, str]) -> dict[str, Any]:
    process = subprocess.Popen(
        [sys.executable, "-m", "chatmaker.hardware.serial_monitor"],
        cwd=ROOT,
        env=environment,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None and process.stdout is not None

    def exchange(request: dict[str, Any]) -> dict[str, Any]:
        process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        process.stdin.flush()
        return json.loads(process.stdout.readline())

    opened = exchange({"action": "open", "port": port, "baudrate": 115200})
    if not opened.get("success"):
        process.stdin.close()
        process.wait(timeout=10)
        return {"open": opened, "expect": None, "close": None}
    session_id = str(opened["session_id"])
    expected = exchange(
        {
            "action": "expect",
            "session_id": session_id,
            "marker": marker,
            "timeout": 8,
            "max_lines": 200,
        }
    )
    closed = exchange({"action": "close", "session_id": session_id})
    process.stdin.close()
    process.wait(timeout=10)
    return {"open": opened, "expect": expected, "close": closed}


def run(*, sketch: Path, upload: bool, port: str | None, serial_marker: str | None) -> dict[str, Any]:
    environment = _environment()
    doctor = _request("chatmaker.hardware.starcore", {"action": "doctor"}, environment)
    request: dict[str, Any] = {
        "action": "compile-upload" if upload else "compile",
        "sketch": str(sketch.resolve()),
    }
    if upload:
        request.update({"board_confirmed": True, "port": port})
    project = _request("chatmaker.hardware.starcore", request, environment)
    serial = None
    if upload and serial_marker and project.get("success") and port:
        serial = _serial(port, serial_marker, environment)
    success = bool(doctor.get("success") and project.get("success"))
    if serial is not None:
        success = success and bool(serial.get("expect", {}).get("success"))
    return {
        "success": success,
        "path": "local_cli_without_mcp",
        "mcp_registration_used": False,
        "doctor": doctor,
        "project": project,
        "serial": serial,
        "evidence_boundaries": {
            "command_success_is_physical_effect": False,
            "physical_effect_requires_user_confirmation": True,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sketch",
        type=Path,
        default=ROOT / "examples" / "chatduino" / "starcore" / "onboard-self-test",
    )
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--port")
    parser.add_argument("--serial-marker")
    args = parser.parse_args(argv)
    if (args.port or args.serial_marker) and not args.upload:
        parser.error("--port and --serial-marker require --upload")
    if args.upload and not args.port:
        parser.error("--upload requires --port")
    result = run(
        sketch=args.sketch,
        upload=args.upload,
        port=args.port,
        serial_marker=args.serial_marker,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

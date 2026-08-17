from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Mapping

from . import nano_mindplus
from . import serial_monitor
from . import uno_mindplus


ADAPTERS = {
    "arduino-nano-classic": nano_mindplus,
    "arduino-uno-r3": uno_mindplus,
}


def _result(state: str, *, success: bool, board_id: str, **values: Any) -> dict[str, Any]:
    return {
        "success": success,
        "action": "avr-project-run",
        "state": state,
        "board_id": board_id,
        **values,
    }


def run_project(
    request: dict[str, Any],
    *,
    adapters: Mapping[str, Any] = ADAPTERS,
    serial_manager: Any = serial_monitor.SERIAL_MANAGER,
) -> dict[str, Any]:
    board_id = str(request.get("board_id", ""))
    adapter = adapters.get(board_id)
    if adapter is None:
        return _result(
            "unsupported-board",
            success=False,
            board_id=board_id,
            error="avr_project_board_not_supported",
            supported_boards=sorted(adapters),
        )
    if not request.get("code") and not request.get("sketch"):
        return _result(
            "source-needed",
            success=False,
            board_id=board_id,
            error="sketch_or_code_required",
        )

    doctor = adapter.execute_request({"action": "doctor"})
    if not doctor.get("ready_for_compile"):
        return _result(
            "awaiting-environment",
            success=False,
            board_id=board_id,
            environment=doctor,
            next_action="Install or repair Mind+ 1.x/2.x, then run the same project again.",
        )

    compile_request = {
        key: request[key]
        for key in (
            "code",
            "sketch",
            "project_name",
            "port",
            "timeout",
            "upload_timeout",
        )
        if key in request
    }
    compiled_uploaded = adapter.execute_request(
        {"action": "compile-upload", **compile_request}
    )
    stage = compiled_uploaded.get("stage")
    if stage == "compile":
        return _result(
            "compile-failed",
            success=False,
            board_id=board_id,
            execution=compiled_uploaded,
            next_action="Repair the complete source from the compiler diagnostics and retry.",
        )
    if stage == "awaiting-hardware":
        return _result(
            "compiled-awaiting-hardware",
            success=False,
            board_id=board_id,
            code_compiled=True,
            firmware_uploaded=False,
            execution=compiled_uploaded,
            next_action="Connect one supported wired board and run the same project again.",
        )
    if not compiled_uploaded.get("success"):
        return _result(
            "upload-needs-attention",
            success=False,
            board_id=board_id,
            code_compiled=bool(compiled_uploaded.get("compile", {}).get("success")),
            firmware_uploaded=False,
            execution=compiled_uploaded,
            next_action="Follow the upload diagnosis, then retry without changing the project goal.",
        )

    expected_marker = str(request.get("expected_serial_marker", "")).strip()
    observe_serial = bool(request.get("observe_serial", True)) and bool(expected_marker)
    upload = compiled_uploaded.get("upload") or {}
    port = str(upload.get("port", ""))
    if not observe_serial or not port:
        return _result(
            "uploaded-awaiting-observation",
            success=True,
            board_id=board_id,
            code_compiled=True,
            firmware_uploaded=True,
            execution=compiled_uploaded,
            serial_evidence=None,
            next_action="Observe the serial marker or physical effect before claiming the project works.",
        )

    opened = serial_manager.open(
        port,
        baudrate=int(request.get("serial_baudrate", 9600)),
        timeout=0.1,
    )
    if not opened.get("success"):
        return _result(
            "uploaded-awaiting-observation",
            success=True,
            board_id=board_id,
            code_compiled=True,
            firmware_uploaded=True,
            execution=compiled_uploaded,
            serial_evidence=opened,
            next_action="The upload succeeded; reopen the serial port and look for the expected marker.",
        )

    session_id = str(opened["session_id"])
    observed: dict[str, Any]
    try:
        observed = serial_manager.expect(
            session_id,
            expected_marker,
            timeout=float(request.get("serial_timeout", 5.0)),
            max_lines=200,
        )
    except Exception as exc:
        observed = {
            "success": False,
            "matched": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        closed = serial_manager.close(session_id)
    evidence = {**observed, "closed": closed}
    if observed.get("matched"):
        return _result(
            "physical-confirmation-needed",
            success=True,
            board_id=board_id,
            code_compiled=True,
            firmware_uploaded=True,
            serial_evidence=evidence,
            physical_effect_verified=False,
            next_action="Ask the user to confirm the real screen, sensor or actuator effect.",
        )
    return _result(
        "uploaded-awaiting-observation",
        success=True,
        board_id=board_id,
        code_compiled=True,
        firmware_uploaded=True,
        serial_evidence=evidence,
        next_action="The upload succeeded, but the expected serial marker was not observed yet.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one Nano or Uno project flow.")
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.request_json == "-" else args.request_json
        request = json.loads(raw)
        if not isinstance(request, dict):
            raise ValueError("request_must_be_object")
        result = run_project(request)
    except Exception as exc:
        result = {
            "success": False,
            "action": "avr-project-run",
            "state": "request-failed",
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") or result.get("state") in {
        "awaiting-environment",
        "compiled-awaiting-hardware",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())

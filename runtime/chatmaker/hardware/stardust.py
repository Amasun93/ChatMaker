#!/usr/bin/env python3
"""ChatMaker bridge for the connected self-developed Stardust board.

The currently verified hardware profile is an ATmega328P with a CH340 USB
serial bridge and a 115200 baud Optiboot-compatible bootloader.  Compilation
and upload deliberately reuse the proven classic Nano backend while keeping
the product identity and evidence separate from an Arduino Nano.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import nano_mindplus as avr


BOARD_ID = "stardust-atmega328p"
BRIDGE_NAME = "chatmaker-stardust"
SCHEMA_VERSION = 1


def _with_identity(result: dict[str, Any]) -> dict[str, Any]:
    value = dict(result)
    value["board"] = BOARD_ID
    value["bridge"] = BRIDGE_NAME
    value["schema_version"] = SCHEMA_VERSION
    if value.get("fqbn"):
        value["compatible_avr_target"] = value["fqbn"]
    return value


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action not in {"prepare-environment", "doctor", "ports", "compile", "compile-upload"}:
        raise ValueError(
            "action_must_be_prepare-environment_doctor_ports_compile_or_compile-upload"
        )
    forwarded = dict(request)
    if action == "compile-upload" and forwarded.get("board_confirmed") is not True:
        return _with_identity(
            {
                "action": action,
                "success": False,
                "stage": "identity",
                "error": "stardust_identity_confirmation_required",
                "upload_executed": False,
                "next_action": "confirm_stardust_identity_then_retry",
                "teacher_message": (
                    "上传前请先确认实物是星辰板（ATmega328P/CH340）。"
                    "确认后我会自动继续，不需要你填写 board_confirmed 参数。"
                ),
            }
        )
    if action == "compile-upload":
        # The connected Stardust board has a physically verified 115200
        # Optiboot-compatible loader. Do not waste a full timeout at Nano's
        # legacy 57600 profile.
        forwarded["bootloader_baud_order"] = [115200]
    result = avr.execute_request(forwarded)
    if action == "doctor" and forwarded.get("board_confirmed") is not True:
        result = dict(result)
        result["ready_for_upload"] = False
        result["upload_blocked_by"] = "stardust_identity_confirmation_required"
    return _with_identity(result)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stardust ATmega328P bridge")
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.request_json == "-" else args.request_json
        result = execute_request(json.loads(raw))
    except Exception as exc:
        result = {
            "success": False,
            "error": "unexpected_bridge_error",
            "detail": f"{type(exc).__name__}: {exc}",
            "board": BOARD_ID,
            "bridge": BRIDGE_NAME,
            "schema_version": SCHEMA_VERSION,
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Small JSON-lines contract shared by Arduino serial pages and sketches."""

from __future__ import annotations

import json
from typing import Any


PROTOCOL = "chatmaker-device-jsonl"
VERSION = 1
DEVICE_TYPES = {"hello", "telemetry", "state", "error", "pong"}
BROWSER_TYPES = {"command", "ping"}


def encode_message(message: dict[str, Any], *, sender: str) -> bytes:
    validate_message(message, sender=sender)
    return (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def decode_line(line: str | bytes, *, sender: str) -> dict[str, Any]:
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    message = json.loads(line.strip())
    if not isinstance(message, dict):
        raise ValueError("message_must_be_object")
    validate_message(message, sender=sender)
    return message


def validate_message(message: dict[str, Any], *, sender: str) -> None:
    allowed = DEVICE_TYPES if sender == "device" else BROWSER_TYPES if sender == "browser" else None
    if allowed is None:
        raise ValueError("sender_must_be_device_or_browser")
    kind = message.get("type")
    if kind not in allowed:
        raise ValueError(f"unsupported_{sender}_message_type")
    if kind in {"command", "state"} and not isinstance(message.get("target"), str):
        raise ValueError("target_required")
    if kind == "telemetry" and not isinstance(message.get("sensor"), str):
        raise ValueError("sensor_required")
    if kind == "error" and not isinstance(message.get("message"), str):
        raise ValueError("error_message_required")


def contract_summary() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "version": VERSION,
        "transport": "UTF-8 JSON object followed by newline",
        "browser_to_device": sorted(BROWSER_TYPES),
        "device_to_browser": sorted(DEVICE_TYPES),
    }

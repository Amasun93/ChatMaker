#!/usr/bin/env python3
"""Dependency-free stdio MCP server for Arduino Nano + Mind+ training."""

from __future__ import annotations

import json
import sys
from typing import Any

from chatmaker.hardware import nano_mindplus as bridge


SERVER_NAME = "arduino-nano-mindplus"
SERVER_VERSION = "1.2.0"
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "nano_prepare_environment",
        "description": (
            "先检查电脑是否已有 Mind+ 1.x 或 2.x；已有则复用。两者都没有时，"
            "识别系统与 CPU 架构并优先准备官方 Mind+ 1.x。download=true 只会在"
            "官方已确认的 Windows x64 1.x 包上执行下载，不会静默启动安装器。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "download": {"type": "boolean", "default": False},
                "launch_installer": {"type": "boolean", "default": False},
                "download_dir": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "nano_doctor",
        "description": "检查 Mind+ 1.x/2.x Nano 编译链、系统架构和可安全烧录的串口。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "nano_ports",
        "description": "列出串口、排除蓝牙，并优先识别 CH340/CH341/FT232/CP210 等常见 Nano USB 串口。",
        "inputSchema": {
            "type": "object",
            "properties": {"port": {"type": "string", "pattern": "^COM[0-9]+$"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "nano_compile",
        "description": "使用已安装的 Mind+ 1.x 或 2.x 工具链真实编译完整 Arduino Nano ATmega328P 程序。",
        "inputSchema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string"},
                "project_name": {"type": "string", "default": "nano-project"},
                "timeout": {"type": "integer", "minimum": 30, "maximum": 900, "default": 600},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "nano_compile_upload",
        "description": (
            "完成代码后自动编译并烧录经典 Arduino Nano ATmega328P。检测到唯一明确的 Nano "
            "串口时自动上传；未检测到硬件时提示接入，接入后再次调用即可自动上传。多串口时"
            "要求老师指定。先用 Mind+ Nano 默认 57600，只有典型 Bootloader 同步失败才尝试 115200。"
        ),
        "inputSchema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string"},
                "project_name": {"type": "string", "default": "nano-project"},
                "port": {"type": "string", "pattern": "^COM[0-9]+$"},
                "timeout": {"type": "integer", "minimum": 30, "maximum": 900, "default": 600},
                "upload_timeout": {"type": "integer", "minimum": 30, "maximum": 300, "default": 180},
            },
            "additionalProperties": False,
        },
    },
]


def _tool_result(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "nano_prepare_environment":
        request = {
            "action": "prepare-environment",
            "download": arguments.get("download", False),
            "launch_installer": arguments.get("launch_installer", False),
            "download_dir": arguments.get("download_dir"),
        }
    elif name == "nano_doctor":
        request = {"action": "doctor"}
    elif name == "nano_ports":
        request = {"action": "ports", "port": arguments.get("port")}
    elif name == "nano_compile":
        request = {"action": "compile", **arguments}
    elif name == "nano_compile_upload":
        request = {"action": "compile-upload", **arguments}
    else:
        raise ValueError(f"unknown_tool: {name}")
    result = bridge.execute_request(request)
    expected_pause = result.get("stage") == "awaiting-hardware"
    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
        "isError": not bool(result.get("success")) and not expected_pause,
    }


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    if method and str(method).startswith("notifications/"):
        return None
    if method == "initialize":
        requested = request.get("params", {}).get("protocolVersion")
        protocol = requested if requested in {"2024-11-05", "2025-03-26"} else PROTOCOL_VERSION
        result = {
            "protocolVersion": protocol,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": (
                "只处理经典 Arduino Nano ATmega328P 和杜邦线通用模块。先调用 nano_doctor；"
                "没有 Mind+ 时调用 nano_prepare_environment。编程前核对模块型号/丝印和引脚，"
                "代码完成后默认调用 nano_compile_upload：有硬件就自动上传，没有硬件就提示接入。"
            ),
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = request.get("params", {})
        result = _tool_result(params.get("name", ""), params.get("arguments", {}) or {})
    elif method == "ping":
        result = {}
    else:
        return {
            "jsonrpc": "2.0", "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle(request)
        except Exception as exc:
            response = {
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32603, "message": "Internal error", "data": f"{type(exc).__name__}: {exc}"},
            }
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Dependency-free stdio MCP server for ChatMaker hardware training."""

from __future__ import annotations

import json
import sys
from typing import Any

from chatmaker import catalog
from chatmaker.hardware import esp32_devkit_v1 as esp32_bridge
from chatmaker.hardware import nano_mindplus as bridge
from chatmaker.hardware import serial_monitor
from chatmaker.hardware import uno_mindplus as uno_bridge


SERVER_NAME = "chatmaker-hardware"
SERVER_VERSION = "1.6.0"
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "catalog_search",
        "description": "用中文或英文搜索 ChatMaker 的板卡、常用模块和项目配方，先找到候选，再读取完整资料。",
        "inputSchema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "kind": {"type": "string", "enum": ["board", "component", "recipe"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "catalog_get",
        "description": "按稳定 ID 读取一条完整资料，包括识别方法、供电、引脚、库、示例、常见故障和分层证据。",
        "inputSchema": {
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}},
            "additionalProperties": False,
        },
    },
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
    {
        "name": "uno_prepare_environment",
        "description": "检查并复用 Mind+ 1.x/2.x 的 Uno 编译环境；没有环境时沿用安全的官方 Mind+ 准备流程。",
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
        "name": "uno_doctor",
        "description": "检查 Arduino Uno Rev3 的 Mind+ 1.x/2.x FQBN、115200 上传规则和可用串口。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "uno_ports",
        "description": "列出 Uno 候选串口、拒绝蓝牙，并在多个有线端口时要求明确选择。",
        "inputSchema": {
            "type": "object",
            "properties": {"port": {"type": "string", "pattern": "^COM[0-9]+$"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "uno_compile",
        "description": "使用独立 Uno FQBN 真实编译 Arduino Uno Rev3 ATmega328P 程序。",
        "inputSchema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string"},
                "project_name": {"type": "string", "default": "uno-project"},
                "timeout": {"type": "integer", "minimum": 30, "maximum": 900, "default": 600},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "uno_compile_upload",
        "description": (
            "使用独立 Uno FQBN 编译并在唯一明确有线端口时自动上传 Arduino Uno Rev3。"
            "上传固定使用 Uno 的 115200，不继承 Nano 的 57600/115200 回退。"
        ),
        "inputSchema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string"},
                "project_name": {"type": "string", "default": "uno-project"},
                "port": {"type": "string", "pattern": "^COM[0-9]+$"},
                "timeout": {"type": "integer", "minimum": 30, "maximum": 900, "default": 600},
                "upload_timeout": {"type": "integer", "minimum": 30, "maximum": 300, "default": 180},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "esp32_prepare_environment",
        "description": (
            "只检查 DOIT ESP32 DEVKIT V1 所需的官方 esp32:esp32 3.3.11；"
            "不会下载、安装或用 FireBeetle/mPython 代替。"
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "esp32_doctor",
        "description": (
            "核对 DOIT ESP32 DEVKIT V1 + ESP-WROOM-32 身份、官方 core 3.3.11、"
            "精确 FQBN 和串口；模块丝印本身不算载板确认。"
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "esp32_ports",
        "description": (
            "列出 ESP32 候选串口并拒绝蓝牙；只有明确确认 DOIT 载板后才选择唯一有线端口。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "board_profile": {
                    "type": "string",
                    "enum": ["doit-esp32-devkit-v1-wroom32"],
                },
                "port": {"type": "string", "pattern": "^COM[0-9]+$"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "esp32_compile",
        "description": (
            "使用官方 esp32:esp32@3.3.11 和精确 DOIT FQBN 编译完整 ESP32 程序；"
            "缺少工具链时只报告，不自动安装。"
        ),
        "inputSchema": {
            "type": "object",
            "required": ["code", "board_profile"],
            "properties": {
                "code": {"type": "string"},
                "project_name": {"type": "string", "default": "esp32-project"},
                "board_profile": {
                    "type": "string",
                    "enum": ["doit-esp32-devkit-v1-wroom32"],
                },
                "timeout": {"type": "integer", "minimum": 30, "maximum": 1200, "default": 900},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "esp32_compile_upload",
        "description": (
            "使用精确 DOIT FQBN 编译，并且只有载板身份明确且只剩一个有线端口时才上传。"
            "不会回退到 FireBeetle/mPython；上传成功也不代表启动、Wi-Fi 或实体效果成功。"
        ),
        "inputSchema": {
            "type": "object",
            "required": ["code", "board_profile"],
            "properties": {
                "code": {"type": "string"},
                "project_name": {"type": "string", "default": "esp32-project"},
                "board_profile": {
                    "type": "string",
                    "enum": ["doit-esp32-devkit-v1-wroom32"],
                },
                "port": {"type": "string", "pattern": "^COM[0-9]+$"},
                "timeout": {"type": "integer", "minimum": 30, "maximum": 1200, "default": 900},
                "upload_timeout": {"type": "integer", "minimum": 30, "maximum": 600, "default": 300},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "serial_list",
        "description": "列出串口和当前打开的会话；保留蓝牙标记，不能把蓝牙串口当作 Nano 证据。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "serial_open",
        "description": "按明确端口和波特率打开串口会话；拒绝蓝牙端口和未枚举端口。",
        "inputSchema": {
            "type": "object",
            "required": ["port"],
            "properties": {
                "port": {"type": "string"},
                "baudrate": {"type": "integer", "minimum": 300, "maximum": 2000000, "default": 9600},
                "timeout": {"type": "number", "minimum": 0, "maximum": 10, "default": 0.1},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "serial_read",
        "description": "读取串口文本并识别空输出、乱码和疑似不断重启；空输出不算串口证据。",
        "inputSchema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string"},
                "timeout": {"type": "number", "minimum": 0, "maximum": 60, "default": 1},
                "max_lines": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "serial_expect",
        "description": "在限定时间内等待指定串口标记，并返回实际读到的行。",
        "inputSchema": {
            "type": "object",
            "required": ["session_id", "marker"],
            "properties": {
                "session_id": {"type": "string"},
                "marker": {"type": "string", "minLength": 1},
                "timeout": {"type": "number", "minimum": 0, "maximum": 60, "default": 5},
                "max_lines": {"type": "integer", "minimum": 1, "maximum": 500, "default": 200},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "serial_write",
        "description": "向已打开的串口会话发送 UTF-8 文本，可选择追加换行。",
        "inputSchema": {
            "type": "object",
            "required": ["session_id", "text"],
            "properties": {
                "session_id": {"type": "string"},
                "text": {"type": "string"},
                "newline": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "serial_close",
        "description": "关闭串口会话并释放端口，烧录前必须先关闭。",
        "inputSchema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {"session_id": {"type": "string"}},
            "additionalProperties": False,
        },
    },
]


def _tool_result(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "catalog_search":
        result = catalog.search_catalog(
            str(arguments.get("query", "")),
            kind=arguments.get("kind"),
            limit=int(arguments.get("limit", 20)),
        )
    elif name == "catalog_get":
        result = catalog.get_catalog_record(str(arguments.get("id", "")))
    elif name == "serial_list":
        result = serial_monitor.SERIAL_MANAGER.list()
    elif name == "serial_open":
        result = serial_monitor.SERIAL_MANAGER.open(
            arguments.get("port", ""),
            baudrate=arguments.get("baudrate", 9600),
            timeout=arguments.get("timeout", 0.1),
        )
    elif name == "serial_read":
        result = serial_monitor.SERIAL_MANAGER.read(
            arguments.get("session_id", ""),
            timeout=arguments.get("timeout", 1),
            max_lines=arguments.get("max_lines", 100),
        )
    elif name == "serial_expect":
        result = serial_monitor.SERIAL_MANAGER.expect(
            arguments.get("session_id", ""),
            arguments.get("marker", ""),
            timeout=arguments.get("timeout", 5),
            max_lines=arguments.get("max_lines", 200),
        )
    elif name == "serial_write":
        result = serial_monitor.SERIAL_MANAGER.write(
            arguments.get("session_id", ""),
            arguments.get("text", ""),
            newline=arguments.get("newline", False),
        )
    elif name == "serial_close":
        result = serial_monitor.SERIAL_MANAGER.close(arguments.get("session_id", ""))
    else:
        result = None
    if result is not None:
        expected_empty = result.get("error") in {"no_serial_output", "serial_marker_not_seen"}
        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": not bool(result.get("success")) and not expected_empty,
        }

    adapter = bridge
    if name.startswith("uno_"):
        adapter = uno_bridge
    elif name.startswith("esp32_"):
        adapter = esp32_bridge

    if name in {"nano_prepare_environment", "uno_prepare_environment"}:
        request = {
            "action": "prepare-environment",
            "download": arguments.get("download", False),
            "launch_installer": arguments.get("launch_installer", False),
            "download_dir": arguments.get("download_dir"),
        }
    elif name == "esp32_prepare_environment":
        request = {"action": "doctor"}
    elif name in {"nano_doctor", "uno_doctor", "esp32_doctor"}:
        request = {"action": "doctor"}
    elif name in {"nano_ports", "uno_ports", "esp32_ports"}:
        request = {
            "action": "ports",
            "port": arguments.get("port"),
            "board_profile": arguments.get("board_profile"),
        }
    elif name in {"nano_compile", "uno_compile", "esp32_compile"}:
        request = {"action": "compile", **arguments}
    elif name in {"nano_compile_upload", "uno_compile_upload", "esp32_compile_upload"}:
        request = {"action": "compile-upload", **arguments}
    else:
        raise ValueError(f"unknown_tool: {name}")
    suspended: list[dict[str, Any]] = []
    upload_tools = {"nano_compile_upload", "uno_compile_upload", "esp32_compile_upload"}
    if name in upload_tools:
        suspended = serial_monitor.SERIAL_MANAGER.suspend_all()
    result = adapter.execute_request(request)
    if name in upload_tools:
        resumed = serial_monitor.SERIAL_MANAGER.resume_all(suspended)
        result["serial_sessions"] = {
            "closed_before_upload": suspended,
            "reopened_after_upload": resumed,
        }
    expected_pause = result.get("stage") == "awaiting-hardware"
    expected_setup = result.get("error") in {
        "exact_esp32_toolchain_missing",
        "board_identity_confirmation_required",
    }
    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
        "isError": not bool(result.get("success")) and not expected_pause and not expected_setup,
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
                "处理 Arduino Uno Rev3、经典 Nano ATmega328P、精确确认的 DOIT ESP32 DEVKIT V1 和杜邦线通用模块。"
                "先用 catalog_search/get 读取匹配资料，再按板型调用对应 doctor。ESP32 只接受官方 3.3.11 core "
                "和精确 DOIT FQBN；ESP-WROOM-32 模块丝印本身不算载板确认，也不会静默安装或替换成 FireBeetle。"
                "编程前核对板卡、模块型号/丝印和引脚；Nano/Uno 调用对应 compile_upload，"
                "ESP32 当前先调用 esp32_compile 并保持烧录门未验证。"
                "需要运行日志时使用 serial_open/read/expect/write/close；空输出不算实物证据。"
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

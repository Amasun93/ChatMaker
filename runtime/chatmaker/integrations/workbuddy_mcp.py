#!/usr/bin/env python3
"""Dependency-free stdio MCP server for ChatMaker hardware training."""

from __future__ import annotations

import json
import sys
from typing import Any

from chatmaker import catalog
from chatmaker import knowledge
from chatmaker.cad import generator as cad_generator
from chatmaker.cad import openscad_runtime
from chatmaker.hardware import esp32_devkit_v1 as esp32_bridge
from chatmaker.hardware import board_identification
from chatmaker.hardware import nano_mindplus as bridge
from chatmaker.hardware import project_flow
from chatmaker.hardware import serial_monitor
from chatmaker.hardware import starcore
from chatmaker.hardware import uno_mindplus as uno_bridge
from chatmaker.hardware import unihiker_m10


SERVER_NAME = "chatmaker-hardware"
SERVER_VERSION = "1.18.0"
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "board_identify",
        "description": (
            "接上主控板后自动识别星核板、经典掌控板 V2.x 或掌控板 3.0。"
            "先做安全读取；允许时会先完整备份原程序，再运行临时识别程序并恢复。"
            "仍无法确定时会告诉用户去哪里看型号，并建议拍正反面照片。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string", "pattern": "^COM[0-9]+$"},
                "allow_temporary_firmware": {"type": "boolean", "default": True},
                "backup_dir": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
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
        "name": "knowledge_get",
        "description": (
            "读取某块板卡的 ChatMaker Knowledge 起始索引或一个完整章节。未传 section_id 时返回索引；"
            "传入 section_id 时按需静默确保官方知识包可用并返回完整章节。"
        ),
        "inputSchema": {
            "type": "object",
            "required": ["board_id", "consumer"],
            "properties": {
                "board_id": {
                    "type": "string",
                    "enum": [
                        "arduino-nano-classic",
                        "arduino-uno-r3",
                        "esp32-devkit-v1",
                        "idmc-0001-starcore-v4-2-2",
                        "mpython-classic-v2x",
                        "mpython-v3",
                    ],
                },
                "consumer": {"type": "string", "enum": ["chatmaker", "chatduino", "chatweb", "chatcad"]},
                "section_id": {
                    "type": "string",
                    "enum": [
                        "start-here",
                        "identify-and-safety",
                        "pins-and-electrical",
                        "toolchains-and-upload",
                        "components-and-wiring",
                        "libraries-and-examples",
                        "web-and-protocol",
                        "troubleshooting",
                    ],
                },
                "auto_install": {"type": "boolean", "default": True},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "unihiker_project_check",
        "description": (
            "检查已确认的 UNIHIKER M10 Python 项目：Python 3.7 语法、密钥、资源路径、"
            "桌面 OpenCV 交互、摄像头释放和依赖文件。只证明源码门，不代表已同步或上板运行。"
        ),
        "inputSchema": {
            "type": "object",
            "required": ["project"],
            "properties": {"project": {"type": "string", "minLength": 1}},
            "additionalProperties": False,
        },
    },
    {
        "name": "unihiker_credential_help",
        "description": "按项目实际使用的云服务，返回应替换的私有配置字段、凭据类型和官方获取入口；不读取或保存真实密钥。",
        "inputSchema": {
            "type": "object",
            "required": ["provider"],
            "properties": {
                "provider": {
                    "type": "string",
                    "enum": [
                        "aliyun-dashscope",
                        "aliyun-qwen-omni",
                        "volcengine-ark",
                        "volcengine-openspeech",
                        "baidu-tts",
                    ],
                }
            },
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
        "name": "avr_project_run",
        "description": (
            "Nano/Uno 默认连续入口：检查 Mind+ 环境、真实编译、有唯一明确有线端口时自动烧录，"
            "并可等待串口标记。没有接板时停在“编译完成、等待硬件”，不会误报烧录成功。"
        ),
        "inputSchema": {
            "type": "object",
            "required": ["board_id", "code"],
            "properties": {
                "board_id": {
                    "type": "string",
                    "enum": ["arduino-nano-classic", "arduino-uno-r3"],
                },
                "code": {"type": "string", "minLength": 1},
                "project_name": {"type": "string"},
                "port": {"type": "string", "pattern": "^COM[0-9]+$"},
                "timeout": {"type": "integer", "minimum": 30, "maximum": 900, "default": 600},
                "upload_timeout": {"type": "integer", "minimum": 30, "maximum": 300, "default": 180},
                "expected_serial_marker": {"type": "string"},
                "observe_serial": {"type": "boolean", "default": True},
                "serial_baudrate": {"type": "integer", "minimum": 300, "maximum": 2000000, "default": 9600},
                "serial_timeout": {"type": "number", "minimum": 0, "maximum": 60, "default": 5},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "esp32_prepare_environment",
        "description": (
            "自动检查 DOIT ESP32 DEVKIT V1 的官方编译环境，并且只安装 ChatMaker 验证过的 "
            "esp32:esp32@3.3.11；不会跳到最新版、降级较新的官方 core，或用 FireBeetle/mPython 代替。"
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "starcore_doctor",
        "description": "检查星核板 v4.2.2 的 Mind+ 环境和有线串口；优先复用 2.x，只有缺少可用 2.x 时才回退 1.x。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "starcore_ports",
        "description": "列出星核板候选有线串口；串口芯片不能单独证明板卡身份。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "starcore_compile",
        "description": "使用已安装的 Mind+ 2.x 优先后端真实编译星核板程序；1.x 仅作为兼容回退。",
        "inputSchema": {
            "type": "object", "required": ["code"],
            "properties": {
                "code": {"type": "string", "minLength": 1},
                "project_name": {"type": "string", "default": "starcore-project"},
                "timeout": {"type": "integer", "minimum": 30, "maximum": 1200, "default": 900},
            }, "additionalProperties": False,
        },
    },
    {
        "name": "starcore_compile_upload",
        "description": "编译星核板程序；仅在用户确认 v4.2.2 板卡身份且只有一个明确有线端口时自动烧录。",
        "inputSchema": {
            "type": "object", "required": ["code", "board_confirmed"],
            "properties": {
                "code": {"type": "string", "minLength": 1},
                "board_confirmed": {"type": "boolean"},
                "project_name": {"type": "string", "default": "starcore-project"},
                "port": {"type": "string", "pattern": "^COM[0-9]+$"},
                "timeout": {"type": "integer", "minimum": 30, "maximum": 1200, "default": 900},
                "upload_timeout": {"type": "integer", "minimum": 30, "maximum": 600, "default": 300},
            }, "additionalProperties": False,
        },
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
                "timeout": {"type": "integer", "minimum": 30, "maximum": 1200, "default": 1200},
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
                "timeout": {"type": "integer", "minimum": 30, "maximum": 1200, "default": 1200},
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
    {
        "name": "cad_profile_get",
        "description": "读取 Nano、Uno、ESP32 或星核板的清洗后机械尺寸、孔位、来源和验证状态。",
        "inputSchema": {
            "type": "object",
            "required": ["board_id"],
            "properties": {
                "board_id": {
                    "type": "string",
                    "enum": [
                        "arduino-nano-classic",
                        "arduino-uno-r3",
                        "esp32-devkit-v1",
                        "idmc-0001-starcore-v4-2-2",
                    ],
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "cad_component_profile_get",
        "description": "按精确组件 ID 读取星核板自研模块的清洗机械尺寸、孔位、开口资料和实体适配状态；缺失尺寸必须先测量。",
        "inputSchema": {
            "type": "object",
            "required": ["component_id"],
            "properties": {
                "component_id": {
                    "type": "string",
                    "enum": [
                        "idmd-0001-starcore-rgb-light",
                        "idmd-0002-starcore-serial-mp3",
                        "idmd-0021-starcore-oled-1-3",
                        "idms-0001-starcore-button",
                        "idms-0003-starcore-potentiometer",
                        "idms-0008-starcore-dht11",
                        "idms-0009-starcore-ultrasonic",
                    ],
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "cad_fabrication_get",
        "description": "读取 ChatCAD 的设备与工艺卡，包括材料默认厚度、LaserMaker 颜色图层、加工顺序和参数校准边界。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "equipment_id": {
                    "type": "string",
                    "default": "lasermaker-generic",
                    "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
                },
                "material_id": {
                    "type": "string",
                    "default": "wood-sheet-3mm",
                    "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "cad_openscad_status",
        "description": "只读检查本机是否已有 OpenSCAD，并返回可执行文件路径和版本；不会安装或启动任何程序。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "cad_openscad_prepare",
        "description": (
            "准备 ChatCAD 本地参数化建模依赖。未安装时必须先取得用户明确同意，"
            "再传 allow_install=true；Windows 只调用 OpenSCAD 官网明确列出的 WinGet 官方包。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"allow_install": {"type": "boolean", "default": False}},
            "additionalProperties": False,
        },
    },
    {
        "name": "cad_generate",
        "description": "按制作方式生成 Chat2D 图纸或已确认的 Chat3D 结果。Chat3D 必须先确认任务卡和开始生成；默认只返回 MakerLab 可用的 OpenSCAD 代码，明确选择 ChatMaker 时才写出模型和预览文件。",
        "inputSchema": {
            "type": "object",
            "required": ["project_name"],
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "板卡相关外壳、安装板或模块项目必填；独立齿轮机构可省略。",
                    "enum": [
                        "arduino-nano-classic",
                        "arduino-uno-r3",
                        "esp32-devkit-v1",
                        "idmc-0001-starcore-v4-2-2",
                    ],
                },
                "project_name": {"type": "string", "minLength": 1},
                "output_dir": {"type": "string", "minLength": 1},
                "generation_confirmed": {"type": "boolean", "default": False},
                "delivery_mode": {
                    "type": "string",
                    "enum": ["makerlab-code", "chatmaker-preview"],
                    "default": "makerlab-code",
                    "description": "Use makerlab-code when MakerLab login is convenient; use chatmaker-preview when the user has no MakerWorld account or login is inconvenient, returning both OpenSCAD code and a parameter simulation page.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["chat2d", "chat3d", "mounting-plate"],
                    "default": "mounting-plate",
                },
                "equipment_id": {
                    "type": "string",
                    "default": "lasermaker-generic",
                    "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
                },
                "material_id": {
                    "type": "string",
                    "default": "wood-sheet-3mm",
                    "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
                },
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clearance": {"type": "number", "minimum": 1, "maximum": 30},
                        "plate_thickness": {"type": "number", "minimum": 1, "maximum": 10},
                        "standoff_height": {"type": "number", "minimum": 0, "maximum": 20},
                        "hole_diameter": {"type": "number", "minimum": 0.8, "maximum": 10},
                        "standoff_outer_diameter": {"type": "number", "minimum": 1.8, "maximum": 20},
                        "box_width": {"type": "number", "minimum": 30, "maximum": 600},
                        "box_depth": {"type": "number", "minimum": 30, "maximum": 600},
                        "box_height": {"type": "number", "minimum": 15, "maximum": 300},
                        "material_thickness": {"type": "number", "minimum": 1, "maximum": 12},
                        "joint_size": {"type": "number", "minimum": 3, "maximum": 50},
                        "inner_width": {"type": "number", "minimum": 20, "maximum": 500},
                        "inner_depth": {"type": "number", "minimum": 20, "maximum": 500},
                        "inner_height": {"type": "number", "minimum": 8, "maximum": 300},
                        "wall": {"type": "number", "minimum": 1, "maximum": 8},
                        "floor": {"type": "number", "minimum": 1, "maximum": 8},
                        "lid": {"type": "number", "minimum": 1, "maximum": 8},
                        "engrave_text": {"type": "string", "maxLength": 24},
                        "text_size": {"type": "number", "minimum": 3, "maximum": 60},
                        "text_depth": {"type": "number", "minimum": 0.4, "maximum": 5},
                        "engrave_font": {"type": "string", "description": "Optional local font file override; defaults to ChatMaker's bundled CJK font and is converted to polygons before MakerLab"},
                        "design_kind": {
                            "type": "string",
                            "enum": ["enclosure", "nameplate", "gear_pair", "rack_and_pinion"],
                            "default": "enclosure",
                        },
                        "tag_length": {"type": "number", "minimum": 30, "maximum": 200},
                        "tag_width": {"type": "number", "minimum": 12, "maximum": 80},
                        "corner_radius": {"type": "number", "minimum": 0, "maximum": 20},
                        "hole_margin_x": {"type": "number", "minimum": 0, "maximum": 50},
                        "hole_margin_y": {"type": "number", "minimum": 0, "maximum": 50},
                        "text_x": {"type": "number", "minimum": -100, "maximum": 100},
                        "text_y": {"type": "number", "minimum": -100, "maximum": 100},
                        "gear_module": {"type": "number", "minimum": 0.5, "maximum": 5},
                        "driver_teeth": {"type": "integer", "minimum": 8, "maximum": 80},
                        "driven_teeth": {"type": "integer", "minimum": 8, "maximum": 120},
                        "pinion_teeth": {"type": "integer", "minimum": 8, "maximum": 80},
                        "rack_teeth": {"type": "integer", "minimum": 4, "maximum": 80},
                        "pressure_angle": {"type": "number", "minimum": 14.5, "maximum": 30},
                        "gear_thickness": {"type": "number", "minimum": 2, "maximum": 20},
                        "shaft_diameter": {"type": "number", "minimum": 2, "maximum": 20},
                        "shaft_clearance": {"type": "number", "minimum": 0.05, "maximum": 1},
                        "backlash": {"type": "number", "minimum": 0, "maximum": 0.8},
                        "bracket_thickness": {"type": "number", "minimum": 2, "maximum": 10},
                        "rack_body_height": {"type": "number", "minimum": 3, "maximum": 30},
                    },
                    "additionalProperties": False,
                },
            },
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
    elif name == "knowledge_get":
        request = {
            "action": "section" if "section_id" in arguments else "index",
            "board_id": arguments.get("board_id", ""),
            "consumer": arguments.get("consumer", ""),
        }
        if "section_id" in arguments:
            request["section_id"] = arguments.get("section_id", "")
            request["auto_install"] = arguments.get("auto_install", True)
        result = knowledge.execute_request(request)
    elif name == "board_identify":
        suspended = serial_monitor.SERIAL_MANAGER.suspend_all()
        try:
            result = board_identification.execute_request(
                {"action": "identify", **arguments}
            )
        finally:
            resumed = serial_monitor.SERIAL_MANAGER.resume_all(suspended)
        result["serial_sessions"] = {
            "closed_before_identification": suspended,
            "reopened_after_identification": resumed,
        }
    elif name == "unihiker_project_check":
        result = unihiker_m10.execute_request(
            {"action": "check_project", "project": arguments.get("project", "")}
        )
    elif name == "unihiker_credential_help":
        result = unihiker_m10.execute_request(
            {"action": "credential_help", "provider": arguments.get("provider", "")}
        )
    elif name == "cad_profile_get":
        result = cad_generator.execute_request(
            {"action": "profile", "board_id": arguments.get("board_id", "")}
        )
    elif name == "cad_component_profile_get":
        result = cad_generator.execute_request(
            {
                "action": "component-profile",
                "component_id": arguments.get("component_id", ""),
            }
        )
    elif name == "cad_fabrication_get":
        result = cad_generator.execute_request(
            {
                "action": "fabrication-profile",
                "equipment_id": arguments.get("equipment_id", "lasermaker-generic"),
                "material_id": arguments.get("material_id", "wood-sheet-3mm"),
            }
        )
    elif name == "cad_openscad_status":
        result = openscad_runtime.status()
    elif name == "cad_openscad_prepare":
        result = openscad_runtime.prepare(allow_install=arguments.get("allow_install") is True)
    elif name == "cad_generate":
        cad_request = {"action": "generate", **arguments}
        if str(arguments.get("mode", "mounting-plate")) == "chat3d":
            if arguments.get("generation_confirmed") is not True:
                result = {
                    "success": False,
                    "error": "chat3d_generation_confirmation_required",
                    "state": "awaiting-generation-confirmation",
                    "stage": "planning",
                    "required": [
                        "confirmed_task_card",
                        "explicit_start_generation",
                        "delivery_mode",
                    ],
                    "delivery_modes": ["makerlab-code", "chatmaker-preview"],
                    "beginner_message": (
                        "请先确认任务卡。准备开始后，请明确说“开始生成”，"
                        "然后告诉我你是否方便登录 MakerLab：方便就直接给 OpenSCAD 代码；"
                        "没有 MakerWorld 账号或不方便登录，就同时给 OpenSCAD 代码和 ChatMaker 仿真界面。"
                    ),
                }
            else:
                cad_request.setdefault("delivery_mode", "makerlab-code")
                result = cad_generator.execute_request(cad_request)
        else:
            result = cad_generator.execute_request(cad_request)
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
    elif name == "avr_project_run":
        suspended = serial_monitor.SERIAL_MANAGER.suspend_all()
        try:
            result = project_flow.run_project(
                arguments,
                serial_manager=serial_monitor.SERIAL_MANAGER,
            )
        finally:
            resumed = serial_monitor.SERIAL_MANAGER.resume_all(suspended)
        result["serial_sessions"] = {
            "closed_before_upload": suspended,
            "reopened_after_upload": resumed,
        }
    else:
        result = None
    if result is not None:
        expected_empty = result.get("error") in {"no_serial_output", "serial_marker_not_seen"}
        expected_project_pause = result.get("state") in {
            "awaiting-environment",
            "compiled-awaiting-hardware",
            "uploaded-awaiting-observation",
            "physical-confirmation-needed",
            "awaiting-generation-confirmation",
            "awaiting-install-confirmation",
            "manual-install-required",
        }
        expected_identification_pause = result.get("identification", {}).get("status") in {
            "probable",
            "ambiguous",
            "unavailable",
            "recovery-required",
        }
        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": (
                not bool(result.get("success"))
                and not expected_empty
                and not expected_project_pause
                and not expected_identification_pause
            ),
        }

    adapter = bridge
    if name.startswith("uno_"):
        adapter = uno_bridge
    elif name.startswith("esp32_"):
        adapter = esp32_bridge
    elif name.startswith("starcore_"):
        adapter = starcore

    if name in {"nano_prepare_environment", "uno_prepare_environment"}:
        request = {
            "action": "prepare-environment",
            "download": arguments.get("download", False),
            "launch_installer": arguments.get("launch_installer", False),
            "download_dir": arguments.get("download_dir"),
        }
    elif name == "esp32_prepare_environment":
        request = {"action": "prepare-environment"}
    elif name in {"nano_doctor", "uno_doctor", "esp32_doctor", "starcore_doctor"}:
        request = {"action": "doctor"}
    elif name in {"nano_ports", "uno_ports", "esp32_ports", "starcore_ports"}:
        request = {
            "action": "ports",
            "port": arguments.get("port"),
            "board_profile": arguments.get("board_profile"),
        }
    elif name in {"nano_compile", "uno_compile", "esp32_compile", "starcore_compile"}:
        request = {"action": "compile", **arguments}
    elif name in {"nano_compile_upload", "uno_compile_upload", "esp32_compile_upload", "starcore_compile_upload"}:
        request = {"action": "compile-upload", **arguments}
    else:
        raise ValueError(f"unknown_tool: {name}")
    suspended: list[dict[str, Any]] = []
    upload_tools = {"nano_compile_upload", "uno_compile_upload", "esp32_compile_upload", "starcore_compile_upload"}
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
        "starcore_identity_confirmation_required",
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
                "处理 Arduino Uno Rev3、经典 Nano ATmega328P、星核板 v4.2.2、精确确认的 DOIT ESP32 DEVKIT V1、UNIHIKER M10 和杜邦线通用模块。"
                "用户接入未知主控板时先调用 board_identify；它会优先自动识别，必要时在完整备份后运行临时程序并恢复，"
                "仍不确定就用简单语言引导查看板上型号，用户看不懂时请其拍正反面照片。"
                "先用 catalog_search/get 读取匹配资料；询问板载器件时把板卡名和器件名一起搜索，命中板卡后继续用 knowledge_get 读取 start-here 索引或相关章节，"
                "再按板型调用对应 doctor。ESP32 只接受官方 3.3.11 core "
                "和精确 DOIT FQBN；先调用 esp32_prepare_environment 自动检查，并且只安装 ChatMaker 验证的锁定版本。"
                "ESP-WROOM-32 模块丝印本身不算载板确认，也不会替换成 FireBeetle。"
                "星核板优先使用 Mind+ 2.x 的 mindplus:esp32:mpython 目标；只有没有可用 2.x 时才回退 1.x。"
                "M10 与 K10 必须分开；M10 先用 catalog_get 读取板卡记录，再调用 unihiker_project_check，源码通过不代表已同步、运行或产生实体效果。"
                "使用云端模型或语音服务时调用 unihiker_credential_help，明确告诉用户替换字段和官方获取入口；不得复用内部 Key。"
                "编程前核对板卡、模块型号/丝印和引脚；Nano/Uno 默认调用 avr_project_run 连续完成"
                "环境检查、编译、可用时烧录和串口观察，独立工具用于诊断；"
                "ESP32 调用 esp32_compile_upload；只有精确载板身份和唯一非蓝牙有线端口都明确时才上传，"
                "上传成功仍不能代替启动、Wi-Fi、HTTP 或实体效果验证。"
                "需要运行日志时使用 serial_open/read/expect/write/close；空输出不算实物证据。"
                "需要制作安装底板、激光切割图或三维模型时，先用 cad_profile_get 核对板卡机械资料；"
                "涉及星核板自研模块时再用 cad_component_profile_get 按精确 ID 读取组件机械资料，缺失尺寸不得猜测。"
                "激光切割任务再用 cad_fabrication_get 读取设备、材料、颜色图层和校准边界，确认后用 cad_generate 生成图纸和预览。"
                "任何三维任务都先讨论并整理任务卡；在用户确认任务卡且明确说“开始生成”前，不得调用 cad_generate。"
                "开始生成前只问一个小白能回答的问题：是否方便登录 MakerLab。"
                "MakerLab 路线直接给完整 OpenSCAD 代码和官方入口 https://makerworld.com.cn/zh/makerlab，"
                "不默认交付 STL、右侧预览或截图。用户没有 MakerWorld 账号或不方便登录时，"
                "先调用 cad_openscad_status 检查本地依赖。缺失时先征得明确安装同意，只有得到同意后才调用"
                "cad_openscad_prepare 且传 allow_install=true；不得把开始建模视为安装授权。随后使用 chatmaker-preview，"
                "同时交付完整 OpenSCAD 代码和 ChatMaker 仿真界面，让用户在界面中调整参数并导出 SCAD 或 STL；仍不默认截图。"
                "MakerLab 中文不得使用 Microsoft YaHei、SimHei 或 SimSun 等电脑本机字体。"
                "名牌默认使用已在 MakerLab 实测通过的 Noto Sans SC:style=Regular；给代码时必须同时提醒用户："
                "点击代码区底部带 T 的放大镜图标（字体），搜索并勾选这个精确名称，确认后再生成。字体清单会更新，其他字体只以编辑器当前面板为准。"
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
            sys.stdout.write(json.dumps(response, ensure_ascii=True, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

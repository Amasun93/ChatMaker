#!/usr/bin/env python3
"""Import the 23-module handoff manifest and sync compact runtime records."""

from __future__ import annotations

import argparse
import csv
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator
import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "knowledge_sources/manifests/self-developed-hardware.yaml"
SCHEMA_PATH = ROOT / "knowledge_sources/schemas/self-developed-hardware.schema.yaml"
RUNTIME_INDEX_PATH = ROOT / "knowledge/hardware/self-developed-modules.yaml"
BOARD_ID = "idmc-0001-starcore-v4-2-2"
SOURCE_ID = "self-developed-hardware-handoff-2026-07-25"
SOURCE_URL = "https://github.com/Amasun93/ChatMaker/tree/main/knowledge_sources"
CHECKED_AT = "2026-08-27"
GUIDE_PATH = "docs/hardware/self-developed-modules.md"


CATALOG_IDS = {
    "IDMC-0001": BOARD_ID,
    "IDMD-0001": "idmd-0001-starcore-rgb-light",
    "IDMD-0002": "idmd-0002-starcore-serial-mp3",
    "IDMD-0003": "idmd-0003-starcore-asr",
    "IDMD-0021": "idmd-0021-starcore-oled-1-3",
    "IDMF-0001": "idmf-0001-starcore-pd-power-adapter",
    "IDMF-0010": "idmf-0010-starcore-power-splitter",
    "IDMF-0011": "idmf-0011-starcore-usb-hub-1-to-4",
    "IDMM-0001": "idmm-0001-starcore-four-channel-dc-motor-driver",
    "IDMM-0007": "idmm-0007-starcore-serial-servo-driver",
    "IDMS-0001": "idms-0001-starcore-button",
    "IDMS-0002": "idms-0002-starcore-toggle-switch",
    "IDMS-0003": "idms-0003-starcore-potentiometer",
    "IDMS-0004": "idms-0004-starcore-rotary-encoder",
    "IDMS-0005": "idms-0005-starcore-light-sensor",
    "IDMS-0006": "idms-0006-starcore-microphone-sensor",
    "IDMS-0007": "idms-0007-starcore-gas-sensor",
    "IDMS-0008": "idms-0008-starcore-dht11",
    "IDMS-0009": "idms-0009-starcore-ultrasonic",
    "IDMS-0010": "idms-0010-starcore-laser-receiver",
    "IDMS-0011": "idms-0011-starcore-slot-counter",
    "IDMS-0012": "idms-0012-starcore-limit-switch",
    "IDMS-0036": "idms-0036-starcore-analog-accelerometer",
}

DISPLAY_NAMES = {
    "IDMC-0001": "星核板主控",
    "IDMD-0001": "三色 RGB 灯",
    "IDMD-0002": "串口 MP3 播放模块",
    "IDMD-0003": "离线语音识别模块",
    "IDMD-0021": "1.3 寸 OLED 显示屏",
    "IDMF-0001": "PD 快充电源适配模块",
    "IDMF-0010": "电源与信号并线器",
    "IDMF-0011": "一分四 USB 集线器",
    "IDMM-0001": "四路直流电机驱动模块",
    "IDMM-0007": "串口舵机驱动模块",
    "IDMS-0001": "按钮传感器",
    "IDMS-0002": "三档钮子开关",
    "IDMS-0003": "电位器旋钮",
    "IDMS-0004": "编码器旋钮",
    "IDMS-0005": "光照强度传感器",
    "IDMS-0006": "麦克风声音传感器",
    "IDMS-0007": "烟雾与酒精气体传感器",
    "IDMS-0008": "温湿度传感器",
    "IDMS-0009": "超声波测距传感器",
    "IDMS-0010": "激光接收传感器",
    "IDMS-0011": "U 形槽光电计数器",
    "IDMS-0012": "微动限位开关",
    "IDMS-0036": "模拟三轴加速度传感器",
}

PURPOSES = {
    "IDMC-0001": "作为项目主控，读取传感器并控制灯光、声音、显示和执行机构。",
    "IDMD-0001": "用三个 PWM 通道混合红、绿、蓝三种颜色。",
    "IDMD-0002": "通过串口播放存储介质中的提示音或音乐。",
    "IDMD-0003": "在本地识别预先配置的语音词条，并用串口交换识别结果。",
    "IDMD-0021": "显示文字、状态和传感器读数。",
    "IDMF-0001": "把 USB-C PD 电源协商后的电能接入项目供电系统。",
    "IDMF-0010": "在确认同一电压轨后分配电源或信号连接。",
    "IDMF-0011": "把一个 USB 上行口扩展为四个 USB 连接口。",
    "IDMM-0001": "让主控分别控制四路直流电机的方向和速度。",
    "IDMM-0007": "通过串口管理配套舵机总线；命令协议取决于模块和舵机版本。",
    "IDMS-0001": "检测学生是否按下按钮。",
    "IDMS-0002": "提供可保持的三档机械开关状态。",
    "IDMS-0003": "把旋钮位置转换为模拟电压。",
    "IDMS-0004": "检测旋转方向、步数和按压动作。",
    "IDMS-0005": "把环境光强变化转换为模拟信号。",
    "IDMS-0006": "把声音强弱变化转换为带偏置的模拟信号。",
    "IDMS-0007": "观察烟雾、酒精等气体引起的模拟信号变化，仅用于教学实验。",
    "IDMS-0008": "读取环境温度和相对湿度。",
    "IDMS-0009": "测量模块前方目标的大致距离。",
    "IDMS-0010": "判断接收端是否检测到配套光源。",
    "IDMS-0011": "检测物体穿过 U 形槽并用于计数或测速。",
    "IDMS-0012": "检测机构是否到达机械行程边界。",
    "IDMS-0036": "分别输出 X、Y、Z 三个方向的模拟加速度信号。",
}

IO_ROLES = {
    "controller": "controller",
    "output": "output",
    "input_output": "input_output",
    "display": "output",
    "power": "power",
    "connectivity": "connectivity",
    "motor_driver": "actuator",
    "servo_driver": "actuator",
    "digital_sensor": "input",
    "passive_switch": "input",
    "analog_sensor": "input",
    "distance_sensor": "input",
}

USABILITY = {
    "IDMC-0001": "guidance_ready",
    "IDMD-0001": "guidance_ready",
    "IDMD-0002": "guidance_ready",
    "IDMD-0021": "guidance_ready",
    "IDMS-0001": "guidance_ready",
    "IDMS-0003": "guidance_ready",
    "IDMS-0008": "guidance_ready",
    "IDMS-0009": "guidance_ready",
    "IDMF-0001": "retrieval_only",
    "IDMF-0010": "retrieval_only",
    "IDMF-0011": "retrieval_only",
    "IDMM-0007": "retrieval_only",
}

EXAMPLE_CAPABILITIES = {
    "IDMC-0001": ["读取板载按键与加速度", "控制板载蜂鸣器", "组合外接自研模块"],
    "IDMD-0001": ["呼吸灯", "颜色状态提示"],
    "IDMD-0002": ["播放提示音", "按事件切换音轨"],
    "IDMD-0003": ["语音口令触发", "识别结果串口上报"],
    "IDMD-0021": ["欢迎页面", "传感器数据显示"],
    "IDMF-0001": ["项目供电方案检索与实测确认"],
    "IDMF-0010": ["同电压轨分配方案检索"],
    "IDMF-0011": ["USB 外设连接方案检索"],
    "IDMM-0001": ["电机方向控制", "四路电机分组控制"],
    "IDMM-0007": ["舵机总线识别与只读诊断"],
    "IDMS-0001": ["按钮控制灯光", "按键计数"],
    "IDMS-0002": ["三档模式选择"],
    "IDMS-0003": ["旋钮调亮度", "模拟量阈值控制"],
    "IDMS-0004": ["菜单选择", "旋转计数"],
    "IDMS-0005": ["自动夜灯", "光照趋势观察"],
    "IDMS-0006": ["声音强弱显示", "拍手触发实验"],
    "IDMS-0007": ["气体变化趋势观察", "预热与校准实验"],
    "IDMS-0008": ["温湿度串口监测", "环境仪表盘"],
    "IDMS-0009": ["距离显示", "靠近提醒"],
    "IDMS-0010": ["光束中断检测", "对准实验"],
    "IDMS-0011": ["物体计数", "转速脉冲采集"],
    "IDMS-0012": ["行程到位检测", "机构回零实验"],
    "IDMS-0036": ["倾斜趋势观察", "三轴模拟量采样"],
}

DIRECT_WIRING = {
    "IDMD-0001": [
        {"module_pin": "VCC", "board_pin": "3V3", "status": "confirmed"},
        {"module_pin": "RED/GREEN/BLUE", "board_pin": "three unoccupied PWM pins", "status": "assignment_required"},
    ],
    "IDMD-0002": [
        {"module_pin": "VCC", "board_pin": "5V connector bank", "status": "confirmed"},
        {"module_pin": "GND", "board_pin": "GND", "status": "confirmed"},
        {"module_pin": "TXD", "board_pin": "P15 (controller RX)", "status": "confirmed"},
        {"module_pin": "RXD", "board_pin": "P16 (controller TX)", "status": "confirmed"},
    ],
    "IDMD-0021": [
        {"module_pin": "VCC/GND/SCL/SDA", "board_pin": "matching-voltage I2C bank on P19/P20", "status": "confirmed"},
    ],
    "IDMS-0001": [
        {"module_pin": "VCC/GND", "board_pin": "3V3/GND", "status": "confirmed"},
        {"module_pin": "SIG", "board_pin": "one unoccupied digital input", "status": "assignment_required"},
    ],
    "IDMS-0003": [
        {"module_pin": "VCC/GND", "board_pin": "3V3/GND", "status": "safe_default"},
        {"module_pin": "SIG", "board_pin": "one unoccupied ADC input", "status": "assignment_required"},
    ],
    "IDMS-0008": [
        {"module_pin": "VCC/GND", "board_pin": "3V3/GND", "status": "confirmed"},
        {"module_pin": "SIG", "board_pin": "P0 classroom route", "status": "confirmed"},
    ],
    "IDMS-0009": [
        {"module_pin": "VCC/GND", "board_pin": "3V3/GND", "status": "confirmed"},
        {"module_pin": "TRIG", "board_pin": "P_H", "status": "confirmed"},
        {"module_pin": "ECHO", "board_pin": "P_O", "status": "confirmed"},
    ],
}


def _read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"mapping_required:{path}")
    return value


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _evidence_type(path: str) -> str:
    lower = path.casefold()
    suffix = Path(path).suffix.casefold()
    if suffix in {".step", ".stp"}:
        return "mechanical-step"
    if suffix == ".dxf":
        return "mechanical-dxf"
    if suffix in {".doc", ".docx", ".txt", ".md", ".xlsx"}:
        return "documentation"
    if suffix == ".pdf" and ("sch" in lower or "原理" in lower):
        return "schematic"
    if suffix == ".pdf":
        return "datasheet"
    if suffix in {".mpext", ".sb3"} or "mind+" in lower:
        return "extension"
    if suffix in {".png", ".jpg", ".jpeg"}:
        return "image"
    return "archive"


def _select_source_evidence(rows: list[dict[str, str]], module_root: str) -> list[dict[str, str]]:
    candidates = [row for row in rows if row["相对路径"].startswith(module_root + "/")]
    groups: dict[str, list[dict[str, str]]] = {}
    for row in candidates:
        groups.setdefault(_evidence_type(row["相对路径"]), []).append(row)
    selected: list[dict[str, str]] = []
    limits = {
        "mechanical-step": 1,
        "mechanical-dxf": 1,
        "documentation": 2,
        "schematic": 1,
        "datasheet": 1,
        "extension": 2,
    }
    for evidence_type, limit in limits.items():
        for row in sorted(groups.get(evidence_type, []), key=lambda item: (len(item["相对路径"]), item["相对路径"]))[:limit]:
            selected.append({"path": row["相对路径"], "sha256": row["SHA256"].upper(), "evidence_type": evidence_type})
    return selected


def _unknowns(module: dict[str, Any], hardware_id: str) -> list[str]:
    unknown: list[str] = []
    status = module.get("verification_status")
    if status in {"partial", "documentation_conflict"}:
        unknown.append("资料未形成可直接执行的完整电气或协议结论，必须核对原文和实物版本。")
    if not module.get("supply_v") and module.get("category") not in {"controller", "passive_switch", "connectivity"}:
        unknown.append("交接资料的结构化提取未确认统一供电范围。")
    if hardware_id not in DIRECT_WIRING and module.get("category") not in {"controller", "connectivity", "power"}:
        unknown.append("尚无经过当前 ChatMaker 证据链确认的星核板具体引脚分配。")
    if hardware_id == "IDMS-0010":
        unknown.append("供电范围在说明材料中存在冲突，不能自动选择 3.3V 或 5V。")
    if hardware_id == "IDMS-0036":
        unknown.append("归档编号为 IDMS-0036，但随附机械/原理图文件名含 IDMS-0013，需核对实物丝印。")
    if hardware_id == "IDMM-0007":
        unknown.append("舵机命令协议和配套舵机型号未确认，禁止生成运动命令。")
    return list(dict.fromkeys(unknown))


def import_manifest(source_root: Path, legacy_catalog: Path, legacy_mechanics: Path) -> dict[str, Any]:
    index_path = source_root / "03_归档索引/自研模块索引.json"
    file_index_path = source_root / "03_归档索引/全文件清单.csv"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    legacy = json.loads(legacy_catalog.read_text(encoding="utf-8"))
    mechanics = json.loads(legacy_mechanics.read_text(encoding="utf-8"))
    with file_index_path.open("r", encoding="utf-8-sig", newline="") as handle:
        file_rows = list(csv.DictReader(handle))
    indexed = {item["模块编号"]: item for item in index}
    curated = {item["id"]: item for item in legacy["modules"]}
    mechanical = {item["id"]: item for item in mechanics["profiles"]}
    expected = set(CATALOG_IDS)
    if set(indexed) != expected or set(curated) != expected or set(mechanical) != expected:
        raise ValueError("source_module_set_mismatch")
    modules: list[dict[str, Any]] = []
    for hardware_id in CATALOG_IDS:
        source = indexed[hardware_id]
        facts = deepcopy(curated[hardware_id])
        mech = deepcopy(mechanical[hardware_id])
        category = str(facts["category"])
        evidence = _select_source_evidence(file_rows, source["主目录"])
        evidence.extend([
            {"path": "03_归档索引/自研模块索引.json", "sha256": _sha256(index_path), "evidence_type": "index"},
            {"path": "03_归档索引/全文件清单.csv", "sha256": _sha256(file_index_path), "evidence_type": "index"},
        ])
        source_files = {
            item["evidence_type"]: item["path"]
            for item in evidence
            if item["evidence_type"] in {"mechanical-step", "mechanical-dxf"}
        }
        power = deepcopy(facts.get("supply_v") or facts.get("motor_supply_v") or {})
        power["status"] = "confirmed" if power else "unknown"
        modules.append({
            "hardware_id": hardware_id,
            "catalog_id": CATALOG_IDS[hardware_id],
            "display_name": DISPLAY_NAMES[hardware_id],
            "source_name": source["模块名称"],
            "purpose": PURPOSES[hardware_id],
            "io_role": IO_ROLES[category],
            "category": category,
            "aliases": list(dict.fromkeys([source["模块名称"], DISPLAY_NAMES[hardware_id], hardware_id])),
            "interface": deepcopy(facts.get("interface") or {"type": "unknown"}),
            "power": power,
            "confirmed_wiring": deepcopy(DIRECT_WIRING.get(hardware_id, [])),
            "unknowns": _unknowns(facts, hardware_id),
            "example_capabilities": EXAMPLE_CAPABILITIES[hardware_id],
            "constraints": deepcopy(facts.get("notes") or []),
            "mechanical": {
                "outline": {"width_mm": source["二维外形宽_mm"], "height_mm": source["二维外形高_mm"]},
                "mounting_status": mech.get("mounting", {}).get("status", "unknown"),
                "mounting": deepcopy(mech.get("mounting", {})),
                "panel_features": deepcopy(mech.get("panel_features")),
                "source_files": source_files,
                "physical_fit": "unverified",
            },
            "evidence_status": facts.get("verification_status", "partial"),
            "usability": USABILITY.get(hardware_id, "teacher_validation"),
            "source_evidence": evidence,
        })
    manifest = {
        "schema_version": "1.0",
        "id": SOURCE_ID,
        "source_package": {
            "archive_date": "2026-07-25",
            "module_index": "03_归档索引/自研模块索引.json",
            "full_file_index": "03_归档索引/全文件清单.csv",
            "raw_material_root": "02_自研硬件资料/01自研硬件资料",
            "curation_inputs": [
                {
                    "path": "04_Skill开发/starcore-project-maker/assets/hardware/module_catalog.json",
                    "sha256": _sha256(legacy_catalog),
                    "role": "reviewed extraction seed; raw evidence paths and conflicts remain authoritative",
                },
                {
                    "path": "04_Skill开发/starcore-project-maker/assets/hardware/mechanical_profiles.json",
                    "sha256": _sha256(legacy_mechanics),
                    "role": "reviewed mechanical extraction seed; physical fit remains unverified",
                },
            ],
            "boundary": "Runtime keeps only curated facts, evidence paths, and hashes; raw binaries stay in the handoff archive.",
        },
        "module_count": 23,
        "modules": modules,
    }
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> None:
    schema = _read_yaml(SCHEMA_PATH)
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda item: list(item.path))
    if errors:
        raise ValueError("manifest_schema_invalid:" + ";".join(error.message for error in errors))
    ids = [item["hardware_id"] for item in manifest["modules"]]
    catalog_ids = [item["catalog_id"] for item in manifest["modules"]]
    if len(ids) != len(set(ids)) or len(catalog_ids) != len(set(catalog_ids)):
        raise ValueError("manifest_duplicate_identity")
    if set(ids) != set(CATALOG_IDS):
        raise ValueError("manifest_module_set_mismatch")


def _gate(status: str = "unverified", *, evidence: str | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "checked_at": CHECKED_AT if status in {"verified", "failed"} else None,
        "evidence": evidence,
    }


def _runtime_profile(module: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_id": module["catalog_id"],
        "hardware_id": module["hardware_id"],
        "display_name": module["display_name"],
        "purpose": module["purpose"],
        "io_role": module["io_role"],
        "interface": module["interface"],
        "power": module["power"],
        "confirmed_wiring": module["confirmed_wiring"],
        "unknowns": module["unknowns"],
        "example_capabilities": module["example_capabilities"],
        "mechanical": module["mechanical"],
        "evidence_status": module["evidence_status"],
        "usability": module["usability"],
        "source_ref": SOURCE_ID,
        "source_evidence": module["source_evidence"],
    }


def _generic_component(module: dict[str, Any]) -> dict[str, Any]:
    interface = module["interface"]
    signals = list(interface.get("signals") or [])
    if not signals:
        signals = ["CONNECTION"]
    power = module["power"]
    minimum = power.get("min", power.get("minimum", power.get("nominal")))
    maximum = power.get("max", power.get("maximum", power.get("nominal")))
    usability = module["usability"]
    code_status = "not_applicable" if usability == "retrieval_only" else "unverified"
    constraints = list(module.get("constraints") or [])
    constraints.extend(module["unknowns"])
    if not constraints:
        constraints.append("Only use source-confirmed voltage, interface, and pin assignments; keep unknown values unassigned.")
    libraries: list[dict[str, Any]] = []
    return {
        "schema_version": "1.0",
        "kind": "component",
        "id": module["catalog_id"],
        "hardware_id": module["hardware_id"],
        "name": module["display_name"],
        "aliases": module["aliases"],
        "category": module["category"],
        "interface": str(interface.get("type", "unknown")).replace("_", "-"),
        "supply_voltage": {"minimum": minimum, "maximum": maximum, "status": power["status"]},
        "logic_boundary": constraints[0],
        "source_ids": [SOURCE_ID],
        "sources": [{"title": "ChatMaker self-developed hardware source manifest", "url": SOURCE_URL}],
        "verification": {
            "source_reviewed": _gate("verified", evidence="The 2026-07-25 handoff index and selected raw source files were reviewed; unresolved fields remain explicit."),
            "code_compiled": _gate(code_status),
            "firmware_uploaded": _gate("not_applicable" if usability == "retrieval_only" else "unverified"),
            "physical_effect_verified": _gate("unverified"),
        },
        "pins": [{"id": str(signal), "role": "source-labelled-signal" if signal != "CONNECTION" else "connector-details-require-source-review"} for signal in signals],
        "supported_boards": [BOARD_ID],
        "constraints": constraints,
        "identification": [f"Confirm the {module['hardware_id']} marking and the beginner name '{module['display_name']}' before applying this record."],
        "libraries": libraries,
        "example_files": [GUIDE_PATH],
        "common_failures": ["Substituting a similarly named generic module can change voltage, pin order, active level, dimensions, or protocol."],
        "board_notes": {BOARD_ID: "Use module_guide or project_task before assigning pins; unknown and conflicting fields are generation blockers."},
    }


def _update_existing_name(path: Path, display_name: str, *, check: bool) -> bool:
    record = _read_yaml(path)
    if record.get("name") == display_name:
        return False
    if check:
        raise ValueError(f"runtime_record_out_of_date:{path.relative_to(ROOT).as_posix()}")
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("name:"):
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            lines[index] = f"name: {display_name}{newline}"
            path.write_text("".join(lines), encoding="utf-8", newline="")
            return True
    raise ValueError(f"runtime_record_name_missing:{path.relative_to(ROOT).as_posix()}")


def sync_runtime(manifest: dict[str, Any], *, check: bool = False) -> list[Path]:
    validate_manifest(manifest)
    changed: list[Path] = []
    runtime_index = {
        "schema_version": "1.0",
        "source_ref": SOURCE_ID,
        "module_count": len(manifest["modules"]),
        "modules": [_runtime_profile(module) for module in manifest["modules"]],
    }
    runtime_text = yaml.safe_dump(runtime_index, allow_unicode=True, sort_keys=False, width=120)
    if not RUNTIME_INDEX_PATH.is_file() or RUNTIME_INDEX_PATH.read_text(encoding="utf-8") != runtime_text:
        if check:
            raise ValueError("runtime_record_out_of_date:knowledge/hardware/self-developed-modules.yaml")
        RUNTIME_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_INDEX_PATH.write_text(runtime_text, encoding="utf-8")
        changed.append(RUNTIME_INDEX_PATH)
    for module in manifest["modules"]:
        path: Path
        if module["hardware_id"] == "IDMC-0001":
            path = ROOT / "packs/boards" / f"{module['catalog_id']}.yaml"
            if _update_existing_name(path, module["display_name"], check=check):
                changed.append(path)
            continue
        else:
            path = ROOT / "packs/components" / f"{module['catalog_id']}.yaml"
            if path.is_file():
                existing = _read_yaml(path)
                if existing.get("source_ids") != [SOURCE_ID]:
                    if _update_existing_name(path, module["display_name"], check=check):
                        changed.append(path)
                    continue
            record = _generic_component(module)
        expected = yaml.safe_dump(record, allow_unicode=True, sort_keys=False, width=120)
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            if check:
                raise ValueError(f"runtime_record_out_of_date:{path.relative_to(ROOT).as_posix()}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
            changed.append(path)
    return changed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, help="Handoff root containing 03_归档索引 and 02_自研硬件资料")
    parser.add_argument("--legacy-catalog", type=Path, help="Reviewed module_catalog.json used as a curation input")
    parser.add_argument("--legacy-mechanics", type=Path, help="Reviewed mechanical_profiles.json used as a curation input")
    parser.add_argument("--check", action="store_true", help="Validate the checked-in manifest without writing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.source_root:
            if not args.legacy_catalog or not args.legacy_mechanics:
                raise ValueError("legacy_catalog_and_mechanics_required_for_import")
            manifest = import_manifest(args.source_root.resolve(), args.legacy_catalog.resolve(), args.legacy_mechanics.resolve())
            if args.check:
                checked_in = _read_yaml(MANIFEST_PATH)
                if checked_in != manifest:
                    raise ValueError("self_developed_hardware_manifest_out_of_date")
            else:
                _write_yaml(MANIFEST_PATH, manifest)
        else:
            manifest = _read_yaml(MANIFEST_PATH)
            validate_manifest(manifest)
        changed = sync_runtime(manifest, check=args.check)
        print(json.dumps({"success": True, "module_count": len(manifest["modules"]), "changed": [str(path.relative_to(ROOT)) for path in changed], "checked": args.check}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"success": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

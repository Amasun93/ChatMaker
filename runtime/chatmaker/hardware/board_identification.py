from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import time
from typing import Any, Callable

from . import nano_mindplus as shared


STARCORE_BOARD_ID = "idmc-0001-starcore-v4-2-2"
MPYTHON_CLASSIC_BOARD_ID = "mpython-classic-v2x"
MPYTHON_V3_BOARD_ID = "mpython-v3"
SUPPORTED_BOARD_IDS = (
    STARCORE_BOARD_ID,
    MPYTHON_CLASSIC_BOARD_ID,
    MPYTHON_V3_BOARD_ID,
)
_CHIP_PATTERN = re.compile(r"Chip is\s+(ESP32-S3|ESP32)(?:\b|[^A-Za-z0-9-])", re.IGNORECASE)
_FLASH_SIZE_PATTERN = re.compile(r"Detected flash size:\s*(\d+)\s*(KB|MB)", re.IGNORECASE)
_FIRMWARE_MARKER_PATTERN = re.compile(
    r"CHATMAKER_BOARD_ID:([a-z0-9][a-z0-9-]+)", re.IGNORECASE
)


@dataclass(frozen=True)
class BoardEvidence:
    port: str | None = None
    usb_labels: tuple[str, ...] = ()
    chip_family: str | None = None
    firmware_board_id: str | None = None
    probe_devices: tuple[str, ...] = ()
    silkscreen_text: tuple[str, ...] = ()
    temporary_probe_used: bool = False
    restore_verified: bool | None = None
    backup_path: str | None = None


@dataclass(frozen=True)
class IdentificationResult:
    status: str
    board_id: str | None
    candidates: tuple[str, ...]
    revision: str | None = None
    reasons: tuple[str, ...] = ()
    needs_temporary_probe: bool = False
    needs_photo: bool = False
    backup_path: str | None = None


def _text(values: tuple[str, ...]) -> str:
    return " ".join(values).casefold()


def _confirmed(
    board_id: str,
    *reasons: str,
    revision: str | None = None,
    backup_path: str | None = None,
) -> IdentificationResult:
    return IdentificationResult(
        status="confirmed",
        board_id=board_id,
        candidates=(board_id,),
        revision=revision,
        reasons=tuple(reasons),
        backup_path=backup_path,
    )


def classify_evidence(evidence: BoardEvidence) -> IdentificationResult:
    if evidence.temporary_probe_used and evidence.restore_verified is not True:
        return IdentificationResult(
            status="recovery-required",
            board_id=None,
            candidates=(),
            reasons=("临时识别程序运行后，原程序恢复尚未得到验证。",),
            backup_path=evidence.backup_path,
        )

    if evidence.firmware_board_id in SUPPORTED_BOARD_IDS:
        return _confirmed(
            str(evidence.firmware_board_id),
            "读取到 ChatMaker 固件提供的精确板卡身份。",
            backup_path=evidence.backup_path,
        )

    silk = _text(evidence.silkscreen_text)
    if "星核板" in silk and ("v4.2.2" in silk or "4.2.2" in silk):
        return _confirmed(
            STARCORE_BOARD_ID,
            "正反面丝印同时给出了星核板名称和 v4.2.2 版本。",
            revision="v4.2.2",
            backup_path=evidence.backup_path,
        )
    if "掌控板" in silk and ("3.0" in silk or "v3" in silk):
        return _confirmed(
            MPYTHON_V3_BOARD_ID,
            "丝印明确标注掌控板 3.0。",
            revision="3.0",
            backup_path=evidence.backup_path,
        )
    if "掌控板" in silk and any(value in silk for value in ("v2.0", "v2.1", "v2.2", "v2.3")):
        revision = next(
            value.upper()
            for value in ("v2.0", "v2.1", "v2.2", "v2.3")
            if value in silk
        )
        return _confirmed(
            MPYTHON_CLASSIC_BOARD_ID,
            "丝印明确标注经典掌控板和 V2.x 版本。",
            revision=revision,
            backup_path=evidence.backup_path,
        )

    devices = {value.casefold() for value in evidence.probe_devices}
    chip = (evidence.chip_family or "").casefold().replace("_", "-")

    if chip == "esp32-s3":
        v3_signature = {"qmi8658c", "mmc5603nj", "ltr-308als-01", "st7789"}
        if v3_signature.issubset(devices):
            return _confirmed(
                MPYTHON_V3_BOARD_ID,
                "读取到 ESP32-S3 和掌控板 3.0 的完整板载器件组合。",
                revision="3.0",
                backup_path=evidence.backup_path,
            )
        return IdentificationResult(
            status="probable",
            board_id=None,
            candidates=(MPYTHON_V3_BOARD_ID,),
            reasons=("读取到 ESP32-S3，但还缺少足够的板载器件证据。",),
            needs_temporary_probe=not evidence.temporary_probe_used,
            needs_photo=True,
            backup_path=evidence.backup_path,
        )

    if chip == "esp32":
        if {"msa300", "mmc5983ma", "oled-0x3c"}.issubset(devices):
            return _confirmed(
                MPYTHON_CLASSIC_BOARD_ID,
                "读取到经典掌控板 V2.0 的运动、磁场和屏幕组合。",
                revision="V2.0",
                backup_path=evidence.backup_path,
            )
        if {"qmi8658c", "mmc5983ma", "oled-0x3c"}.issubset(devices):
            return _confirmed(
                MPYTHON_CLASSIC_BOARD_ID,
                "读取到经典掌控板 V2.1 的运动、磁场和屏幕组合。",
                revision="V2.1",
                backup_path=evidence.backup_path,
            )
        if {"qmi8658c", "mmc5603nj", "oled-0x3c"}.issubset(devices):
            return _confirmed(
                MPYTHON_CLASSIC_BOARD_ID,
                "读取到经典掌控板 V2.2 或更新版本的板载器件组合。",
                revision="V2.2+",
                backup_path=evidence.backup_path,
            )
        if {"qmi8658c", "starcore-can-transceiver"}.issubset(devices):
            return _confirmed(
                STARCORE_BOARD_ID,
                "读取到星核板的运动传感器和板载 CAN 特征组合。",
                revision="v4.2.2",
                backup_path=evidence.backup_path,
            )
        return IdentificationResult(
            status="ambiguous",
            board_id=None,
            candidates=(STARCORE_BOARD_ID, MPYTHON_CLASSIC_BOARD_ID),
            reasons=("ESP32、常见串口芯片或 QMI8658 可能同时出现在两种板卡上。",),
            needs_temporary_probe=not evidence.temporary_probe_used,
            needs_photo=True,
            backup_path=evidence.backup_path,
        )

    if any(
        (
            evidence.port,
            evidence.usb_labels,
            evidence.firmware_board_id,
            evidence.probe_devices,
            evidence.silkscreen_text,
        )
    ):
        return IdentificationResult(
            status="ambiguous",
            board_id=None,
            candidates=SUPPORTED_BOARD_IDS,
            reasons=("已发现硬件线索，但还不足以安全确认板卡。",),
            needs_temporary_probe=not evidence.temporary_probe_used,
            needs_photo=True,
            backup_path=evidence.backup_path,
        )

    return IdentificationResult(
        status="unavailable",
        board_id=None,
        candidates=(),
        reasons=("没有发现已连接的有线主控板。",),
    )


def beginner_next_step(result: IdentificationResult) -> str:
    if result.status == "confirmed" and result.board_id:
        names = {
            STARCORE_BOARD_ID: "星核板 v4.2.2",
            MPYTHON_CLASSIC_BOARD_ID: "经典掌控板 V2.x",
            MPYTHON_V3_BOARD_ID: "掌控板 3.0",
        }
        revision = f"（{result.revision}）" if result.revision else ""
        return f"我已经识别出这是{names[result.board_id]}{revision}，可以继续为它开发。"
    if result.status == "recovery-required":
        location = f"，备份保存在 {result.backup_path}" if result.backup_path else ""
        return f"识别过程中原程序还没有确认恢复成功{location}。请先不要断开板子，我来继续恢复。"
    if result.status == "unavailable":
        return "我还没有发现主控板。请用能传数据的 USB 线接上板子，然后告诉我继续。"
    return (
        "我找到了板子，但还不能安全区分具体型号。请先看看正面或背面是否印有“星核板”、"
        "“掌控板”、版本号或 3.0；如果还是看不明白，请拍一张正面和一张背面照片，我来帮你识别。"
    )


def _esptool_candidates() -> list[Path]:
    paths: list[Path] = []
    for installation in shared.discover_installations():
        root = Path(str(installation.get("root", ""))) / "Arduino" / "hardware" / "tools"
        paths.extend(
            [
                root / "esp32s3" / "esptool" / "esptool.exe",
                root / "mpython" / "esptool.exe",
            ]
        )
    local = Path.home() / "AppData" / "Local" / "mind+" / "Arduino" / "packages"
    paths.extend(sorted(local.glob("**/esptool.exe"), reverse=True))
    unique: list[Path] = []
    for path in paths:
        if path.is_file() and path not in unique:
            unique.append(path)
    return unique


def inspect_chip_family(port: str) -> dict[str, Any]:
    candidates = _esptool_candidates()
    if not candidates:
        return {"success": False, "error": "esptool-not-found"}
    last_execution: dict[str, Any] | None = None
    for tool in candidates:
        execution = shared._run(
            [
                str(tool),
                "--chip", "auto",
                "--port", port,
                "--baud", "115200",
                "--before", "default_reset",
                "--after", "hard_reset",
                "flash_id",
            ],
            timeout=45,
        )
        last_execution = execution
        if execution.get("returncode") != 0:
            continue
        text = "\n".join(str(execution.get(key, "")) for key in ("stdout", "stderr"))
        chip_match = _CHIP_PATTERN.search(text)
        size_match = _FLASH_SIZE_PATTERN.search(text)
        if chip_match is None:
            continue
        chip = chip_match.group(1).casefold()
        flash_size = None
        if size_match is not None:
            multiplier = 1024 if size_match.group(2).upper() == "KB" else 1024 * 1024
            flash_size = int(size_match.group(1)) * multiplier
        return {
            "success": True,
            "chip_family": chip,
            "flash_size": flash_size,
            "tool": str(tool),
            "execution": execution,
        }
    return {
        "success": False,
        "error": "connected-chip-not-readable",
        "execution": last_execution,
    }


def read_firmware_marker(port: str, *, timeout: float = 1.5) -> str | None:
    try:
        import serial

        handle = serial.Serial(port=port, baudrate=115200, timeout=0.2)
    except Exception:
        return None
    deadline = time.monotonic() + max(0.2, min(float(timeout), 3.0))
    try:
        while time.monotonic() < deadline:
            raw = handle.readline()
            if not raw:
                continue
            match = _FIRMWARE_MARKER_PATTERN.search(
                raw.decode("utf-8", errors="replace")
            )
            if match and match.group(1) in SUPPORTED_BOARD_IDS:
                return match.group(1)
    except OSError:
        return None
    finally:
        handle.close()
    return None


def _selected_port(
    request: dict[str, Any], ports: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, str | None]:
    eligible = [item for item in ports if item.get("eligible_for_upload")]
    requested = str(request.get("port", "")).upper()
    if requested:
        item = next(
            (row for row in eligible if str(row.get("address", "")).upper() == requested),
            None,
        )
        return item, None if item else "requested-wired-port-not-found"
    if len(eligible) == 1:
        return eligible[0], None
    if not eligible:
        return None, "no-wired-board-found"
    return None, "multiple-wired-ports-require-selection"


def execute_request(
    request: dict[str, Any],
    *,
    port_provider: Callable[[], list[dict[str, Any]]] = shared.scan_ports,
    chip_inspector: Callable[[str], dict[str, Any]] = inspect_chip_family,
    marker_reader: Callable[[str], str | None] = read_firmware_marker,
    probe_runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if request.get("action") != "identify":
        return {"success": False, "error": "action-must-be-identify"}
    ports = port_provider()
    selected, selection_error = _selected_port(request, ports)
    if selected is None:
        if selection_error == "no-wired-board-found":
            result = classify_evidence(BoardEvidence())
            message = beginner_next_step(result)
        else:
            result = IdentificationResult(
                status="ambiguous",
                board_id=None,
                candidates=SUPPORTED_BOARD_IDS,
                reasons=("检测到多块有线设备，需要先选择正在使用的板子。",),
                needs_photo=False,
            )
            message = "我发现了不止一块有线设备。请只保留要开发的那块板子，或告诉我它对应哪个端口。"
        return {
            "success": False,
            "action": "identify",
            "error": selection_error,
            "ports": ports,
            "identification": asdict(result),
            "beginner_message": message,
        }

    port = str(selected["address"]).upper()
    marker = marker_reader(port)
    usb_labels = tuple(
        str(value)
        for value in (
            selected.get("label"),
            selected.get("device_name"),
            selected.get("pnp_device_id"),
        )
        if value
    )
    if marker:
        result = classify_evidence(
            BoardEvidence(port=port, usb_labels=usb_labels, firmware_board_id=marker)
        )
        return {
            "success": True,
            "action": "identify",
            "port": port,
            "identification": asdict(result),
            "beginner_message": beginner_next_step(result),
        }

    chip = chip_inspector(port)
    if not chip.get("success"):
        result = IdentificationResult(
            status="ambiguous",
            board_id=None,
            candidates=SUPPORTED_BOARD_IDS,
            reasons=("板卡已连接，但当前工具没有读出足够身份信息。",),
            needs_photo=True,
        )
        return {
            "success": False,
            "action": "identify",
            "error": chip.get("error", "chip-inspection-failed"),
            "port": port,
            "identification": asdict(result),
            "beginner_message": beginner_next_step(result),
        }

    evidence = BoardEvidence(
        port=port,
        usb_labels=usb_labels,
        chip_family=str(chip.get("chip_family", "")),
    )
    result = classify_evidence(evidence)
    if (
        request.get("allow_temporary_firmware") is True
        and result.needs_temporary_probe
        and evidence.chip_family.casefold() == "esp32"
    ):
        if probe_runner is None:
            from .temporary_probe import MindPlusEsp32ProbeAdapter, run_temporary_probe

            adapter = MindPlusEsp32ProbeAdapter()
            probe_runner = lambda probe_request: run_temporary_probe(probe_request, adapter)
        return probe_runner({**request, "port": port, "action": "identify"})

    return {
        "success": result.status == "confirmed",
        "action": "identify",
        "port": port,
        "chip": {
            "family": chip.get("chip_family"),
            "flash_size": chip.get("flash_size"),
        },
        "identification": asdict(result),
        "beginner_message": beginner_next_step(result),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Identify a connected ChatMaker board.")
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request_json)
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        result = execute_request(request)
    except Exception as exc:
        result = {
            "success": False,
            "error": "board-identification-request-failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("error") == "board-identification-request-failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

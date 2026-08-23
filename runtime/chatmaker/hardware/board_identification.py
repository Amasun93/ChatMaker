from __future__ import annotations

from dataclasses import dataclass


STARCORE_BOARD_ID = "idmc-0001-starcore-v4-2-2"
MPYTHON_CLASSIC_BOARD_ID = "mpython-classic-v2x"
MPYTHON_V3_BOARD_ID = "mpython-v3"
SUPPORTED_BOARD_IDS = (
    STARCORE_BOARD_ID,
    MPYTHON_CLASSIC_BOARD_ID,
    MPYTHON_V3_BOARD_ID,
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


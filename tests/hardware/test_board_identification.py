from __future__ import annotations

from chatmaker.hardware.board_identification import (
    BoardEvidence,
    beginner_next_step,
    classify_evidence,
    execute_request,
)
from pathlib import Path


STARCORE = "idmc-0001-starcore-v4-2-2"
CLASSIC = "mpython-classic-v2x"
V3 = "mpython-v3"
ROOT = Path(__file__).resolve().parents[2]


def test_exact_chatmaker_marker_confirms_starcore_without_guessing_from_usb():
    result = classify_evidence(
        BoardEvidence(
            usb_labels=("CH9102F",),
            chip_family="esp32",
            firmware_board_id=STARCORE,
        )
    )

    assert result.status == "confirmed"
    assert result.board_id == STARCORE
    assert result.candidates == (STARCORE,)


def test_verified_v3_device_combination_confirms_mpython_v3():
    result = classify_evidence(
        BoardEvidence(
            chip_family="esp32-s3",
            probe_devices=("qmi8658c", "mmc5603nj", "ltr-308als-01", "st7789"),
            temporary_probe_used=True,
            restore_verified=True,
        )
    )

    assert result.status == "confirmed"
    assert result.board_id == V3
    assert "ESP32-S3" in " ".join(result.reasons)


def test_classic_msa300_signature_reports_v20_revision():
    result = classify_evidence(
        BoardEvidence(
            chip_family="esp32",
            probe_devices=("msa300", "mmc5983ma", "oled-0x3c"),
            temporary_probe_used=True,
            restore_verified=True,
        )
    )

    assert result.status == "confirmed"
    assert result.board_id == CLASSIC
    assert result.revision == "V2.0"


def test_classic_qmi_and_new_magnetometer_reports_v22_or_later():
    result = classify_evidence(
        BoardEvidence(
            chip_family="esp32",
            probe_devices=("qmi8658c", "mmc5603nj", "oled-0x3c"),
            temporary_probe_used=True,
            restore_verified=True,
        )
    )

    assert result.status == "confirmed"
    assert result.board_id == CLASSIC
    assert result.revision == "V2.2+"


def test_overlapping_qmi_and_ch9102_evidence_keeps_starcore_and_classic_ambiguous():
    result = classify_evidence(
        BoardEvidence(
            usb_labels=("USB-Enhanced-SERIAL CH9102",),
            chip_family="esp32",
            probe_devices=("qmi8658c",),
        )
    )

    assert result.status == "ambiguous"
    assert result.board_id is None
    assert result.candidates == (STARCORE, CLASSIC)
    assert result.needs_photo is True


def test_silkscreen_can_confirm_board_when_electronic_evidence_overlaps():
    result = classify_evidence(
        BoardEvidence(
            chip_family="esp32",
            probe_devices=("qmi8658c",),
            silkscreen_text=("星核板", "V4.2.2", "IDEALAB"),
        )
    )

    assert result.status == "confirmed"
    assert result.board_id == STARCORE
    assert result.revision == "v4.2.2"


def test_unverified_restore_blocks_a_confirmed_result_and_preserves_recovery_guidance():
    result = classify_evidence(
        BoardEvidence(
            chip_family="esp32",
            probe_devices=("msa300", "mmc5983ma", "oled-0x3c"),
            temporary_probe_used=True,
            restore_verified=False,
            backup_path="C:/safe-backups/board.bin",
        )
    )

    assert result.status == "recovery-required"
    assert result.board_id is None
    assert result.backup_path == "C:/safe-backups/board.bin"
    assert "恢复" in beginner_next_step(result)


def test_beginner_guidance_asks_where_to_look_then_offers_photo_without_jargon():
    result = classify_evidence(BoardEvidence(chip_family="esp32"))
    message = beginner_next_step(result)

    assert result.status == "ambiguous"
    assert "正面" in message or "背面" in message
    assert "照片" in message
    for jargon in ("VID", "PID", "I2C", "寄存器"):
        assert jargon not in message


def test_no_connected_evidence_gives_one_simple_action():
    result = classify_evidence(BoardEvidence())

    assert result.status == "unavailable"
    assert "USB" in beginner_next_step(result)


def test_starcore_wiki_explains_automatic_detection_without_treating_compatibility_as_identity():
    root = ROOT / "knowledge_sources" / "published" / "boards" / STARCORE
    text = "\n".join(
        (root / name).read_text(encoding="utf-8")
        for name in ("identify-and-safety.md", "toolchains-and-upload.md")
    )

    assert "自动识别" in text
    assert "临时识别程序" in text
    assert "完整备份" in text
    assert "不能" in text and "掌控板" in text


def test_connected_identification_returns_simple_no_hardware_guidance():
    result = execute_request(
        {"action": "identify"},
        port_provider=lambda: [],
    )

    assert result["success"] is False
    assert result["identification"]["status"] == "unavailable"
    assert "USB" in result["beginner_message"]


def test_connected_s3_without_probe_toolchain_is_a_photo_fallback_not_a_guess():
    result = execute_request(
        {"action": "identify", "port": "COM8", "allow_temporary_firmware": True},
        port_provider=lambda: [
            {"address": "COM8", "eligible_for_upload": True, "label": "USB Serial"}
        ],
        chip_inspector=lambda port: {
            "success": True,
            "chip_family": "esp32-s3",
            "flash_size": 16 * 1024 * 1024,
        },
        probe_runner=lambda request: (_ for _ in ()).throw(AssertionError("must not flash v3")),
    )

    assert result["success"] is False
    assert result["identification"]["status"] == "probable"
    assert result["identification"]["candidates"] == (V3,)
    assert "照片" in result["beginner_message"]


def test_connected_esp32_uses_allowed_temporary_probe_when_evidence_is_ambiguous():
    captured = []

    def probe(request):
        captured.append(request)
        return {
            "success": True,
            "stage": "complete",
            "identification": {"status": "confirmed", "board_id": CLASSIC},
            "beginner_message": "我已经识别出这是经典掌控板。",
        }

    result = execute_request(
        {"action": "identify", "port": "COM9", "allow_temporary_firmware": True},
        port_provider=lambda: [
            {"address": "COM9", "eligible_for_upload": True, "label": "CH9102"}
        ],
        chip_inspector=lambda port: {
            "success": True,
            "chip_family": "esp32",
            "flash_size": 4 * 1024 * 1024,
        },
        probe_runner=probe,
    )

    assert result["success"] is True
    assert result["identification"]["board_id"] == CLASSIC
    assert captured[0]["port"] == "COM9"
    assert captured[0]["allow_temporary_firmware"] is True

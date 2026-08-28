"""Shared ESP32 flashing helpers for mPython-compatible boards.

Mind+ keeps its 16 px Chinese font in flash at 0x400000.  Its official
uploader first reads four bytes and writes the font only when the ``GUIX``
marker is absent.  ChatMaker mirrors that behavior and keeps the font check,
font write, firmware write, and physical verification as separate evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
from typing import Any, Callable


FONT_ADDRESS = "0x400000"
FONT_MARKER = b"GUIX"
FONT_FILENAME = "Noto_Sans_CJK_SC_Light16.xbf"
FONT_SHA256 = "75f647887f54441d569e17f1310520c322bdf7d2ea555ecededa45c9911bc5be"
MINDPLUS_CORE_VERSION = "0.0.1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_flash_assets(context: dict[str, Any]) -> dict[str, Any]:
    """Resolve only files owned by the selected, already-verified backend."""
    if context.get("arduino"):
        arduino = Path(str(context["arduino"]))
        platform = arduino / "hardware" / "dfrobot" / "mpython"
        esptool = arduino / "hardware" / "tools" / "mpython" / "esptool.exe"
        font = arduino / "fw" / "esp32" / FONT_FILENAME
    else:
        config = Path(str(context.get("config", "")))
        managed_root = Path(str(context["root"])) if context.get("root") else None
        data = managed_root / "data" if managed_root else config.parent
        platform = data / "packages" / "mindplus" / "hardware" / "esp32" / MINDPLUS_CORE_VERSION
        esptool = data / "packages" / "mindplus" / "tools" / "esptool_py" / "2.8" / "esptool.exe"
        if context.get("font_asset"):
            font = Path(str(context["font_asset"]))
        elif managed_root:
            font = managed_root / "firmware" / FONT_FILENAME
        else:
            font = (
                config.parent.parent
                / "download" / "upload" / "devices"
                / "dev-DFRobot-handpyEsp32@0.0.2" / "firmware" / FONT_FILENAME
            )
    assets = {
        "esptool": esptool,
        "boot_app0": platform / "tools" / "partitions" / "boot_app0.bin",
        "bootloader": platform / "tools" / "sdk" / "bin" / "bootloader_dio_80m.bin",
        "font": font,
    }
    missing = [name for name, path in assets.items() if not path.is_file()]
    font_hash_verified = False
    if "font" not in missing:
        try:
            font_hash_verified = _sha256(font) == FONT_SHA256
        except OSError:
            missing.append("font")
    if not font_hash_verified and "font" not in missing:
        missing.append("font")
    return {
        **{name: str(path) for name, path in assets.items()},
        "missing": sorted(set(missing)),
        "font_sha256": FONT_SHA256,
        "font_hash_verified": font_hash_verified,
    }


def font_check_command(
    assets: dict[str, Any], port: str, speed: int, marker_path: Path, *, manual_download_mode: bool,
) -> list[str]:
    before = "no_reset" if manual_download_mode else "default_reset"
    return [
        str(assets["esptool"]),
        "--chip", "esp32", "--port", port, "--baud", str(speed),
        "--before", before, "--after", "no_reset",
        "read_flash", FONT_ADDRESS, "4", str(marker_path),
    ]


def firmware_upload_command(
    assets: dict[str, Any], compiled: dict[str, Any], port: str, speed: int, *,
    manual_download_mode: bool, include_font: bool,
) -> list[str]:
    before = "no_reset" if manual_download_mode else "default_reset"
    command = [
        str(assets["esptool"]),
        "--chip", "esp32", "--port", port, "--baud", str(speed),
        "--before", before, "--after", "hard_reset", "write_flash", "-z",
        "--flash_mode", "dio", "--flash_freq", "80m", "--flash_size", "detect",
        "0xe000", str(assets["boot_app0"]),
        "0x1000", str(assets["bootloader"]),
        "0x10000", str(compiled["application_bin"]),
        "0x8000", str(compiled["partitions_bin"]),
    ]
    if include_font:
        command.extend([FONT_ADDRESS, str(assets["font"])])
    return command


def upload_with_font(
    context: dict[str, Any], request: dict[str, Any], compiled: dict[str, Any], port: str, *,
    fast_speed: int, safe_speed: int, runner: Callable[..., dict[str, Any]],
    diagnostics_for: Callable[[dict[str, Any]], dict[str, Any]], timeout: int,
) -> dict[str, Any]:
    """Check the official font marker, then flash firmware and font if needed."""
    assets = resolve_flash_assets(context)
    if assets["missing"]:
        return {
            "success": False,
            "error": "mpython_flash_assets_missing",
            "upload_executed": False,
            "font_checked": False,
            "font_asset_written": False,
            "missing_assets": assets["missing"],
            "font_sha256": FONT_SHA256,
            "teacher_message": (
                "上传环境缺少经过校验的掌控板中文字库或烧录文件。"
                "请先运行 prepare-environment；不要从不明网盘或代理下载替代文件。"
            ),
        }

    manual = bool(request.get("manual_download_mode"))
    marker_path = Path(tempfile.gettempdir()) / f"chatmaker-mpython-font-{port.casefold()}.ck"
    marker_path.unlink(missing_ok=True)
    font_checks: list[dict[str, Any]] = []
    speed = fast_speed
    fallback_used = False

    check = runner(
        font_check_command(assets, port, speed, marker_path, manual_download_mode=manual),
        timeout=timeout,
    )
    font_checks.append(check)
    diagnostics = diagnostics_for(check)
    if check.get("returncode") != 0 and diagnostics.get("retry_at_115200"):
        speed = safe_speed
        fallback_used = True
        marker_path.unlink(missing_ok=True)
        check = runner(
            font_check_command(assets, port, speed, marker_path, manual_download_mode=manual),
            timeout=timeout,
        )
        font_checks.append(check)
        diagnostics = diagnostics_for(check)
    if check.get("returncode") != 0:
        marker_path.unlink(missing_ok=True)
        return {
            "success": False,
            "error": "font_check_failed",
            "upload_executed": False,
            "font_checked": False,
            "font_asset_written": False,
            "font_check_attempts": font_checks,
            "upload_baud": speed,
            "safe_baud_fallback_used": fallback_used,
            "diagnostics": diagnostics,
        }
    try:
        marker = marker_path.read_bytes()
    except OSError:
        marker = b""
    finally:
        marker_path.unlink(missing_ok=True)
    if len(marker) != 4:
        return {
            "success": False,
            "error": "font_marker_read_failed",
            "upload_executed": False,
            "font_checked": False,
            "font_asset_written": False,
            "font_check_attempts": font_checks,
            "upload_baud": speed,
            "safe_baud_fallback_used": fallback_used,
            "teacher_message": "中文字库检查没有读回 4 字节标记，已停止烧录以避免误报。",
        }

    include_font = marker != FONT_MARKER
    firmware_attempts: list[dict[str, Any]] = []
    execution = runner(
        firmware_upload_command(
            assets, compiled, port, speed,
            manual_download_mode=manual, include_font=include_font,
        ),
        timeout=timeout,
    )
    firmware_attempts.append(execution)
    diagnostics = diagnostics_for(execution)
    if execution.get("returncode") != 0 and diagnostics.get("retry_at_115200") and speed != safe_speed:
        speed = safe_speed
        fallback_used = True
        execution = runner(
            firmware_upload_command(
                assets, compiled, port, speed,
                manual_download_mode=manual, include_font=include_font,
            ),
            timeout=timeout,
        )
        firmware_attempts.append(execution)
        diagnostics = diagnostics_for(execution)
    success = execution.get("returncode") == 0
    return {
        "success": success,
        "upload_executed": True,
        "execution": execution,
        "attempts": firmware_attempts,
        "font_check_attempts": font_checks,
        "font_checked": True,
        "font_marker_present_before_upload": not include_font,
        "font_asset_written": bool(success and include_font),
        "font_sha256": FONT_SHA256,
        "upload_baud": speed,
        "safe_baud_fallback_used": fallback_used,
        **({} if success else {"error": "upload_failed", "diagnostics": diagnostics}),
    }

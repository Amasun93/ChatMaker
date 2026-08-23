from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import time
from typing import Any, Protocol

from .board_identification import BoardEvidence, beginner_next_step, classify_evidence
from . import nano_mindplus as shared
from . import starcore


_FLASH_SIZE_PATTERN = re.compile(r"Detected flash size:\s*(\d+)\s*(KB|MB)", re.IGNORECASE)
_READ_MEM_PATTERN = re.compile(r"=\s*(0x[0-9a-f]+)", re.IGNORECASE)
_REPORT_PREFIX = "CHATMAKER_PROBE:"


def parse_flash_size(text: str) -> int | None:
    match = _FLASH_SIZE_PATTERN.search(text or "")
    if match is None:
        return None
    multiplier = 1024 if match.group(2).upper() == "KB" else 1024 * 1024
    return int(match.group(1)) * multiplier


def parse_read_mem_value(text: str) -> int | None:
    match = _READ_MEM_PATTERN.search(text or "")
    return int(match.group(1), 16) if match is not None else None


def esp32_security_safe(efuse_rdata0: int, efuse_rdata6: int) -> bool:
    flash_crypt_count = (int(efuse_rdata0) >> 20) & 0x7F
    flash_encryption_enabled = flash_crypt_count.bit_count() % 2 == 1
    secure_boot_enabled = bool(int(efuse_rdata6) & ((1 << 4) | (1 << 5)))
    return not flash_encryption_enabled and not secure_boot_enabled


class TemporaryProbeAdapter(Protocol):
    def inspect(self, request: dict[str, Any]) -> dict[str, Any]: ...
    def backup(self, inspection: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]: ...
    def verify_backup(self, backup: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]: ...
    def write_probe(self, inspection: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]: ...
    def read_report(self, inspection: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]: ...
    def restore(self, backup: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]: ...
    def verify_restore(self, backup: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]: ...


class MindPlusEsp32ProbeAdapter:
    """Classic ESP32 probe adapter using the discovered Mind+ 1.8 toolchain."""

    def __init__(self, *, runner=shared._run, port_provider=shared.scan_ports) -> None:
        self.runner = runner
        self.port_provider = port_provider

    @staticmethod
    def _tool(context: dict[str, Any]) -> Path:
        return Path(str(context["arduino"])) / "hardware" / "tools" / "mpython" / "esptool.exe"

    @staticmethod
    def _base(
        tool: Path,
        port: str,
        *,
        after: str = "hard_reset",
        baud: int = 115200,
    ) -> list[str]:
        return [
            str(tool),
            "--chip", "esp32",
            "--port", port,
            "--baud", str(baud),
            "--before", "default_reset",
            "--after", after,
        ]

    @staticmethod
    def _execution_text(execution: dict[str, Any]) -> str:
        return "\n".join(
            str(execution.get(key, "")) for key in ("stdout", "stderr")
        )

    def _select_port(self, request: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        ports = [item for item in self.port_provider() if item.get("eligible_for_upload")]
        requested = str(request.get("port", "")).upper()
        if requested:
            selected = next(
                (item for item in ports if str(item.get("address", "")).upper() == requested),
                None,
            )
            return selected, None if selected else "upload-port-not-eligible"
        if len(ports) == 1:
            return ports[0], None
        if not ports:
            return None, "no-wired-board-found"
        return None, "multiple-wired-ports-require-selection"

    def inspect(self, request: dict[str, Any]) -> dict[str, Any]:
        selected, error = self._select_port(request)
        if selected is None:
            return {"success": False, "error": error}
        context = starcore._current_context()
        if context is None:
            return {"success": False, "error": "mindplus-1.8-mpython-toolchain-missing"}
        tool = self._tool(context)
        if not tool.is_file():
            return {"success": False, "error": "esptool-missing"}

        port = str(selected["address"]).upper()
        flash_execution = self.runner(self._base(tool, port) + ["flash_id"], timeout=45)
        if flash_execution.get("returncode") != 0:
            return {"success": False, "error": "esp32-flash-inspection-failed", "execution": flash_execution}
        flash_size = parse_flash_size(self._execution_text(flash_execution))

        efuse_values: list[int | None] = []
        for address in ("0x3ff5a000", "0x3ff5a018"):
            execution = self.runner(
                self._base(tool, port) + ["read_mem", address], timeout=45
            )
            efuse_values.append(
                parse_read_mem_value(self._execution_text(execution))
                if execution.get("returncode") == 0
                else None
            )
        security_safe = (
            None not in efuse_values
            and esp32_security_safe(int(efuse_values[0]), int(efuse_values[1]))
        )
        return {
            "success": flash_size is not None,
            "error": None if flash_size is not None else "flash-size-not-detected",
            "port": port,
            "chip_family": "esp32",
            "flash_size": flash_size,
            "security_safe": security_safe,
            "security_evidence": {
                "efuse_rdata0": efuse_values[0],
                "efuse_rdata6": efuse_values[1],
            },
            "toolchain": "mindplus-1.8-mpython",
            "context": context,
            "usb_labels": tuple(
                value
                for value in (
                    selected.get("label"),
                    selected.get("device_name"),
                    selected.get("pnp_device_id"),
                )
                if value
            ),
        }

    def backup(self, inspection: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        flash_size = int(inspection["flash_size"])
        backup_root = Path(
            request.get("backup_dir")
            or Path.home() / "ChatMakerBackups" / "board-identification"
        ).expanduser().resolve()
        backup_root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(backup_root).free < flash_size * 2:
            return {"success": False, "error": "insufficient-backup-space"}
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe_port = re.sub(r"[^A-Za-z0-9_-]", "-", str(inspection["port"]))
        final_path = backup_root / f"{stamp}-{safe_port}-original-flash.bin"
        partial_path = final_path.with_suffix(".bin.part")
        tool = self._tool(inspection["context"])
        execution = self.runner(
            self._base(tool, str(inspection["port"]), baud=460800)
            + ["read_flash", "0x0", hex(flash_size), str(partial_path)],
            timeout=int(request.get("backup_timeout", 900)),
        )
        if execution.get("returncode") != 0 or not partial_path.is_file():
            partial_path.unlink(missing_ok=True)
            return {"success": False, "error": "full-flash-backup-failed", "execution": execution}
        partial_path.replace(final_path)
        return {
            "success": True,
            "path": str(final_path),
            "size": final_path.stat().st_size,
            "baud": 460800,
            "execution": execution,
        }

    def verify_backup(self, backup: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(backup.get("path", "")))
        if not path.is_file():
            return {"success": False, "error": "backup-file-missing"}
        size = path.stat().st_size
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = int(inspection["flash_size"])
        return {
            "success": size == expected,
            "error": None if size == expected else "backup-size-mismatch",
            "size": size,
            "sha256": digest,
            "full_flash": size == expected,
        }

    def write_probe(self, inspection: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        root = Path(__file__).resolve().parents[3]
        sketch = root / "examples" / "chatduino" / "board-identification" / "esp32-mpython-probe"
        compiled = starcore.compile_result(
            inspection["context"],
            {
                "sketch": str(sketch),
                "timeout": int(request.get("compile_timeout", 900)),
            },
        )
        if not compiled.get("success"):
            return {"success": False, "error": "probe-compile-failed", "compile": compiled}
        uploaded = starcore.upload_result(
            inspection["context"],
            {
                "board_confirmed": True,
                "port": inspection["port"],
                "upload_timeout": int(request.get("upload_timeout", 300)),
            },
            compiled,
        )
        return {
            "success": bool(uploaded.get("success")),
            "error": None if uploaded.get("success") else "probe-upload-failed",
            "firmware_written": bool(uploaded.get("success")),
            "compile": compiled,
            "upload": uploaded,
        }

    def read_report(self, inspection: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        try:
            import serial

            handle = serial.Serial(
                port=str(inspection["port"]),
                baudrate=115200,
                timeout=0.2,
            )
        except Exception as exc:
            return {"success": False, "error": f"probe-serial-open-failed:{type(exc).__name__}"}
        deadline = time.monotonic() + max(1.0, min(float(request.get("report_timeout", 12)), 30.0))
        lines: list[str] = []
        try:
            while time.monotonic() < deadline:
                raw = handle.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                lines.append(line)
                if line.startswith(_REPORT_PREFIX):
                    payload = json.loads(line[len(_REPORT_PREFIX):])
                    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
                        return {"success": False, "error": "probe-report-invalid", "lines": lines}
                    return {"success": True, **payload, "lines": lines}
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {"success": False, "error": f"probe-report-read-failed:{type(exc).__name__}", "lines": lines}
        finally:
            handle.close()
        return {"success": False, "error": "probe-report-timeout", "lines": lines}

    def restore(self, backup: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]:
        tool = self._tool(inspection["context"])
        execution = self.runner(
            self._base(tool, str(inspection["port"]))
            + ["write_flash", "-z", "--flash_size", "detect", "0x0", str(backup["path"])],
            timeout=900,
        )
        return {
            "success": execution.get("returncode") == 0,
            "error": None if execution.get("returncode") == 0 else "original-flash-restore-failed",
            "restored": execution.get("returncode") == 0,
            "execution": execution,
        }

    def verify_restore(self, backup: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]:
        tool = self._tool(inspection["context"])
        execution = self.runner(
            self._base(tool, str(inspection["port"]))
            + ["verify_flash", "0x0", str(backup["path"])],
            timeout=900,
        )
        matches = execution.get("returncode") == 0
        return {
            "success": matches,
            "error": None if matches else "restored-flash-verification-failed",
            "matches_backup": matches,
            "restored_sha256": (
                hashlib.sha256(Path(str(backup["path"])).read_bytes()).hexdigest()
                if matches
                else None
            ),
            "execution": execution,
        }


def _failure(stage: str, result: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "success": False,
        "stage": stage,
        "error": result.get("error", f"{stage}-failed"),
        **extra,
    }


def _verified_full_backup(
    inspection: dict[str, Any],
    backup: dict[str, Any],
    verification: dict[str, Any],
) -> bool:
    expected_size = inspection.get("flash_size")
    return bool(
        verification.get("success")
        and verification.get("full_flash") is True
        and isinstance(expected_size, int)
        and expected_size > 0
        and backup.get("size") == expected_size
        and verification.get("size") == expected_size
        and isinstance(verification.get("sha256"), str)
        and len(verification["sha256"]) == 64
    )


def run_temporary_probe(
    request: dict[str, Any], adapter: TemporaryProbeAdapter
) -> dict[str, Any]:
    if request.get("allow_temporary_firmware") is not True:
        return {
            "success": False,
            "stage": "permission",
            "error": "temporary-firmware-permission-required",
            "beginner_message": "需要运行一次临时识别程序。你允许后我才会备份原程序并继续。",
        }

    try:
        inspection = adapter.inspect(request)
    except Exception as exc:
        return _failure("preflight", {"error": f"inspect-exception:{type(exc).__name__}"})
    if (
        not inspection.get("success")
        or not inspection.get("port")
        or not inspection.get("toolchain")
        or not isinstance(inspection.get("flash_size"), int)
        or inspection.get("flash_size", 0) <= 0
        or inspection.get("security_safe") is not True
    ):
        return _failure(
            "preflight",
            inspection,
            beginner_message=(
                "这块板暂时不适合自动写入识别程序。我会改用板上型号和照片帮助你识别。"
            ),
        )

    try:
        backup = adapter.backup(inspection, request)
    except Exception as exc:
        return _failure("backup", {"error": f"backup-exception:{type(exc).__name__}"})
    if not backup.get("success") or not backup.get("path"):
        return _failure("backup", backup)

    try:
        backup_verification = adapter.verify_backup(backup, inspection)
    except Exception as exc:
        return _failure(
            "backup-verification",
            {"error": f"backup-verification-exception:{type(exc).__name__}"},
            backup_path=backup.get("path"),
        )
    if not _verified_full_backup(inspection, backup, backup_verification):
        return _failure(
            "backup-verification",
            backup_verification,
            backup_path=backup.get("path"),
        )

    write_result: dict[str, Any]
    report_result: dict[str, Any] = {
        "success": False,
        "error": "probe-report-not-read",
    }
    write_attempted = False
    try:
        write_attempted = True
        write_result = adapter.write_probe(inspection, request)
        if write_result.get("success"):
            report_result = adapter.read_report(inspection, request)
    except Exception as exc:
        write_result = {"success": False, "error": f"probe-exception:{type(exc).__name__}"}

    restore_result: dict[str, Any] = {"success": False, "error": "restore-not-attempted"}
    restore_verification: dict[str, Any] = {
        "success": False,
        "error": "restore-verification-not-attempted",
    }
    if write_attempted:
        try:
            restore_result = adapter.restore(backup, inspection)
            if restore_result.get("success"):
                restore_verification = adapter.verify_restore(backup, inspection)
        except Exception as exc:
            restore_result = {"success": False, "error": f"restore-exception:{type(exc).__name__}"}

    restore_verified = bool(
        restore_result.get("success")
        and restore_verification.get("success")
        and restore_verification.get("matches_backup") is True
    )
    if not restore_verified:
        return {
            "success": False,
            "stage": "recovery-required",
            "error": restore_result.get("error") or restore_verification.get("error"),
            "restore_verified": False,
            "backup_path": backup.get("path"),
            "backup_sha256": backup_verification.get("sha256"),
            "beginner_message": (
                "原程序还没有确认恢复成功。请不要断开板子；完整备份已经保留，我会继续帮你恢复。"
            ),
        }

    common = {
        "restore_verified": True,
        "backup_path": backup.get("path"),
        "backup_sha256": backup_verification.get("sha256"),
    }
    if not write_result.get("success"):
        return _failure("probe-write", write_result, **common)
    if not report_result.get("success"):
        return _failure("probe-report", report_result, **common)

    evidence = BoardEvidence(
        port=str(inspection.get("port")),
        usb_labels=tuple(inspection.get("usb_labels", ())),
        chip_family=str(report_result.get("chip_family") or inspection.get("chip_family") or ""),
        firmware_board_id=report_result.get("firmware_board_id"),
        probe_devices=tuple(report_result.get("probe_devices", ())),
        temporary_probe_used=True,
        restore_verified=True,
        backup_path=str(backup.get("path")),
    )
    identification = classify_evidence(evidence)
    return {
        "success": identification.status == "confirmed",
        "stage": "complete" if identification.status == "confirmed" else "identification",
        **common,
        "identification": asdict(identification),
        "beginner_message": beginner_next_step(identification),
    }

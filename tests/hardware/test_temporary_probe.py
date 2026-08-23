from __future__ import annotations

from pathlib import Path

from chatmaker.hardware.temporary_probe import (
    MindPlusEsp32ProbeAdapter,
    esp32_security_safe,
    parse_flash_size,
    parse_read_mem_value,
    run_temporary_probe,
)


class FakeAdapter:
    def __init__(self, *, fail: str | None = None):
        self.fail = fail
        self.calls: list[str] = []

    def _result(self, name: str, success: dict):
        self.calls.append(name)
        if self.fail == name:
            return {"success": False, "error": f"{name}-failed"}
        return {"success": True, **success}

    def inspect(self, request):
        return self._result(
            "inspect",
            {
                "port": request["port"],
                "chip_family": "esp32",
                "flash_size": 4 * 1024 * 1024,
                "security_safe": True,
                "toolchain": "mindplus-1.8-mpython",
            },
        )

    def backup(self, inspection, request):
        return self._result(
            "backup",
            {"path": "C:/safe-backups/original.bin", "size": inspection["flash_size"]},
        )

    def verify_backup(self, backup, inspection):
        return self._result(
            "verify_backup",
            {"sha256": "a" * 64, "size": backup["size"], "full_flash": True},
        )

    def write_probe(self, inspection, request):
        return self._result("write_probe", {"firmware_written": True})

    def read_report(self, inspection, request):
        return self._result(
            "read_report",
            {
                "chip_family": "esp32",
                "probe_devices": ["msa300", "mmc5983ma", "oled-0x3c"],
            },
        )

    def restore(self, backup, inspection):
        return self._result("restore", {"restored": True})

    def verify_restore(self, backup, inspection):
        return self._result(
            "verify_restore",
            {"restored_sha256": "a" * 64, "matches_backup": True},
        )


def request(**values):
    return {"port": "COM7", "allow_temporary_firmware": True, **values}


def test_probe_never_writes_before_full_backup_is_verified():
    adapter = FakeAdapter(fail="verify_backup")

    result = run_temporary_probe(request(), adapter)

    assert result["success"] is False
    assert result["stage"] == "backup-verification"
    assert adapter.calls == ["inspect", "backup", "verify_backup"]
    assert "write_probe" not in adapter.calls


def test_probe_requires_explicit_temporary_firmware_permission():
    adapter = FakeAdapter()

    result = run_temporary_probe(
        request(allow_temporary_firmware=False), adapter
    )

    assert result["stage"] == "permission"
    assert adapter.calls == []


def test_read_failure_still_restores_and_verifies_original_firmware():
    adapter = FakeAdapter(fail="read_report")

    result = run_temporary_probe(request(), adapter)

    assert result["stage"] == "probe-report"
    assert result["restore_verified"] is True
    assert adapter.calls == [
        "inspect",
        "backup",
        "verify_backup",
        "write_probe",
        "read_report",
        "restore",
        "verify_restore",
    ]


def test_restore_failure_blocks_identification_and_preserves_backup_path():
    adapter = FakeAdapter(fail="restore")

    result = run_temporary_probe(request(), adapter)

    assert result["success"] is False
    assert result["stage"] == "recovery-required"
    assert result["restore_verified"] is False
    assert result["backup_path"] == "C:/safe-backups/original.bin"
    assert "不要断开" in result["beginner_message"]
    assert "identification" not in result


def test_restore_verification_failure_is_not_reported_as_success():
    adapter = FakeAdapter(fail="verify_restore")

    result = run_temporary_probe(request(), adapter)

    assert result["success"] is False
    assert result["stage"] == "recovery-required"
    assert result["restore_verified"] is False


def test_successful_probe_restores_first_then_returns_identification():
    adapter = FakeAdapter()

    result = run_temporary_probe(request(), adapter)

    assert result["success"] is True
    assert result["stage"] == "complete"
    assert result["restore_verified"] is True
    assert result["identification"]["board_id"] == "mpython-classic-v2x"
    assert result["identification"]["revision"] == "V2.0"
    assert adapter.calls.index("restore") < len(adapter.calls)
    assert adapter.calls[-1] == "verify_restore"


def test_unsafe_security_or_missing_toolchain_stops_before_backup():
    class UnsafeAdapter(FakeAdapter):
        def inspect(self, request):
            result = super().inspect(request)
            result["security_safe"] = False
            result["error"] = "flash-security-not-supported"
            return result

    adapter = UnsafeAdapter()

    result = run_temporary_probe(request(), adapter)

    assert result["stage"] == "preflight"
    assert adapter.calls == ["inspect"]


def test_mindplus_adapter_parses_flash_size_and_efuse_security_without_guessing():
    assert parse_flash_size("Detected flash size: 4MB") == 4 * 1024 * 1024
    assert parse_flash_size("Detected flash size: 16MB") == 16 * 1024 * 1024
    assert parse_flash_size("no size here") is None
    assert parse_read_mem_value("0x3ff5a000 = 0x00100000") == 0x00100000
    assert parse_read_mem_value("read failed") is None

    assert esp32_security_safe(0, 0) is True
    assert esp32_security_safe(1 << 20, 0) is False
    assert esp32_security_safe(0, 1 << 4) is False


def test_full_flash_backup_uses_460800_baud_by_default(tmp_path):
    commands = []

    def runner(command, timeout):
        commands.append(command)
        Path(command[-1]).write_bytes(b"full-flash")
        return {"returncode": 0, "stdout": "", "stderr": ""}

    adapter = MindPlusEsp32ProbeAdapter(runner=runner)
    adapter._tool = lambda context: Path("esptool.exe")
    result = adapter.backup(
        {
            "flash_size": len(b"full-flash"),
            "port": "COM4",
            "context": {},
        },
        {"backup_dir": str(tmp_path)},
    )

    assert result["success"] is True
    baud_index = commands[0].index("--baud")
    assert commands[0][baud_index + 1] == "460800"

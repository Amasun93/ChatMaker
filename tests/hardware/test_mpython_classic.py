from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from chatmaker.hardware import mpython_classic


ROOT = Path(__file__).resolve().parents[2]


def flash_assets():
    return {
        "esptool": "esptool.exe",
        "boot_app0": "boot_app0.bin",
        "bootloader": "bootloader.bin",
        "font": "font.xbf",
        "missing": [],
        "font_sha256": mpython_classic.mpython_flash.FONT_SHA256,
        "font_hash_verified": True,
    }


class FakeHandle:
    def __init__(self):
        self.dtr = None
        self.rts_values = []
        self.closed = False

    @property
    def rts(self):
        return self.rts_values[-1] if self.rts_values else None

    @rts.setter
    def rts(self, value):
        self.rts_values.append(value)

    def close(self):
        self.closed = True


class FakeSerialManager:
    def __init__(self):
        self.closed = []

    def open(self, port, **options):
        return {"success": True, "session_id": "classic-1", "port": port, **options}

    def read(self, session_id, **options):
        return {
            "success": True,
            "session_id": session_id,
            "lines": ["MPYTHON_CLASSIC_CHINESE_STATUS_READY"],
            "serial_evidence": True,
        }

    def close(self, session_id):
        self.closed.append(session_id)
        return {"success": True, "session_id": session_id}


class MpythonClassicTests(unittest.TestCase):
    def test_identity_and_targets_remain_separate_from_starcore_and_v3(self):
        self.assertEqual(mpython_classic.BOARD_ID, "mpython-classic-v2x")
        self.assertNotIn("starcore", mpython_classic.BOARD_ID)
        self.assertTrue(mpython_classic.V2_FQBN.startswith("mindplus:esp32:mpython:"))
        self.assertTrue(mpython_classic.V1_FQBN.startswith("dfrobot:mpython:mpython:"))

    def test_managed_context_is_preferred_but_reports_classic_backend(self):
        raw = {
            "backend": "chatmaker-managed-starcore",
            "cli": "managed-cli.exe",
            "config": "managed.yaml",
        }
        with (
            mock.patch.object(mpython_classic.managed_mpython, "managed_context", return_value=raw),
            mock.patch.object(mpython_classic.shared, "discover_installations") as discover,
        ):
            selected = mpython_classic._current_context()
        discover.assert_not_called()
        self.assertEqual(selected["backend"], mpython_classic.MANAGED_BACKEND)
        self.assertEqual(selected["artifact_profile"], "mindplus-esp32-0.0.1")
        self.assertEqual(selected["fqbn"], mpython_classic.V2_FQBN)

    def test_compile_command_uses_isolated_config(self):
        context = {
            "backend": mpython_classic.MANAGED_BACKEND,
            "cli": r"C:\ChatMaker\arduino-cli.exe",
            "config": r"C:\ChatMaker\arduino-cli.yaml",
        }
        command = mpython_classic.build_compile_command(context, Path("demo.ino"), Path("build"))
        self.assertIn(mpython_classic.V2_FQBN, command)
        self.assertIn(r"C:\ChatMaker\arduino-cli.yaml", command)

    def test_upload_and_reset_require_exact_board_confirmation(self):
        ports = [{"address": "COM7", "eligible_for_upload": True}]
        with mock.patch.object(mpython_classic, "scan_ports", return_value=ports):
            port, error, _ = mpython_classic._select_port({}, identity_required=True)
            reset = mpython_classic.reset_result({})
        self.assertIsNone(port)
        self.assertEqual(error, "mpython_classic_identity_confirmation_required")
        self.assertFalse(reset["reset_executed"])

    def test_doctor_does_not_call_an_unidentified_port_ready_for_upload(self):
        ports = [{"address": "COM7", "eligible_for_upload": True}]
        context = {"backend": mpython_classic.MANAGED_BACKEND, "fqbn": mpython_classic.V2_FQBN}
        with (
            mock.patch.object(mpython_classic, "scan_ports", return_value=ports),
            mock.patch.object(mpython_classic, "_current_context", return_value=context),
            mock.patch.object(mpython_classic.managed_mpython, "managed_context", return_value=None),
        ):
            result = mpython_classic.doctor_result()
        self.assertFalse(result["ready_for_upload"])
        self.assertEqual(result["upload_blocked_by"], "mpython_classic_identity_confirmation_required")

    def test_upload_retries_at_115200_after_permission_error(self):
        calls = []

        def runner(command, timeout):
            calls.append(command)
            if "read_flash" in command and "1500000" in command:
                return {"returncode": 1, "stdout": "", "stderr": "PermissionError: access denied"}
            if "read_flash" in command:
                Path(command[-1]).write_bytes(b"GUIX")
            return {"returncode": 0, "stdout": "Hash of data verified", "stderr": ""}

        context = {
            "backend": mpython_classic.MANAGED_BACKEND,
            "cli": "arduino-cli.exe",
            "config": "arduino-cli.yaml",
            "fqbn": mpython_classic.V2_FQBN,
        }
        compiled = {"application_bin": "app.bin", "partitions_bin": "partitions.bin"}
        ports = [{"address": "COM7", "eligible_for_upload": True}]
        with (
            mock.patch.object(mpython_classic, "scan_ports", return_value=ports),
            mock.patch.object(mpython_classic.mpython_flash, "resolve_flash_assets", return_value=flash_assets()),
        ):
            result = mpython_classic.upload_result(
                context,
                {"board_confirmed": True},
                compiled,
                runner=runner,
            )

        self.assertTrue(result["success"])
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["upload_baud"], 115200)
        self.assertTrue(result["font_checked"])
        self.assertFalse(result["font_asset_written"])

    def test_reset_toggles_rts_without_claiming_restart_or_effect(self):
        handle = FakeHandle()
        ports = [{"address": "COM7", "eligible_for_upload": True}]
        with (
            mock.patch.object(mpython_classic, "scan_ports", return_value=ports),
            mock.patch.object(mpython_classic.time, "sleep"),
        ):
            result = mpython_classic.reset_result(
                {"board_confirmed": True, "port": "COM7"},
                serial_factory=lambda **kwargs: handle,
            )
        self.assertTrue(result["success"])
        self.assertEqual(handle.rts_values, [True, False])
        self.assertTrue(handle.closed)
        self.assertFalse(result["board_restart_observed"])
        self.assertFalse(result["physical_effect_verified"])

    def test_serial_read_closes_session_and_keeps_effect_unverified(self):
        manager = FakeSerialManager()
        ports = [{"address": "COM7", "eligible_for_upload": True}]
        with mock.patch.object(mpython_classic, "scan_ports", return_value=ports):
            result = mpython_classic.serial_read_result({"port": "COM7"}, manager=manager)
        self.assertTrue(result["serial_evidence"])
        self.assertEqual(manager.closed, ["classic-1"])
        self.assertFalse(result["physical_effect_verified"])

    def test_toolchain_lock_records_hashes_and_license_boundary(self):
        lock = mpython_classic.toolchain_lock()
        self.assertEqual(lock["arduino_cli"]["size"], 14311609)
        self.assertEqual(lock["core"]["size"], 35008313)
        self.assertEqual(len(lock["arduino_cli"]["sha256"]), 64)
        self.assertEqual(len(lock["core"]["sha256"]), 64)
        self.assertEqual(len(lock["libraries"]), 6)
        self.assertIn("GPL-3.0", lock["licenses"]["arduino_cli"])
        self.assertIn("LGPL-2.1", lock["licenses"]["mindplus_esp32_core"])
        self.assertIn("Do not repackage", lock["redistribution_boundary"])

    def test_recipe_has_static_chinese_screen_and_separate_evidence_gates(self):
        recipe = yaml.safe_load(
            (ROOT / "packs/recipes/mpython-classic-chinese-status.yaml").read_text(encoding="utf-8")
        )
        source = (ROOT / recipe["source_file"]).read_text(encoding="utf-8")
        self.assertEqual(recipe["boards"], [mpython_classic.BOARD_ID])
        self.assertIn("掌控板就绪", source)
        loop = source.split("void loop()", 1)[1]
        self.assertNotIn("display.clear", loop)
        self.assertNotIn("display.print", loop)
        for gate in ("firmware_uploaded", "serial_evidence", "power_cycle_verified", "physical_effect_verified"):
            self.assertEqual(recipe["verification"][gate]["status"], "unverified")


if __name__ == "__main__":
    unittest.main()

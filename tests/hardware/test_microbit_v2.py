from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.hardware import microbit_v2


DETAILS_V2 = "# DAPLink Firmware - see https://mbed.com/daplink\nVersion: 0257\nBuild ID: v0257\n"


class MicrobitV2Tests(unittest.TestCase):
    def test_prepare_environment_runs_npm_inside_the_isolated_tool_root(self):
        with tempfile.TemporaryDirectory() as directory:
            tool_root = Path(directory) / "tool"
            base_status = {
                "ready_for_packaging": False,
                "node": "node",
                "npm": "npm",
                "runtime_hex": str(tool_root / "runtime.hex"),
                "runtime_verified": False,
                "microbit_fs_verified": False,
                "tool_root": str(tool_root),
            }
            ready_status = {**base_status, "ready_for_packaging": True, "runtime_verified": True, "microbit_fs_verified": True}
            calls = []

            def downloader(url, destination):
                destination.write_bytes(b"0" * microbit_v2.MICROPYTHON_SIZE)

            def runner(command, *, timeout, cwd):
                calls.append((command, cwd))
                return {"returncode": 0, "stdout": "ok", "stderr": ""}

            with mock.patch.object(
                microbit_v2,
                "_environment_status",
                side_effect=[base_status, base_status, ready_status],
            ), mock.patch.object(
                microbit_v2, "_sha256", return_value=microbit_v2.MICROPYTHON_SHA256
            ):
                result = microbit_v2.prepare_environment_result(
                    tool_root=tool_root, runner=runner, downloader=downloader
                )

        self.assertTrue(result["success"])
        self.assertEqual(calls[0][1], tool_root.resolve())

    def test_source_check_keeps_packaging_separate_from_compilation(self):
        valid = microbit_v2.source_check("from microbit import *\ndisplay.show('中')\n")
        invalid = microbit_v2.source_check("if True print('bad')\n")

        self.assertTrue(valid["source_checked"])
        self.assertFalse(invalid["source_checked"])
        self.assertEqual(invalid["error"], "python_syntax_invalid")

    def test_volume_identity_requires_microbit_label_details_and_v2_interface(self):
        with tempfile.TemporaryDirectory() as directory:
            mount = Path(directory)
            (mount / "DETAILS.TXT").write_text(DETAILS_V2, encoding="utf-8")

            accepted = microbit_v2.inspect_volume(mount, label="MICROBIT")
            ordinary = microbit_v2.inspect_volume(mount, label="USB DISK")
            maintenance = microbit_v2.inspect_volume(mount, label="MAINTENANCE")
            (mount / "DETAILS.TXT").write_text("Version: 0249\n", encoding="utf-8")
            v1 = microbit_v2.inspect_volume(mount, label="MICROBIT")

        self.assertIsNotNone(accepted)
        self.assertEqual(accepted.interface_version, 257)
        self.assertIsNone(ordinary)
        self.assertIsNone(maintenance)
        self.assertIsNone(v1)

    def test_multiple_microbits_require_an_explicit_mount(self):
        first = microbit_v2.MicrobitVolume(Path("C:/one"), "MICROBIT", DETAILS_V2, 257)
        second = microbit_v2.MicrobitVolume(Path("D:/two"), "MICROBIT", DETAILS_V2, 257)

        selected, error = microbit_v2.select_volume([first, second])
        requested, requested_error = microbit_v2.select_volume([first, second], str(first.mount))

        self.assertIsNone(selected)
        self.assertEqual(error, "multiple_microbits_require_selection")
        self.assertEqual(requested, first)
        self.assertIsNone(requested_error)

    def test_virtual_flash_reports_write_and_fail_txt_as_separate_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mount = root / "MICROBIT"
            mount.mkdir()
            (mount / "DETAILS.TXT").write_text(DETAILS_V2, encoding="utf-8")
            volume = microbit_v2.inspect_volume(mount, label="MICROBIT")
            assert volume is not None
            firmware = root / "program.hex"
            firmware.write_text(":00000001FF\n", encoding="ascii")

            success = microbit_v2.flash_hex_to_volume(firmware, volume)
            (mount / "FAIL.TXT").write_text("error 123", encoding="utf-8")
            failed = microbit_v2.flash_hex_to_volume(firmware, volume)

        self.assertTrue(success["success"])
        self.assertTrue(success["write_completed"])
        self.assertFalse(success["reenumeration_verified"])
        self.assertFalse(success["serial_verified"])
        self.assertFalse(success["physical_effect_verified"])
        self.assertFalse(failed["success"])
        self.assertEqual(failed["error"], "daplink_reported_failure")

    def test_package_result_records_hex_packaging_not_native_compilation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out.hex"

            def runner(command, timeout):
                Path(command[-1]).write_text(":00000001FF\n", encoding="ascii")
                return {"returncode": 0, "stdout": "{}", "stderr": "", "command": command}

            status = {
                "ready_for_packaging": True,
                "node": "node",
                "npm": "npm",
                "runtime_hex": str(root / "runtime.hex"),
                "runtime_verified": True,
                "microbit_fs_verified": True,
                "tool_root": str(root),
            }
            with mock.patch.object(microbit_v2, "_environment_status", return_value=status):
                result = microbit_v2.package_hex_result(
                    "print('hello')\n", output=output, tool_root=root, runner=runner
                )

        self.assertTrue(result["success"])
        self.assertTrue(result["hex_packaged"])
        self.assertFalse(result["code_compiled"])

    def test_packager_failure_cannot_be_overwritten_by_a_successful_source_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = {
                "ready_for_packaging": True,
                "node": "node",
                "npm": "npm",
                "runtime_hex": str(root / "runtime.hex"),
                "runtime_verified": True,
                "microbit_fs_verified": True,
                "tool_root": str(root),
            }
            with mock.patch.object(microbit_v2, "_environment_status", return_value=status):
                result = microbit_v2.package_hex_result(
                    "print('hello')\n",
                    output=root / "out.hex",
                    tool_root=root,
                    runner=lambda command, timeout: {"returncode": 1, "stdout": "", "stderr": "failed"},
                )

        self.assertFalse(result["success"])
        self.assertTrue(result["source_checked"])
        self.assertFalse(result["hex_packaged"])
        self.assertEqual(result["error"], "hex_packaging_failed")


if __name__ == "__main__":
    unittest.main()

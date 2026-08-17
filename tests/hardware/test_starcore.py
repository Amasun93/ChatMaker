import tempfile
import unittest
from pathlib import Path

from chatmaker.hardware import starcore


class StarcoreTests(unittest.TestCase):
    def test_current_and_historical_targets_stay_separate(self):
        self.assertTrue(starcore.CURRENT_FQBN.startswith("dfrobot:mpython:mpython:"))
        self.assertTrue(starcore.HISTORICAL_FQBN.startswith("mindplus:esp32:mpython:"))
        self.assertNotEqual(starcore.CURRENT_FQBN, starcore.HISTORICAL_FQBN)

    def test_compile_command_uses_current_target(self):
        context = {"builder": "builder.exe", "arduino": r"C:\Mind+\Arduino"}
        command = starcore.build_compile_command(context, Path("blink.ino"), Path("build"))
        self.assertIn(f"-fqbn={starcore.CURRENT_FQBN}", command)
        self.assertNotIn(f"-fqbn={starcore.HISTORICAL_FQBN}", command)

    def test_upload_requires_confirmed_board_identity(self):
        original = starcore.scan_ports
        starcore.scan_ports = lambda: [{"address": "COM7", "eligible_for_upload": True}]
        try:
            port, error, _ = starcore._select_port({})
        finally:
            starcore.scan_ports = original
        self.assertIsNone(port)
        self.assertEqual(error, "starcore_identity_confirmation_required")

    def test_missing_current_toolchain_is_reported(self):
        original = starcore._current_context
        starcore._current_context = lambda: None
        try:
            result = starcore.execute_request({"action": "compile", "code": "x"})
        finally:
            starcore._current_context = original
        self.assertEqual(result["error"], "mindplus_1_starcore_toolchain_missing")

    def test_compile_requires_source(self):
        with tempfile.TemporaryDirectory() as folder:
            context = {"builder": "builder.exe", "arduino": folder}
            result = starcore.compile_result(context, {})
        self.assertEqual(result["error"], "sketch_or_code_required")


if __name__ == "__main__":
    unittest.main()

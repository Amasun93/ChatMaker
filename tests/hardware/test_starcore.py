import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chatmaker.hardware import starcore


class StarcoreTests(unittest.TestCase):
    def test_current_and_historical_targets_stay_separate(self):
        self.assertTrue(starcore.CURRENT_FQBN.startswith("mindplus:esp32:mpython:"))
        self.assertTrue(starcore.FALLBACK_FQBN.startswith("dfrobot:mpython:mpython:"))
        self.assertNotEqual(starcore.CURRENT_FQBN, starcore.FALLBACK_FQBN)

    def test_mindplus_2_compile_command_uses_preferred_target(self):
        context = {
            "backend": "mindplus-2-cli",
            "cli": "arduino-cli.exe",
            "config": "arduino-cli.yaml",
        }
        command = starcore.build_compile_command(context, Path("blink.ino"), Path("build"))
        self.assertIn(starcore.CURRENT_FQBN, command)
        self.assertNotIn(starcore.FALLBACK_FQBN, command)

    def test_mindplus_1_compile_command_is_only_the_fallback(self):
        context = {
            "backend": "mindplus-1-builder",
            "builder": "builder.exe",
            "arduino": r"C:\Mind+\Arduino",
        }
        command = starcore.build_compile_command(context, Path("blink.ino"), Path("build"))
        self.assertIn(f"-fqbn={starcore.FALLBACK_FQBN}", command)
        self.assertNotIn(f"-fqbn={starcore.CURRENT_FQBN}", command)

    def test_discovery_prefers_usable_mindplus_2_over_mindplus_1(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cli = root / "Mind+2" / "arduino-cli.exe"
            config = root / "arduino-cli.yaml"
            builder = root / "Mind+1" / "Arduino" / "arduino-builder.exe"
            boards = root / "Mind+1" / "Arduino" / "hardware" / "dfrobot" / "mpython" / "boards.txt"
            for path in (cli, config, builder, boards):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder", encoding="utf-8")
            installations = [
                {"backend": "mindplus-1-builder", "root": str(root / "Mind+1"), "builder": str(builder)},
                {"backend": "mindplus-2-cli", "root": str(root / "Mind+2"), "cli": str(cli), "config": str(config)},
            ]
            with mock.patch.object(starcore.shared, "discover_installations", return_value=installations):
                context = starcore._current_context()
        self.assertEqual(context["backend"], "mindplus-2-cli")
        self.assertEqual(context["fqbn"], starcore.CURRENT_FQBN)

    def test_upload_requires_confirmed_board_identity(self):
        original = starcore.scan_ports
        starcore.scan_ports = lambda: [{"address": "COM7", "eligible_for_upload": True}]
        try:
            port, error, _ = starcore._select_port({})
        finally:
            starcore.scan_ports = original
        self.assertIsNone(port)
        self.assertEqual(error, "starcore_identity_confirmation_required")

    def test_missing_toolchain_is_reported(self):
        original = starcore._current_context
        starcore._current_context = lambda: None
        try:
            result = starcore.execute_request({"action": "compile", "code": "x"})
        finally:
            starcore._current_context = original
        self.assertEqual(result["error"], "starcore_mindplus_toolchain_missing")

    def test_compile_requires_source(self):
        with tempfile.TemporaryDirectory() as folder:
            context = {"builder": "builder.exe", "arduino": folder}
            result = starcore.compile_result(context, {})
        self.assertEqual(result["error"], "sketch_or_code_required")


if __name__ == "__main__":
    unittest.main()

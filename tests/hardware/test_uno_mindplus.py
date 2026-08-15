from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNO_PATH = ROOT / "runtime" / "chatmaker" / "hardware" / "uno_mindplus.py"


def load_uno():
    if not UNO_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("chatmaker_uno_mindplus", UNO_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class UnoMindPlusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uno = load_uno()

    def test_uno_runtime_exists(self):
        self.assertIsNotNone(self.uno, "Uno runtime is missing")

    def test_compile_commands_use_uno_fqbn_for_each_mindplus_generation(self):
        self.assertIsNotNone(self.uno, "Uno runtime is missing")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sketch = root / "blink" / "blink.ino"
            sketch.parent.mkdir()
            sketch.write_text("void setup() {}\nvoid loop() {}\n", encoding="utf-8")
            build = root / "build"

            v2 = self.uno.build_compile_command(
                {"backend": "mindplus-2-cli", "cli": "arduino-cli", "config": "config.yaml"},
                sketch,
                build,
            )
            v1 = self.uno.build_compile_command(
                {
                    "backend": "mindplus-1-builder",
                    "builder": "arduino-builder",
                    "arduino": str(root / "Arduino"),
                },
                sketch,
                build,
            )

        self.assertIn("mindplus:avr:uno", v2)
        self.assertIn("-fqbn=arduino:avr:uno", v1)
        self.assertFalse(any("nano" in part.casefold() for part in v1 + v2))

    def test_upload_uses_one_fixed_115200_attempt_without_nano_fallback(self):
        self.assertIsNotNone(self.uno, "Uno runtime is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            return {"returncode": 1, "stdout": "avrdude: stk500_getsync(): not in sync", "stderr": ""}

        with tempfile.TemporaryDirectory() as directory:
            hex_file = Path(directory) / "blink.hex"
            hex_file.write_text(":00000001FF\n", encoding="ascii")
            result = self.uno.run_upload_attempt(
                avrdude="avrdude",
                config="avrdude.conf",
                hex_file=hex_file,
                port="COM9",
                runner=runner,
            )

        self.assertFalse(result["success"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][calls[0].index("-b") + 1], "115200")
        self.assertNotIn("57600", calls[0])

    def test_port_selection_rejects_bluetooth_and_requires_one_wired_candidate(self):
        self.assertIsNotNone(self.uno, "Uno runtime is missing")
        ports = [
            {"address": "COM3", "is_bluetooth": True, "eligible_for_upload": False},
            {"address": "COM8", "is_bluetooth": False, "eligible_for_upload": True},
            {"address": "COM9", "is_bluetooth": False, "eligible_for_upload": True},
        ]

        selected, error = self.uno.select_upload_port(ports)
        bluetooth, bluetooth_error = self.uno.select_upload_port(ports, "COM3")

        self.assertIsNone(selected)
        self.assertEqual(error, "multiple_wired_ports_require_selection")
        self.assertIsNone(bluetooth)
        self.assertEqual(bluetooth_error, "bluetooth_port_rejected")

    def test_compile_upload_waits_for_uno_hardware_after_compile(self):
        self.assertIsNotNone(self.uno, "Uno runtime is missing")

        result = self.uno.compile_upload_result(
            {"backend": "mindplus-2-cli"},
            {"code": "void setup(){} void loop(){}"},
            compile_fn=lambda context, request: {"success": True, "application_hex": "blink.hex"},
            upload_fn=lambda context, request, compiled: {
                "success": False,
                "error": "no_wired_upload_port_found",
                "upload_executed": False,
            },
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "awaiting-hardware")
        self.assertTrue(result["hardware_connection_required"])
        self.assertIn("Uno", result["teacher_message"])


if __name__ == "__main__":
    unittest.main()

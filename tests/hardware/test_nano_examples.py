from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.hardware.nano_examples import EXAMPLE_NAMES, compile_examples  # noqa: E402


EXPECTED = {
    "blink",
    "dht11-serial",
    "light-led",
    "oled-light",
    "oled-dashboard",
    "potentiometer-led",
    "relay-control-side",
    "rgb-led-cycle",
    "servo-button",
    "ultrasonic-buzzer",
    "ws2812-one-pixel",
}


class NanoExampleTests(unittest.TestCase):
    def test_checked_in_examples_match_the_supported_set(self):
        example_root = ROOT / "examples" / "chatduino" / "nano"
        found = {
            path.name
            for path in example_root.iterdir()
            if path.is_dir() and (path / f"{path.name}.ino").is_file()
        }

        self.assertEqual(set(EXAMPLE_NAMES), EXPECTED)
        self.assertEqual(found, EXPECTED)

    def test_batch_compile_reports_each_real_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            example_root = Path(temporary)
            for name in EXAMPLE_NAMES:
                folder = example_root / name
                folder.mkdir()
                (folder / f"{name}.ino").write_text(
                    "void setup() {}\nvoid loop() {}\n", encoding="utf-8"
                )

            calls: list[str] = []

            def compile_fn(context, request):
                calls.append(Path(request["sketch"]).stem)
                return {
                    "success": request["project_name"] != "oled-light",
                    "backend": context["backend"],
                    "fqbn": "mindplus:avr:nano:cpu=atmega328",
                }

            report = compile_examples(
                example_root,
                context={"backend": "mindplus-2-cli"},
                compile_fn=compile_fn,
            )

        self.assertEqual(set(calls), EXPECTED)
        self.assertFalse(report["success"])
        self.assertEqual(report["compiled"], len(EXPECTED))
        self.assertEqual(report["passed"], len(EXPECTED) - 1)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(
            [item["name"] for item in report["results"] if not item["success"]],
            ["oled-light"],
        )

    def test_batch_compile_stops_when_no_mindplus_is_available(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = compile_examples(
                Path(temporary),
                discover_fn=lambda: [],
            )

        self.assertFalse(report["success"])
        self.assertEqual(report["error"], "mindplus_not_installed_or_toolchain_missing")
        self.assertEqual(report["compiled"], 0)


if __name__ == "__main__":
    unittest.main()

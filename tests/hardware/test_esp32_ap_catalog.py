from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


class Esp32ApCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = load_yaml("packs/boards/esp32-devkit-v1.yaml")
        cls.potentiometer = load_yaml(
            "packs/components/linear-potentiometer-10k.yaml"
        )
        cls.recipe = load_yaml("packs/recipes/esp32-ap-led-sensor.yaml")

    def test_board_record_exposes_only_the_exact_doit_wroom_target(self):
        identity = self.board["identity"]

        self.assertEqual(identity["carrier_board"], "DOIT ESP32 DEVKIT V1")
        self.assertEqual(identity["module"], "ESP-WROOM-32")
        self.assertTrue(identity["physical_confirmation_required"])
        self.assertEqual(
            identity["allowed_fqbn"],
            ["esp32:esp32:esp32doit-devkit-v1"],
        )
        self.assertEqual(self.board["toolchains"][0]["version"], "3.3.11")

    def test_board_record_documents_safe_ap_demo_pins_and_power(self):
        pins = {pin["id"]: pin["capabilities"] for pin in self.board["pins"]}
        constraints = " ".join(self.board["constraints"])

        self.assertIn("output", pins["GPIO23"])
        self.assertIn("adc1", pins["GPIO34"])
        self.assertIn("input-only", pins["GPIO34"])
        self.assertIn("3.3v", pins["3V3"])
        self.assertIn("shared", pins["GND"])
        self.assertIn("GPIO23", constraints)
        self.assertIn("GPIO34", constraints)
        self.assertIn("3V3", constraints)
        self.assertIn("Wi-Fi", constraints)

    def test_potentiometer_adds_esp32_3v3_gpio34_guidance(self):
        notes = self.potentiometer["board_notes"]["esp32-devkit-v1"]

        self.assertIn("esp32-devkit-v1", self.potentiometer["supported_boards"])
        self.assertIn("3V3", notes)
        self.assertIn("GPIO34", notes)
        self.assertIn("GND", notes)
        self.assertIn("never use 5V", notes)
        self.assertIn(
            "examples/chatduino/esp32/ap-led-sensor/ap-led-sensor.ino",
            self.potentiometer["example_files"],
        )

    def test_ap_recipe_uses_gpio23_led_and_3v3_gpio34_potentiometer(self):
        self.assertEqual(self.recipe["boards"], ["esp32-devkit-v1"])
        self.assertEqual(
            self.recipe["components"],
            ["basic-led", "linear-potentiometer-10k"],
        )
        self.assertEqual(
            self.recipe["source_file"],
            "examples/chatduino/esp32/ap-led-sensor/ap-led-sensor.ino",
        )

        wiring = {
            (wire["component"], wire["component_pin"]): wire
            for wire in self.recipe["wiring"]
        }
        self.assertEqual(wiring[("basic-led", "anode")]["board_pin"], "GPIO23")
        self.assertEqual(wiring[("basic-led", "cathode")]["board_pin"], "GND")
        self.assertTrue(wiring[("basic-led", "cathode")]["shared"])
        self.assertEqual(
            wiring[("linear-potentiometer-10k", "VCC")]["board_pin"], "3V3"
        )
        self.assertEqual(
            wiring[("linear-potentiometer-10k", "OUT")]["board_pin"], "GPIO34"
        )
        self.assertEqual(
            wiring[("linear-potentiometer-10k", "GND")]["board_pin"], "GND"
        )
        self.assertTrue(wiring[("linear-potentiometer-10k", "GND")]["shared"])
        self.assertNotIn("5V", {wire["board_pin"] for wire in self.recipe["wiring"]})

    def test_ap_recipe_keeps_every_runtime_gate_unverified(self):
        verification = self.recipe["verification"]
        runtime_gates = (
            "code_compiled",
            "firmware_uploaded",
            "wifi_ap_available",
            "http_exchange_verified",
            "physical_effect_verified",
        )

        for gate_name in runtime_gates:
            with self.subTest(gate=gate_name):
                self.assertEqual(verification[gate_name]["status"], "unverified")
                self.assertIsNone(verification[gate_name]["checked_at"])
                self.assertIsNone(verification[gate_name]["evidence"])

    def test_ap_recipe_source_file_exists_but_does_not_imply_runtime_success(self):
        self.assertTrue((ROOT / self.recipe["source_file"]).is_file())
        self.assertIn("current-limiting resistor", self.recipe["summary"])
        self.assertIn("ChatMaker-ESP32", self.recipe["expected_effect"])
        self.assertIn("192.168.4.1", self.recipe["expected_effect"])


if __name__ == "__main__":
    unittest.main()

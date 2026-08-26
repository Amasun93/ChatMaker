from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

import yaml

from chatmaker.hardware import stardust


ROOT = Path(__file__).resolve().parents[2]


class StardustTests(unittest.TestCase):
    def test_product_identity_stays_separate_from_compatible_nano_target(self):
        with mock.patch.object(
            stardust.avr,
            "execute_request",
            return_value={"action": "doctor", "success": True, "fqbn": "mindplus:avr:nano:cpu=atmega328"},
        ):
            result = stardust.execute_request({"action": "doctor"})
        self.assertEqual(result["board"], "stardust-atmega328p")
        self.assertEqual(result["compatible_avr_target"], "mindplus:avr:nano:cpu=atmega328")
        self.assertNotEqual(result["board"], "arduino-nano-classic")

    def test_upload_requires_confirmed_stardust_identity(self):
        result = stardust.execute_request({"action": "compile-upload", "code": "void setup(){}"})
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "stardust_identity_confirmation_required")
        self.assertFalse(result["upload_executed"])

    def test_doctor_does_not_promote_a_wired_port_to_confirmed_stardust(self):
        with mock.patch.object(
            stardust.avr,
            "execute_request",
            return_value={
                "action": "doctor",
                "success": True,
                "ready_for_compile": True,
                "ready_for_upload": True,
                "ports": [{"address": "COM8", "eligible_for_upload": True}],
            },
        ):
            result = stardust.execute_request({"action": "doctor"})
        self.assertFalse(result["ready_for_upload"])
        self.assertEqual(result["upload_blocked_by"], "stardust_identity_confirmation_required")

    def test_record_preserves_only_observed_pin_and_evidence_scope(self):
        board = yaml.safe_load(
            (ROOT / "packs/boards/stardust-atmega328p.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(board["identity"]["compatible_target"], "mindplus:avr:nano:cpu=atmega328")
        self.assertEqual(board["mechanics"]["status"], "research-required")
        self.assertEqual({pin["id"] for pin in board["pins"]}, {"USB", "5V", "GND", "A4", "A5"})
        self.assertEqual(board["verification"]["physical_effect_verified"]["status"], "verified")
        self.assertEqual(
            board["verification"]["physical_effect_verified"]["method"],
            "user-confirmation",
        )

    def test_oled_recipe_records_user_confirmed_visible_effect_separately_from_serial_proxy(self):
        recipe = yaml.safe_load(
            (ROOT / "packs/recipes/stardust-idmd-0021-oled-status.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(recipe["boards"], ["stardust-atmega328p"])
        self.assertEqual(recipe["verification"]["serial_evidence"]["status"], "verified")
        self.assertEqual(recipe["verification"]["physical_effect_verified"]["status"], "verified")
        self.assertEqual(
            recipe["verification"]["physical_effect_verified"]["method"],
            "user-confirmation",
        )

    def test_oled_component_records_the_stardust_driver_without_replacing_starcore_api(self):
        component = yaml.safe_load(
            (ROOT / "packs/components/idmd-0021-starcore-oled-1-3.yaml").read_text(
                encoding="utf-8"
            )
        )
        libraries = {item["name"]: item for item in component["libraries"]}
        self.assertIn("Mind+ MPython display API", libraries)
        self.assertEqual(
            libraries["DFRobot SSD1306 I2C for Stardust"]["headers"],
            ["DFRobot_SSD1306_I2C.h"],
        )
        self.assertIn("stardust-atmega328p", component["supported_boards"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BOARD_ID = "idmc-0001-starcore-v4-2-2"
CURRENT_FQBN = "dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none"
COMPILE_REPORT = "docs/verification/2026-08-18-starcore-seven-module-compilation.md"
RECIPES = {
    "starcore-idmd-0001-rgb-pwm": "idmd-0001-starcore-rgb-light",
    "starcore-idmd-0002-serial-mp3": "idmd-0002-starcore-serial-mp3",
    "starcore-idmd-0021-oled-message": "idmd-0021-starcore-oled-1-3",
    "starcore-idms-0001-button-input": "idms-0001-starcore-button",
    "starcore-idms-0003-potentiometer-read": "idms-0003-starcore-potentiometer",
    "starcore-idms-0008-dht11-serial": "idms-0008-starcore-dht11",
    "starcore-idms-0009-ultrasonic-distance": "idms-0009-starcore-ultrasonic",
}


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class StarcoreOwnedExampleTests(unittest.TestCase):
    def test_each_owned_module_has_one_exact_recipe_and_source(self):
        for recipe_id, component_id in RECIPES.items():
            with self.subTest(recipe_id=recipe_id):
                recipe = load_yaml(ROOT / "packs" / "recipes" / f"{recipe_id}.yaml")
                expected_source = (
                    f"examples/chatduino/starcore/{recipe_id}/{recipe_id}.ino"
                )
                self.assertEqual(recipe["id"], recipe_id)
                self.assertEqual(recipe["boards"], [BOARD_ID])
                self.assertEqual(recipe["components"], [component_id])
                self.assertEqual(recipe["source_file"], expected_source)
                self.assertTrue((ROOT / expected_source).is_file())
                self.assertEqual(
                    {wire["component"] for wire in recipe["wiring"]},
                    {component_id},
                )
                compiled = recipe["verification"]["code_compiled"]
                self.assertEqual(compiled["status"], "verified")
                evidence = recipe["compile_evidence"]
                if recipe_id == "starcore-idmd-0021-oled-message":
                    self.assertEqual(compiled["checked_at"], "2026-08-25")
                    self.assertEqual(
                        compiled["evidence_id"],
                        "starcore-oled-mindplus2-compile-2026-08-25",
                    )
                else:
                    self.assertEqual(compiled["checked_at"], "2026-08-18")
                    self.assertEqual(compiled["evidence"], evidence["id"])
                self.assertRegex(
                    evidence["completed_at"],
                    r"^2026-08-18T\d{2}:\d{2}:\d{2}\+08:00$",
                )
                self.assertEqual(evidence["fqbn"], CURRENT_FQBN)
                self.assertEqual(evidence["exit_code"], 0)
                self.assertEqual(evidence["report"], COMPILE_REPORT)
                self.assertIn("Mind+ 1.8", evidence["toolchain"])
                self.assertIn("arduino-builder -compile", evidence["command"])
                self.assertGreater(evidence["flash_bytes"], 0)
                self.assertGreater(evidence["ram_bytes"], 0)
                self.assertRegex(evidence["source_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(evidence["application_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(evidence["partitions_sha256"], r"^[0-9a-f]{64}$")
                self.assertFalse(Path(evidence["application_artifact"]).is_absolute())
                self.assertFalse(Path(evidence["partitions_artifact"]).is_absolute())
                source_digest = hashlib.sha256(
                    (ROOT / expected_source).read_bytes()
                ).hexdigest()
                self.assertEqual(evidence["source_sha256"], source_digest)
                expected_upload = (
                    "verified"
                    if recipe_id == "starcore-idmd-0021-oled-message"
                    else "unverified"
                )
                self.assertEqual(
                    recipe["verification"]["firmware_uploaded"]["status"],
                    expected_upload,
                )
                expected_physical = (
                    "verified"
                    if recipe_id == "starcore-idmd-0021-oled-message"
                    else "unverified"
                )
                self.assertEqual(
                    recipe["verification"]["physical_effect_verified"]["status"],
                    expected_physical,
                )
                component = load_yaml(
                    ROOT / "packs" / "components" / f"{component_id}.yaml"
                )
                self.assertIn(expected_source, component["example_files"])
                component_compiled = component["verification"]["code_compiled"]
                self.assertEqual(component_compiled["status"], "verified")
                if recipe_id == "starcore-idmd-0021-oled-message":
                    self.assertEqual(component_compiled["checked_at"], "2026-08-25")
                    self.assertEqual(
                        component_compiled["evidence_id"],
                        "starcore-oled-mindplus2-compile-2026-08-25",
                    )
                else:
                    self.assertEqual(component_compiled["checked_at"], "2026-08-18")
                    self.assertEqual(component_compiled["evidence"], evidence["id"])
                self.assertNotIn("compile_evidence", component)
                self.assertEqual(
                    component["verification"]["firmware_uploaded"]["status"],
                    "unverified",
                )
                self.assertEqual(
                    component["verification"]["physical_effect_verified"]["status"],
                    expected_physical,
                )

        report = ROOT / COMPILE_REPORT
        self.assertTrue(report.is_file())
        report_text = report.read_text(encoding="utf-8")
        self.assertIn(CURRENT_FQBN, report_text)
        for recipe_id in RECIPES:
            self.assertIn(recipe_id, report_text)
        self.assertNotRegex(report_text, r"[A-Z]:\\")

    def test_examples_keep_beginner_safe_structure_and_diagnostics(self):
        for recipe_id in RECIPES:
            with self.subTest(recipe_id=recipe_id):
                code = (
                    ROOT
                    / "examples"
                    / "chatduino"
                    / "starcore"
                    / recipe_id
                    / f"{recipe_id}.ino"
                ).read_text(encoding="utf-8")
                self.assertIn("void setup()", code)
                self.assertIn("void loop()", code)
                self.assertIn("Serial.begin(115200)", code)
                self.assertIn("_READY", code)
                self.assertNotIn("while (true)", code)

    def test_examples_use_the_owned_mindplus_apis(self):
        expected_tokens = {
            "starcore-idmd-0001-rgb-pwm": (
                "ledcSetup",
                "ledcAttachPin",
                "255 - brightness",
            ),
            "starcore-idmd-0002-serial-mp3": (
                "#include <DFRobot_SerialMp3.h>",
                "begin(&Serial1, P15, P16)",
                "playList",
            ),
            "starcore-idmd-0021-oled-message": (
                "#include <MPython.h>",
                "display.begin(OLED_ADDRESS)",
                "display.printLine",
            ),
            "starcore-idms-0001-button-input": (
                "pinMode(BUTTON_PIN, INPUT)",
                "digitalRead",
                "DEBOUNCE_MS",
            ),
            "starcore-idms-0003-potentiometer-read": (
                "analogRead(POT_PIN)",
                "READ_INTERVAL_MS",
            ),
            "starcore-idms-0008-dht11-serial": (
                "#include <DFRobot_DHT.h>",
                "begin(DHT_PIN, DHT11)",
                "getTemperature",
                "getHumidity",
                "2500",
            ),
            "starcore-idms-0009-ultrasonic-distance": (
                "#include <DFRobot_URM10.h>",
                "getDistanceCM(P_H, P_O)",
                "NO_ECHO",
                "100",
            ),
        }
        for recipe_id, tokens in expected_tokens.items():
            code = (
                ROOT
                / "examples"
                / "chatduino"
                / "starcore"
                / recipe_id
                / f"{recipe_id}.ino"
            ).read_text(encoding="utf-8")
            for token in tokens:
                with self.subTest(recipe_id=recipe_id, token=token):
                    self.assertIn(token, code)
        dht_code = (
            ROOT
            / "examples/chatduino/starcore/starcore-idms-0008-dht11-serial"
            / "starcore-idms-0008-dht11-serial.ino"
        ).read_text(encoding="utf-8")
        self.assertNotIn("isnan", dht_code)

    def test_owned_recipes_remain_discoverable_as_classroom_recipes_grow(self):
        recipe_paths = sorted((ROOT / "packs" / "recipes").glob("*.yaml"))
        self.assertTrue(
            set(RECIPES).issubset({load_yaml(path)["id"] for path in recipe_paths})
        )


if __name__ == "__main__":
    unittest.main()

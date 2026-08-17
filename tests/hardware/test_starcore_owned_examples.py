from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BOARD_ID = "idmc-0001-starcore-v4-2-2"
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
                self.assertEqual(recipe["verification"]["code_compiled"]["status"], "unverified")
                component = load_yaml(
                    ROOT / "packs" / "components" / f"{component_id}.yaml"
                )
                self.assertEqual(component["example_files"], [expected_source])

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

    def test_recipe_total_moves_to_twenty_three_only_with_all_seven_files(self):
        recipe_paths = sorted((ROOT / "packs" / "recipes").glob("*.yaml"))
        self.assertEqual(len(recipe_paths), 23)
        self.assertTrue(
            set(RECIPES).issubset({load_yaml(path)["id"] for path in recipe_paths})
        )


if __name__ == "__main__":
    unittest.main()

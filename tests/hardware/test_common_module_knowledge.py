from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
BOARDS = {
    "arduino-nano-classic": "nano",
    "arduino-uno-r3": "uno",
    "esp32-devkit-v1": "esp32",
    "idmc-0001-starcore-v4-2-2": "starcore",
}
COMPONENTS = (
    "ssd1306-i2c-128x64-module",
    "lcd1602-i2c-pcf8574",
    "ws2812b-addressable-rgb",
    "sg90-micro-servo",
    "hc-sr04",
)


class CommonModuleKnowledgeTests(unittest.TestCase):
    def test_five_component_cards_cover_all_four_boards(self):
        for component_id in COMPONENTS:
            path = ROOT / "packs" / "components" / f"{component_id}.yaml"
            record = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(set(BOARDS), set(record["supported_boards"]), component_id)
            self.assertEqual(set(BOARDS), set(record["board_notes"]), component_id)

    def test_each_component_has_an_example_for_every_board(self):
        for component_id in COMPONENTS:
            record = yaml.safe_load(
                (ROOT / "packs" / "components" / f"{component_id}.yaml").read_text(
                    encoding="utf-8"
                )
            )
            examples = record["example_files"]
            for board_dir in BOARDS.values():
                matches = [item for item in examples if f"/{board_dir}/" in item]
                self.assertTrue(matches, f"{component_id} missing {board_dir} example")
                for relative in matches:
                    self.assertTrue((ROOT / relative).is_file(), relative)

    def test_board_pages_name_the_five_components(self):
        expected = ("OLED", "LCD1602", "WS2812", "SG90", "HC-SR04")
        for board_id in BOARDS:
            page = (
                ROOT
                / "knowledge_sources"
                / "published"
                / "boards"
                / board_id
                / "components-and-wiring.md"
            ).read_text(encoding="utf-8")
            for name in expected:
                self.assertIn(name, page, f"{board_id} missing {name}")


if __name__ == "__main__":
    unittest.main()

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
OWNED_STARCORE_REPLACEMENTS = {
    "ssd1306-i2c-128x64-module",
    "hc-sr04",
}
STARCORE_OWNED_MODULES = (
    "IDMD-0001",
    "IDMD-0002",
    "IDMD-0021",
    "IDMS-0001",
    "IDMS-0003",
    "IDMS-0008",
    "IDMS-0009",
)


class CommonModuleKnowledgeTests(unittest.TestCase):
    def test_common_component_cards_do_not_duplicate_owned_starcore_hardware(self):
        for component_id in COMPONENTS:
            path = ROOT / "packs" / "components" / f"{component_id}.yaml"
            record = yaml.safe_load(path.read_text(encoding="utf-8"))
            expected = set(BOARDS)
            if component_id in OWNED_STARCORE_REPLACEMENTS:
                expected.remove("idmc-0001-starcore-v4-2-2")
            self.assertEqual(expected, set(record["supported_boards"]), component_id)
            self.assertEqual(expected, set(record["board_notes"]), component_id)

    def test_each_component_has_an_example_for_every_board(self):
        for component_id in COMPONENTS:
            record = yaml.safe_load(
                (ROOT / "packs" / "components" / f"{component_id}.yaml").read_text(
                    encoding="utf-8"
                )
            )
            examples = record["example_files"]
            board_dirs = set(BOARDS.values())
            if component_id in OWNED_STARCORE_REPLACEMENTS:
                board_dirs.remove("starcore")
            for board_dir in board_dirs:
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

    def test_starcore_pages_publish_all_seven_owned_modules_and_compile_boundary(self):
        root = ROOT / "knowledge_sources" / "published" / "boards" / "idmc-0001-starcore-v4-2-2"
        wiring = (root / "components-and-wiring.md").read_text(encoding="utf-8")
        libraries = (root / "libraries-and-examples.md").read_text(encoding="utf-8")
        toolchain = (root / "toolchains-and-upload.md").read_text(encoding="utf-8")

        for module_id in STARCORE_OWNED_MODULES:
            self.assertIn(module_id, wiring)
            self.assertIn(module_id, libraries)
        self.assertIn("7/7", toolchain)
        self.assertIn("unverified", toolchain)


if __name__ == "__main__":
    unittest.main()

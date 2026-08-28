from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BOARD_ID = "idmc-0001-starcore-v4-2-2"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class StarcoreClassroomRecipeTests(unittest.TestCase):
    def test_ws2812_and_sg90_reuse_canonical_common_components(self):
        expected = {
            "starcore-ws2812-classroom-strip": "ws2812b-addressable-rgb",
            "starcore-sg90-safe-position": "sg90-micro-servo",
        }
        for recipe_id, component_id in expected.items():
            with self.subTest(recipe_id=recipe_id):
                recipe = load_yaml(ROOT / "packs" / "recipes" / f"{recipe_id}.yaml")
                self.assertEqual(recipe["boards"], [BOARD_ID])
                self.assertEqual(recipe["components"], [component_id])
                self.assertTrue((ROOT / recipe["source_file"]).is_file())
        component_ids = {
            load_yaml(path)["id"]
            for path in (ROOT / "packs" / "components").glob("*.yaml")
        }
        self.assertNotIn("starcore-ws2812", component_ids)
        self.assertNotIn("starcore-sg90", component_ids)

    def test_classroom_examples_keep_low_risk_startup_and_plain_text_wiring(self):
        ws = (
            ROOT
            / "examples/chatduino/starcore/starcore-ws2812-classroom-strip"
            / "starcore-ws2812-classroom-strip.ino"
        ).read_text(encoding="utf-8")
        servo = (
            ROOT
            / "examples/chatduino/starcore/starcore-sg90-safe-position"
            / "starcore-sg90-safe-position.ino"
        ).read_text(encoding="utf-8")
        guide = (
            ROOT / "skills/chatduino/references/starcore-classroom-modules.md"
        ).read_text(encoding="utf-8")

        for token in ("BRIGHTNESS = 32", "strip.clear()", "STARCORE_WS2812_READY"):
            self.assertIn(token, ws)
        for token in ("SAFE_ANGLE = 90", "{60, 90, 120, 90}", "STARCORE_SG90_READY"):
            self.assertIn(token, servo)
        for token in ("【先断电】", "【引脚占用】", "【按顺序接线】", "【通电前检查】"):
            self.assertIn(token, guide)
        self.assertIn("74AHCT125", guide)
        self.assertIn("独立且足量的 5V 电源", guide)

    def test_oled_guide_separates_avr_u8g2_from_starcore_font_asset(self):
        guide = (
            ROOT / "skills/chatduino/references/oled-i2c-troubleshooting.md"
        ).read_text(encoding="utf-8")
        for token in (
            "U8g2",
            "u8g2_font_unifont_t_chinese2",
            "MPython.h",
            "Noto_Sans_CJK_SC_Light16.xbf",
            "0x400000",
        ):
            self.assertIn(token, guide)
        starcore_section = guide.split("## 星核板 IDMC-0001 + IDMD-0021 中文", 1)[1]
        starcore_code = starcore_section.split("```cpp", 1)[1].split("```", 1)[0]
        self.assertIn('display.printLine("你好")', starcore_section)
        self.assertIn("U8g2 不是这条链路的修复方案", starcore_section)
        self.assertNotIn("DFRobot_SSD1306_I2C.h", starcore_code)

    def test_i2c_scanners_are_receive_only_diagnostics(self):
        guide = (
            ROOT / "skills/chatduino/references/oled-i2c-troubleshooting.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(guide.count("Wire.beginTransmission(address)"), 2)
        self.assertEqual(guide.count("Wire.endTransmission()"), 2)
        self.assertIn("I2C_NONE_FOUND", guide)
        self.assertIn("Wire.begin(P20, P19)", guide)

    def test_idmm_0007_diagnostic_never_transmits(self):
        component = load_yaml(
            ROOT / "packs/components/idmm-0007-starcore-serial-servo-driver.yaml"
        )
        code = (
            ROOT
            / "examples/chatduino/starcore/starcore-idmm-0007-read-only-diagnostic"
            / "starcore-idmm-0007-read-only-diagnostic.ino"
        ).read_text(encoding="utf-8")

        self.assertEqual(component["hardware_id"], "IDMM-0007")
        self.assertEqual(component["interface"], "uart-protocol-unknown")
        self.assertIn("ServoBus.read()", code)
        for forbidden in ("ServoBus.write", "ServoBus.print", "ServoBus.printf"):
            self.assertNotIn(forbidden, code)

    def test_chatduino_routes_to_the_two_focused_guides(self):
        skill = (ROOT / "skills/chatduino/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("starcore-classroom-modules.md", skill)
        self.assertIn("oled-i2c-troubleshooting.md", skill)

    def test_i2c_socket_and_ultrasonic_harness_rules_are_explicit(self):
        board = load_yaml(ROOT / "packs/boards/idmc-0001-starcore-v4-2-2.yaml")
        interfaces = {item["id"]: item for item in board["interfaces"]}
        self.assertEqual(interfaces["i2c-connector-bank"]["count"], 8)
        self.assertIn("complete four-wire module cable", interfaces["i2c-connector-bank"]["selection_rule"])

        component = load_yaml(ROOT / "packs/components/idms-0009-starcore-ultrasonic.yaml")
        self.assertEqual(component["recommended_wiring"]["board_pins"]["TRIG"], "H/P26")
        self.assertEqual(component["recommended_wiring"]["board_pins"]["ECHO"], "O/P27")
        self.assertIn("split the cable", component["recommended_wiring"]["beginner_note"])

        guide = (ROOT / "skills/chatduino/references/starcore-classroom-modules.md").read_text(encoding="utf-8")
        for token in ("8 个物理 I2C 插口", "SCL/C", "SDA/D", "2+2 四芯线", "H/P26", "O/P27"):
            self.assertIn(token, guide)


if __name__ == "__main__":
    unittest.main()

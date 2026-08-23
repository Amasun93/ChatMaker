from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from chatmaker.catalog import execute_request


ROOT = Path(__file__).resolve().parents[2]
BOARD_ID = "idmc-0001-starcore-v4-2-2"


class StarcoreOnboardAccelerometerTests(unittest.TestCase):
    def test_onboard_self_test_example_covers_safe_mainboard_only_features(self):
        sketch = (
            ROOT
            / "examples"
            / "chatduino"
            / "starcore"
            / "onboard-self-test"
            / "onboard-self-test.ino"
        )

        self.assertTrue(sketch.is_file())
        source = sketch.read_text(encoding="utf-8")
        for token in (
            "mPython.begin()",
            "buzz.freq(880)",
            "buzz.off()",
            "buttonA.isPressed()",
            "buttonB.isPressed()",
            "accelerometer.getStrength()",
            "STARCORE_SELF_TEST_READY",
        ):
            self.assertIn(token, source)

    def test_catalog_exposes_source_backed_qmi8658_and_mpython_route(self):
        result = execute_request({"action": "get", "id": BOARD_ID}, project_root=ROOT)

        self.assertTrue(result["success"], result)
        self.assertEqual(result["record"]["verification"]["code_compiled"]["status"], "verified")
        self.assertEqual(
            result["record"]["verification"]["firmware_uploaded"]["status"],
            "verified",
        )
        self.assertEqual(
            result["record"]["verification"]["physical_effect_verified"]["status"],
            "verified",
        )
        self.assertIn(
            "QMI8658",
            result["record"]["verification"]["physical_effect_verified"]["evidence"],
        )
        devices = {item["id"]: item for item in result["record"]["onboard_hardware"]}
        sensor = devices["qmi8658"]
        self.assertEqual(
            sensor["interface"],
            {
                "type": "i2c",
                "address": "0x6B",
                "sda_pin": "P20",
                "scl_pin": "P19",
                "interrupt_gpio": 37,
            },
        )
        self.assertEqual(sensor["library"]["header"], "MPython.h")
        self.assertEqual(sensor["library"]["initialization"], "mPython.begin()")
        self.assertEqual(sensor["library"]["object"], "accelerometer")
        self.assertEqual(
            sensor["library"]["read_methods"],
            ["getX()", "getY()", "getZ()", "getStrength()"],
        )
        self.assertTrue(
            {
                "starcore-board-schematic-v4-2-2",
                "starcore-qmi8658-datasheet",
                "starcore-mpython-public-api-snapshot",
                "starcore-mpython-implementation-snapshot",
            }.issubset(sensor["source_ids"])
        )

    def test_knowledge_index_and_pages_make_onboard_motion_discoverable(self):
        index = yaml.safe_load(
            (ROOT / "knowledge" / "boards" / f"{BOARD_ID}.yaml").read_text(
                encoding="utf-8"
            )
        )
        sections = {item["section_id"]: item for item in index["sections"]}
        self.assertIn("onboard-accelerometer", sections["start-here"]["topics"])
        self.assertIn("accelerometer", sections["libraries-and-examples"]["topics"])

        page_root = ROOT / "knowledge_sources" / "published" / "boards" / BOARD_ID
        start_here = (page_root / "start-here.md").read_text(encoding="utf-8")
        libraries = (page_root / "libraries-and-examples.md").read_text(encoding="utf-8")
        pins = (page_root / "pins-and-electrical.md").read_text(encoding="utf-8")
        troubleshooting = (page_root / "troubleshooting.md").read_text(encoding="utf-8")

        self.assertIn("QMI8658", start_here)
        for token in (
            "esp32.esp32_acceleration",
            "mPython.begin()",
            "accelerometer",
            "getX()",
            "getY()",
            "getZ()",
            "getStrength()",
            "MSA300::TiltLeft",
            "onboard-self-test",
            "1041",
        ):
            self.assertIn(token, libraries)
        self.assertIn("0x6B", pins)
        self.assertIn("LIS2DH12", troubleshooting)

    def test_publication_manifest_tracks_accelerometer_evidence_without_source_paths(self):
        manifest = yaml.safe_load(
            (
                ROOT
                / "knowledge_sources"
                / "manifests"
                / f"{BOARD_ID}.yaml"
            ).read_text(encoding="utf-8")
        )
        evidence = {item["source_id"]: item for item in manifest["source_evidence"]}
        for source_id in (
            "starcore-board-schematic-v4-2-2",
            "starcore-qmi8658-datasheet",
            "starcore-mpython-public-api-snapshot",
            "starcore-mpython-implementation-snapshot",
            "starcore-mindplus-acceleration-corpus-snapshot",
        ):
            self.assertRegex(evidence[source_id]["sha256"], r"^[0-9a-f]{64}$")

    def test_router_reports_an_incomplete_workbuddy_bundle_instead_of_fake_search(self):
        router = (ROOT / "skills" / "chatmaker" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        specialist = (ROOT / "skills" / "chatduino" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("chatmaker-install doctor", router)
        self.assertIn("chatmaker-install auto", router)
        self.assertIn("never claim that ChatMaker Knowledge was searched", router)
        self.assertIn("read Starcore `start-here` and `libraries-and-examples`", specialist)
        self.assertIn("onboard QMI8658", specialist)


if __name__ == "__main__":
    unittest.main()

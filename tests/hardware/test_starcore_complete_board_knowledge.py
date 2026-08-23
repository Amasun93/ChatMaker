from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BOARD_ID = "idmc-0001-starcore-v4-2-2"


class StarcoreCompleteBoardKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.board = yaml.safe_load(
            (ROOT / "packs" / "boards" / f"{BOARD_ID}.yaml").read_text(
                encoding="utf-8"
            )
        )

    def test_complete_gpio_map_preserves_starcore_and_mpython_aliases(self):
        expected = {
            "P4": 39,
            "P6": 16,
            "P7": 17,
            "P10": 36,
            "P13": 18,
            "P14": 19,
            "P19": 22,
            "P20": 23,
            "P23": 27,
            "P24": 14,
            "P25": 12,
            "P26": 13,
            "P27": 15,
            "P28": 4,
        }
        self.assertEqual(
            {key: self.board["gpio_map"][key] for key in expected},
            expected,
        )
        self.assertEqual(
            self.board["code_aliases"],
            {
                "P_P": "P23",
                "P_Y": "P24",
                "P_T": "P25",
                "P_H": "P26",
                "P_O": "P27",
                "P_N": "P28",
            },
        )

    def test_real_onboard_hardware_and_software_only_objects_stay_separate(self):
        devices = {item["id"]: item for item in self.board["onboard_hardware"]}
        self.assertTrue(
            {
                "qmi8658",
                "button-a",
                "button-b",
                "passive-buzzer",
                "ch9102f",
                "sit3051tk",
            }.issubset(devices)
        )
        self.assertEqual(devices["button-a"]["library"]["object"], "buttonA")
        self.assertEqual(devices["button-b"]["library"]["object"], "buttonB")
        self.assertEqual(devices["passive-buzzer"]["library"]["object"], "buzz")
        compatibility = self.board["software_compatibility"]
        self.assertEqual(
            compatibility["exposed_but_not_onboard_hardware"],
            ["display", "rgb", "light", "sound"],
        )
        self.assertIn(
            "accelerometer",
            compatibility["physically_present_mpython_objects"],
        )

    def test_power_can_i2c_and_input_only_boundaries_are_canonical(self):
        power_ids = {item["id"] for item in self.board["power_inputs"]}
        self.assertEqual(
            power_ids,
            {"usb-c-5v", "vin-6-24v", "d5v-3.8-5.5v", "direct-3v3"},
        )
        interfaces = {item["id"]: item for item in self.board["interfaces"]}
        self.assertEqual(interfaces["can-bus"]["controller_tx"], "P13/GPIO18")
        self.assertEqual(interfaces["can-bus"]["controller_rx"], "P14/GPIO19")
        self.assertEqual(interfaces["i2c-3v3-bank"]["count"], 3)
        self.assertEqual(interfaces["i2c-5v-bank"]["count"], 3)
        pins = {item["id"]: set(item["capabilities"]) for item in self.board["pins"]}
        for pin_id in ("P2", "P3", "P4", "P10", "IO37", "IO38"):
            self.assertIn("input-only", pins[pin_id])
        self.assertIn("onboard-can-tx", pins["P13"])
        self.assertIn("onboard-can-rx", pins["P14"])

    def test_source_manifest_tracks_the_new_primary_sources(self):
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
            "starcore-board-description-doc",
            "starcore-io-mapping-workbook",
            "starcore-mpython-pin-variant",
        ):
            self.assertRegex(evidence[source_id]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            manifest["cleaning_version"],
            "chatmaker-starcore-knowledge-v3",
        )


if __name__ == "__main__":
    unittest.main()

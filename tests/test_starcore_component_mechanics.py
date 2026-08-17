from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.cad import generator  # noqa: E402
from chatmaker.integrations import workbuddy_mcp  # noqa: E402


COMPONENT_IDS = {
    "idmd-0001-starcore-rgb-light",
    "idmd-0002-starcore-serial-mp3",
    "idmd-0021-starcore-oled-1-3",
    "idms-0001-starcore-button",
    "idms-0003-starcore-potentiometer",
    "idms-0008-starcore-dht11",
    "idms-0009-starcore-ultrasonic",
}


class StarcoreComponentMechanicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema_path = ROOT / "knowledge/mechanical/schemas/component-profile.schema.json"
        cls.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(cls.schema)
        cls.profile_paths = sorted((ROOT / "knowledge/mechanical/components").glob("*.json"))
        cls.profiles = {
            value["component_id"]: value
            for value in (json.loads(path.read_text(encoding="utf-8")) for path in cls.profile_paths)
        }

    def test_schema_accepts_exactly_the_seven_owned_profiles(self):
        self.assertEqual(set(self.profiles), COMPONENT_IDS)
        registry = json.loads(
            (ROOT / "knowledge/mechanical/source-registry.json").read_text(encoding="utf-8")
        )
        sources = {item["id"]: item for item in registry["sources"]}
        for path in self.profile_paths:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.validator.validate(value)
            self.assertEqual(path.stem, value["component_id"])
            self.assertEqual(value["verification"]["physical_fit"], "unverified")
            self.assertTrue(value["source_ids"])
            for source_id in value["source_ids"]:
                self.assertRegex(sources[source_id]["artifact_sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(sources[source_id]["evidence_level"])

    def test_known_outline_mounting_and_panel_facts_are_preserved(self):
        expected = {
            "idmd-0001-starcore-rgb-light": (30, 30, 20, 20),
            "idmd-0002-starcore-serial-mp3": (55.021, 30.021, 45, 20),
            "idmd-0021-starcore-oled-1-3": (55.283, 30.255, 45, 20),
            "idms-0001-starcore-button": (30, 30, 20, 20),
            "idms-0003-starcore-potentiometer": (30, 30, 20, 20),
            "idms-0008-starcore-dht11": (30, 30, 20, 20),
            "idms-0009-starcore-ultrasonic": (55.021, 30.021, 45, 20),
        }
        for component_id, facts in expected.items():
            profile = self.profiles[component_id]
            actual = (
                profile["outline"]["width"],
                profile["outline"]["depth"],
                profile["mounting"]["pattern_x"],
                profile["mounting"]["pattern_y"],
            )
            self.assertEqual(actual, facts)
            self.assertEqual(len(profile["mounting"]["holes"]), 4)

        self.assertEqual(
            self.profiles["idmd-0002-starcore-serial-mp3"]["panel_features"][0]["diameter"],
            23,
        )
        self.assertEqual(
            self.profiles["idmd-0021-starcore-oled-1-3"]["panel_features"][0]["size"],
            [37, 25],
        )
        self.assertEqual(
            self.profiles["idms-0008-starcore-dht11"]["panel_features"][0]["center"],
            [0, 0.239],
        )
        ultrasonic = self.profiles["idms-0009-starcore-ultrasonic"]["panel_features"][0]
        self.assertEqual((ultrasonic["diameter"], ultrasonic["center_spacing"]), (15.8, 25.525))

    def test_unknown_cutouts_are_explicit_and_contain_no_guessed_geometry(self):
        for component_id in {
            "idmd-0001-starcore-rgb-light",
            "idms-0001-starcore-button",
            "idms-0003-starcore-potentiometer",
        }:
            feature = self.profiles[component_id]["panel_features"][0]
            self.assertEqual(feature["status"], "requires_measurement")
            self.assertEqual(feature["availability"], "not_available")
            self.assertFalse(
                {"center", "diameter", "size", "center_spacing"} & set(feature),
                feature,
            )

    def test_profiles_do_not_publish_manufacturing_files_or_local_paths(self):
        serialized = "\n".join(
            path.read_text(encoding="utf-8") for path in self.profile_paths
        ).lower()
        for forbidden in (".step", ".dxf", ".gerber", "c:\\", "d:\\", "file://"):
            self.assertNotIn(forbidden, serialized)

    def test_runtime_and_mcp_read_a_component_profile_by_exact_id(self):
        result = generator.execute_request(
            {
                "action": "component-profile",
                "component_id": "idms-0008-starcore-dht11",
            }
        )
        self.assertTrue(result["success"], result)
        self.assertEqual(result["profile"]["hardware_id"], "IDMS-0008")

        tool = next(
            item for item in workbuddy_mcp.TOOLS
            if item["name"] == "cad_component_profile_get"
        )
        self.assertEqual(set(tool["inputSchema"]["required"]), {"component_id"})
        response = workbuddy_mcp._tool_result(
            "cad_component_profile_get",
            {"component_id": "idms-0008-starcore-dht11"},
        )
        self.assertFalse(response["isError"])
        payload = json.loads(response["content"][0]["text"])
        self.assertEqual(payload["profile"]["component_id"], "idms-0008-starcore-dht11")

        rejected = generator.execute_request(
            {"action": "component-profile", "component_id": "../private-source"}
        )
        self.assertEqual(rejected["error"], "invalid_component_id")

    def test_doctor_reports_seven_valid_component_profiles(self):
        completed = subprocess.run(
            [sys.executable, "-m", "chatmaker.doctor", "--packs"],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "runtime")},
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["component_mechanics"], {"ok": True, "count": 7, "errors": []})


if __name__ == "__main__":
    unittest.main()

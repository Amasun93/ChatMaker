from __future__ import annotations

from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.catalog import execute_request


MANIFEST = ROOT / "knowledge_sources/catalogs/self-developed-hardware.yaml"
SCHEMA = ROOT / "knowledge_sources/schemas/self-developed-hardware.schema.yaml"


class SelfDevelopedHardwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_schema_and_exact_unique_scope(self):
        self.assertTrue(MANIFEST.is_file())
        self.assertFalse((ROOT / "knowledge_sources/manifests/self-developed-hardware.yaml").exists())
        schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(self.manifest))
        self.assertEqual(errors, [])
        self.assertEqual(self.manifest["module_count"], 23)
        hardware_ids = [item["hardware_id"] for item in self.manifest["modules"]]
        catalog_ids = [item["catalog_id"] for item in self.manifest["modules"]]
        self.assertEqual(len(set(hardware_ids)), 23)
        self.assertEqual(len(set(catalog_ids)), 23)

    def test_all_runtime_records_have_beginner_names_and_traceable_profiles(self):
        result = execute_request({"action": "list_modules"}, project_root=ROOT)
        self.assertTrue(result["success"])
        self.assertEqual(result["module_count"], 23)
        for card in result["modules"]:
            with self.subTest(card=card["name"]):
                self.assertNotRegex(card["name"], r"IDM[CDFMS]-\d{4}")
                self.assertRegex(card["identity"]["hardware_id"], r"^IDM[CDFMS]-\d{4}$")
                self.assertEqual(card["usability"], "guidance_ready")
                self.assertIn(card["capability_gates"]["programming"], {"ready", "conditional", "not_applicable"})
                self.assertEqual(card["historical_use"]["status"], "owner_confirmed")

    def test_sensor_output_and_actuator_are_searchable_and_task_aware(self):
        search = execute_request({"action": "search", "query": "U 形槽光电计数"}, project_root=ROOT)
        sensor = execute_request({"action": "module_guide", "module": "超声波测距"}, project_root=ROOT)
        output = execute_request({"action": "project_task", "module": "1.3 寸 OLED 显示屏"}, project_root=ROOT)
        actuator = execute_request({"action": "project_task", "module": "四路直流电机驱动模块"}, project_root=ROOT)
        self.assertTrue(search["success"])
        self.assertEqual(search["matches"][0]["name"], "U 形槽光电计数器")
        self.assertTrue(sensor["success"])
        self.assertEqual(sensor["module"]["io_role"], "input")
        self.assertEqual(sensor["module"]["usability"], "guidance_ready")
        self.assertTrue(sensor["recipes"])
        self.assertEqual(output["generation_level"], "guidance_ready")
        self.assertTrue(output["candidate_recipes"])
        self.assertEqual(actuator["module"]["io_role"], "actuator")
        self.assertEqual(actuator["generation_level"], "guidance_ready")
        self.assertEqual(actuator["capability_gates"]["programming"], "conditional")
        self.assertEqual(actuator["acceptance"]["physical_effect_verified"], "unverified")

    def test_starcore_board_context_contains_all_22_companion_modules(self):
        opened = execute_request({"action": "open_board", "board_id": "idmc-0001-starcore-v4-2-2"}, project_root=ROOT)
        expected = {item["catalog_id"] for item in self.manifest["modules"] if item["hardware_id"] != "IDMC-0001"}
        actual = {item["id"] for item in opened["components"]}
        self.assertTrue(opened["success"])
        self.assertTrue(expected.issubset(actual))

    def test_conflict_and_non_programmable_states_keep_fact_level_gates(self):
        laser = execute_request({"action": "project_task", "module": "激光接收"}, project_root=ROOT)
        servo = execute_request({"action": "project_task", "module": "串口舵机驱动"}, project_root=ROOT)
        hub = execute_request({"action": "project_task", "module": "一分四 USB 集线器"}, project_root=ROOT)
        self.assertEqual(laser["generation_level"], "guidance_ready")
        self.assertEqual(laser["capability_gates"]["wiring"], "version_check")
        self.assertTrue(any("冲突" in item for item in laser["blocked_facts"]))
        self.assertEqual(servo["generation_level"], "guidance_ready")
        self.assertEqual(servo["capability_gates"]["programming"], "conditional")
        self.assertTrue(any("禁止生成运动命令" in item for item in servo["blocked_facts"]))
        self.assertEqual(hub["capability_gates"]["programming"], "not_applicable")
        self.assertTrue(any("不需要 Arduino 控制程序" in item for item in hub["steps"]))

    def test_existing_owned_recipe_modules_remain_connected(self):
        expected = {
            "IDMD-0001",
            "IDMD-0002",
            "IDMD-0021",
            "IDMS-0001",
            "IDMS-0003",
            "IDMS-0008",
            "IDMS-0009",
        }
        for hardware_id in expected:
            with self.subTest(hardware_id=hardware_id):
                guide = execute_request({"action": "module_guide", "module": hardware_id}, project_root=ROOT)
                self.assertTrue(guide["success"])
                self.assertEqual(guide["module"]["usability"], "guidance_ready")
                self.assertTrue(guide["recipes"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.cad import generator  # noqa: E402
from chatmaker.integrations import workbuddy_mcp  # noqa: E402


class ChatCadAlphaTests(unittest.TestCase):
    def test_lasermaker_and_default_wood_cards_are_available(self):
        result = generator.execute_request(
            {
                "action": "fabrication-profile",
                "equipment_id": "lasermaker-generic",
                "material_id": "wood-sheet-3mm",
            }
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["material"]["default_thickness_mm"], 3.0)
        self.assertEqual(
            {
                item["color_name"]: item["process_id"]
                for item in result["equipment"]["layer_rules"]
            },
            {
                "black": "cut-through",
                "red": "line-engrave",
                "yellow": "shallow-engrave",
                "blue": "deep-engrave",
            },
        )
        self.assertTrue(result["equipment"]["process_order"]["cut_layer_must_be_last"])
        self.assertEqual(
            result["equipment"]["parameter_policy"]["status"],
            "calibration-required",
        )
        self.assertIsNone(result["material"]["machine_parameters"]["power"])

    def test_four_board_profiles_are_available(self):
        result = generator.execute_request({"action": "list-profiles"})

        self.assertTrue(result["success"])
        self.assertEqual(
            {item["board_id"] for item in result["profiles"]},
            {
                "arduino-nano-classic",
                "arduino-uno-r3",
                "esp32-devkit-v1",
                "idmc-0001-starcore-v4-2-2",
            },
        )
        self.assertTrue(all(item["physical_fit"] == "unverified" for item in result["profiles"]))

    def test_uno_project_generates_editable_files_and_preview_lab(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generator.execute_request(
                {
                    "action": "generate",
                    "board_id": "arduino-uno-r3",
                    "project_name": "课堂安装底板",
                    "output_dir": directory,
                    "parameters": {"clearance": 6},
                }
            )

            self.assertTrue(result["success"], result)
            self.assertEqual(result["physical_fit"], "unverified")
            paths = {name: Path(path) for name, path in result["files"].items()}
            self.assertEqual(set(paths), {"project", "scad", "dxf", "svg", "stl", "preview_lab"})
            self.assertTrue(all(path.is_file() for path in paths.values()))
            self.assertIn("mounting_holes", paths["scad"].read_text(encoding="utf-8"))
            self.assertIn("SECTION", paths["dxf"].read_text(encoding="ascii"))
            self.assertTrue(paths["stl"].read_text(encoding="ascii").startswith("solid"))
            project = json.loads(paths["project"].read_text(encoding="utf-8"))
            self.assertEqual(project["parameters"]["clearance"], 6.0)
            self.assertEqual(project["parameters"]["plate_thickness"], 3.0)
            self.assertEqual(project["equipment_id"], "lasermaker-generic")
            self.assertEqual(project["material_id"], "wood-sheet-3mm")
            self.assertEqual(project["fabrication"]["parameter_policy"]["status"], "calibration-required")

            preview = paths["preview_lab"].read_text(encoding="utf-8")
            self.assertIn("右侧预览实验室", preview)
            for marker in ("clearance", "plateThickness", 'data-kind="dxf"', 'data-kind="svg"', 'data-kind="scad"', 'data-kind="stl"'):
                self.assertIn(marker, preview)

    def test_mcp_exposes_and_routes_cad_tools(self):
        names = {tool["name"] for tool in workbuddy_mcp.TOOLS}
        self.assertIn("cad_profile_get", names)
        self.assertIn("cad_fabrication_get", names)
        self.assertIn("cad_generate", names)

        response = workbuddy_mcp._tool_result(
            "cad_profile_get", {"board_id": "idmc-0001-starcore-v4-2-2"}
        )
        payload = json.loads(response["content"][0]["text"])
        self.assertFalse(response["isError"])
        self.assertEqual(payload["profile"]["revision"], "v4.2.2")

        fabrication_response = workbuddy_mcp._tool_result("cad_fabrication_get", {})
        fabrication_payload = json.loads(fabrication_response["content"][0]["text"])
        self.assertFalse(fabrication_response["isError"])
        self.assertEqual(fabrication_payload["material"]["default_thickness_mm"], 3.0)

    def test_mcp_exposes_bounded_basic_mechanical_parameters(self):
        tool = next(item for item in workbuddy_mcp.TOOLS if item["name"] == "cad_generate")
        parameters = tool["inputSchema"]["properties"]["parameters"]
        properties = parameters["properties"]

        self.assertEqual(tool["inputSchema"]["required"], ["project_name", "output_dir"])
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(
            properties["design_kind"]["enum"],
            ["enclosure", "gear_pair", "rack_and_pinion"],
        )
        self.assertEqual(properties["gear_module"], {"type": "number", "minimum": 0.5, "maximum": 5})
        self.assertEqual(properties["driver_teeth"], {"type": "integer", "minimum": 8, "maximum": 80})
        self.assertEqual(properties["driven_teeth"], {"type": "integer", "minimum": 8, "maximum": 120})
        self.assertEqual(properties["pinion_teeth"], {"type": "integer", "minimum": 8, "maximum": 80})
        self.assertEqual(properties["rack_teeth"], {"type": "integer", "minimum": 4, "maximum": 80})
        self.assertEqual(properties["pressure_angle"], {"type": "number", "minimum": 14.5, "maximum": 30})


if __name__ == "__main__":
    unittest.main()

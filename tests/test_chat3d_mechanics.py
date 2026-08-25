from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile
import unittest

from chatmaker.cad import generator


class Chat3DMechanicalBasicsTests(unittest.TestCase):
    def test_makerlab_delivery_returns_assembly_scad_without_writing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "must-not-exist"
            result = generator.generate_project(
                {
                    "mode": "chat3d",
                    "delivery_mode": "makerlab-code",
                    "project_name": "classroom-gears",
                    "output_dir": str(output),
                    "parameters": {
                        "design_kind": "gear_pair",
                        "driver_teeth": 12,
                        "driven_teeth": 24,
                    },
                }
            )

            self.assertTrue(result["success"], result)
            self.assertEqual(result["delivery_mode"], "makerlab-code")
            self.assertIn("module driver_gear", result["scad_code"])
            self.assertEqual(result["files"], {})
            self.assertEqual(result["model_generated"], "unverified")
            self.assertFalse(output.exists())

    def test_standalone_mechanism_does_not_require_an_unrelated_board(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project(
                {
                    "mode": "chat3d",
                    "project_name": "standalone-gears",
                    "output_dir": folder,
                    "parameters": {
                        "design_kind": "gear_pair",
                        "driver_teeth": 12,
                        "driven_teeth": 24,
                    },
                }
            )

            self.assertTrue(result["success"], result)
            project = json.loads(Path(result["files"]["project"]).read_text(encoding="utf-8"))
            self.assertIsNone(project["board_id"])

    def test_gear_pair_derives_ratio_center_distance_and_component_files(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project(
                {
                    "mode": "chat3d",
                    "board_id": "arduino-uno-r3",
                    "project_name": "classroom-gears",
                    "output_dir": folder,
                    "parameters": {
                        "design_kind": "gear_pair",
                        "gear_module": 2,
                        "driver_teeth": 12,
                        "driven_teeth": 24,
                        "shaft_diameter": 5,
                        "shaft_clearance": 0.2,
                        "backlash": 0.15,
                    },
                }
            )

            self.assertTrue(result["success"], result)
            project = json.loads(Path(result["files"]["project"]).read_text(encoding="utf-8"))
            derived = project["design_brief"]["derived"]
            self.assertEqual(derived["ratio"], 2.0)
            self.assertEqual(derived["driver_pitch_diameter"], 24.0)
            self.assertEqual(derived["driven_pitch_diameter"], 48.0)
            self.assertEqual(derived["center_distance"], 36.0)
            self.assertEqual(derived["bore_diameter"], 5.4)
            self.assertEqual(derived["driven_phase_degrees"], 7.5)
            self.assertEqual(project["checks"]["status"], "passed")
            self.assertEqual(
                {component["type"] for component in project["components"]},
                {"spur_gear", "shaft", "bushing", "bracket"},
            )
            for key in (
                "scad",
                "stl",
                "preview_lab",
                "driver_gear_scad",
                "driver_gear_stl",
                "driven_gear_scad",
                "driven_gear_stl",
                "shaft_scad",
                "shaft_stl",
                "bushing_scad",
                "bushing_stl",
                "bracket_scad",
                "bracket_stl",
            ):
                self.assertTrue(Path(result["files"][key]).is_file(), key)
            self.assertGreater(
                Path(result["files"]["driver_gear_stl"])
                .read_text(encoding="ascii")
                .count("facet normal"),
                100,
            )
            lab = Path(result["files"]["preview_lab"]).read_text(encoding="utf-8")
            for marker in (
                'id="driver_teeth"',
                'id="driven_teeth"',
                "function derive()",
                "center_distance",
                'data-export="assembly-scad"',
                'data-export="assembly-stl"',
                'data-component="driver_gear"',
                "function stl(",
                "Math.PI/s.driven_teeth",
            ):
                self.assertIn(marker, lab)

    def test_rack_and_pinion_share_pitch_and_static_position(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project(
                {
                    "mode": "chat3d",
                    "board_id": "arduino-nano-classic",
                    "project_name": "rack-demo",
                    "output_dir": folder,
                    "parameters": {
                        "design_kind": "rack_and_pinion",
                        "gear_module": 1.5,
                        "pinion_teeth": 16,
                        "rack_teeth": 12,
                        "pressure_angle": 20,
                    },
                }
            )

            self.assertTrue(result["success"], result)
            project = json.loads(Path(result["files"]["project"]).read_text(encoding="utf-8"))
            derived = project["design_brief"]["derived"]
            self.assertAlmostEqual(derived["circular_pitch"], math.pi * 1.5, places=6)
            self.assertAlmostEqual(derived["rack_length"], math.pi * 1.5 * 12, places=6)
            self.assertEqual(derived["pinion_pitch_radius"], 12.0)
            self.assertEqual(derived["pinion_center_to_rack_pitch_line"], 12.0)
            self.assertEqual(project["checks"]["status"], "passed")
            self.assertIn("rack_scad", result["files"])
            self.assertIn("rack_stl", result["files"])
            self.assertTrue(Path(result["files"]["rack_stl"]).is_file())
            lab = Path(result["files"]["preview_lab"]).read_text(encoding="utf-8")
            self.assertIn('id="pinion_teeth"', lab)
            self.assertIn('id="rack_teeth"', lab)
            self.assertIn('data-component="rack"', lab)

    def test_rejects_a_shaft_that_removes_the_gear_root(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project(
                {
                    "mode": "chat3d",
                    "board_id": "arduino-uno-r3",
                    "project_name": "bad-gear",
                    "output_dir": folder,
                    "parameters": {
                        "design_kind": "gear_pair",
                        "gear_module": 1,
                        "driver_teeth": 8,
                        "driven_teeth": 16,
                        "shaft_diameter": 6,
                    },
                }
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "cad_generation_failed")
        self.assertIn("shaft_diameter_too_large_for_driver_gear", result["detail"])

    def test_board_based_enclosure_still_requires_a_board(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project(
                {
                    "mode": "chat3d",
                    "project_name": "missing-board-box",
                    "output_dir": folder,
                }
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "invalid_board_id")


if __name__ == "__main__":
    unittest.main()

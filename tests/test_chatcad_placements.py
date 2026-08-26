from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from chatmaker.cad import generator


BOARD_ID = "idmc-0001-starcore-v4-2-2"
RGB = "idmd-0001-starcore-rgb-light"
OLED = "idmd-0021-starcore-oled-1-3"
ULTRASONIC = "idms-0009-starcore-ultrasonic"
LIMIT_SWITCH = "idms-0012-starcore-limit-switch"


class ChatcadPlacementTests(unittest.TestCase):
    def test_chat2d_placements_drive_chat3d_mounts_and_openings(self):
        with tempfile.TemporaryDirectory() as folder:
            two_d = generator.generate_project(
                {
                    "mode": "chat2d",
                    "board_id": BOARD_ID,
                    "project_name": "shared-layout",
                    "output_dir": str(Path(folder) / "two-d"),
                    "parameters": {
                        "dimension_mode": "internal",
                        "box_width": 190,
                        "box_depth": 140,
                        "box_height": 45,
                        "component_ids": [RGB, OLED, ULTRASONIC],
                    },
                }
            )
            self.assertTrue(two_d["success"], two_d)
            project = json.loads(
                Path(two_d["files"]["project"]).read_text(encoding="utf-8")
            )
            placements = project["parameters"]["placements"]
            three_d = generator.generate_project(
                {
                    "mode": "chat3d",
                    "delivery_mode": "makerlab-code",
                    "generation_confirmed": True,
                    "board_id": BOARD_ID,
                    "project_name": "shared-layout-3d",
                    "parameters": {
                        "inner_width": 190,
                        "inner_depth": 140,
                        "inner_height": 45,
                        "placements": placements,
                    },
                }
            )

        self.assertTrue(three_d["success"], three_d)
        self.assertEqual(three_d["placements"], placements)
        self.assertTrue(three_d["layout_validation"]["ok"])
        self.assertIn("base_mount_points", three_d["scad_code"])
        self.assertIn("lid_mount_points", three_d["scad_code"])
        self.assertIn("idmd-0021-starcore-oled-1-3", three_d["scad_code"])
        self.assertIn("idms-0009-starcore-ultrasonic", three_d["scad_code"])
        self.assertIn("lid_cutouts", three_d["scad_code"])

    def test_automatic_layout_is_deterministic_and_collision_checked(self):
        request = {
            "mode": "chat3d",
            "delivery_mode": "makerlab-code",
            "generation_confirmed": True,
            "board_id": BOARD_ID,
            "project_name": "auto-layout",
            "parameters": {"component_ids": [RGB, OLED, ULTRASONIC]},
        }
        first = generator.generate_project(request)
        second = generator.generate_project(request)
        self.assertTrue(first["success"], first)
        self.assertEqual(first["placements"], second["placements"])
        self.assertEqual(len(first["placements"]), 4)
        self.assertTrue(first["layout_validation"]["ok"])

    def test_overlapping_explicit_placements_are_rejected(self):
        result = generator.generate_project(
            {
                "mode": "chat3d",
                "delivery_mode": "makerlab-code",
                "generation_confirmed": True,
                "board_id": BOARD_ID,
                "parameters": {
                    "inner_width": 180,
                    "inner_depth": 130,
                    "placements": [
                        {"item_id": BOARD_ID, "face": "bottom", "x": 0, "y": 0, "rotation": 0},
                        {"item_id": RGB, "face": "bottom", "x": 0, "y": 0, "rotation": 0},
                    ],
                },
            }
        )
        self.assertFalse(result["success"])
        self.assertIn("placement_validation_failed", result["detail"])

    def test_limit_switch_uses_dxf_reviewed_mounting_holes_without_inventing_cutout(self):
        result = generator.generate_project(
            {
                "mode": "chat3d",
                "delivery_mode": "makerlab-code",
                "generation_confirmed": True,
                "board_id": BOARD_ID,
                "parameters": {
                    "inner_width": 180,
                    "inner_depth": 130,
                    "placements": [
                        {"item_id": BOARD_ID, "face": "bottom", "x": 0, "y": 0, "rotation": 0},
                        {"item_id": LIMIT_SWITCH, "face": "top", "x": 45, "y": 30, "rotation": 0},
                    ],
                },
            }
        )
        self.assertTrue(result["success"], result)
        self.assertIn(
            "lid_mount_points = [[35.0,20.0],[55.0,20.0],[55.0,40.0],[35.0,40.0]];",
            result["scad_code"],
        )
        self.assertFalse(
            any(LIMIT_SWITCH in warning for warning in result["layout_validation"]["warnings"])
        )
        self.assertNotIn("limit_switch_motion", result["scad_code"])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from chatmaker.cad import generator


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "chatcad" / "starcore-smart-sensing-enclosure"


class Chat3DTests(unittest.TestCase):
    def test_makerlab_code_without_label_has_no_undefined_label_modules(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project(
                {
                    "mode": "chat3d",
                    "delivery_mode": "makerlab-code",
                    "board_id": "arduino-uno-r3",
                    "project_name": "plain-case",
                    "output_dir": str(Path(folder) / "must-not-exist"),
                }
            )

        self.assertTrue(result["success"], result)
        self.assertNotIn("label_on(", result["scad_code"])
        self.assertNotIn("label_glyphs(", result["scad_code"])

    def test_generates_printable_enclosure_and_rotatable_lab(self):
        with tempfile.TemporaryDirectory() as folder:
            result=generator.generate_project({"mode":"chat3d","board_id":"idmc-0001-starcore-v4-2-2","project_name":"starcore-case","output_dir":folder,"parameters":{"wall":2.8}})
            self.assertTrue(result["success"],result)
            self.assertEqual(set(result["files"]),{"project","scad","stl","preview_lab"})
            project=json.loads(Path(result["files"]["project"]).read_text(encoding="utf-8"))
            scad=Path(result["files"]["scad"]).read_text(encoding="utf-8")
            stl=Path(result["files"]["stl"]).read_text(encoding="ascii")
            preview=Path(result["files"]["preview_lab"]).read_text(encoding="utf-8")
        self.assertEqual(project["parameters"]["wall"],2.8)
        self.assertIn("difference()",scad)
        self.assertEqual(result["scad_code"],scad)
        self.assertEqual(result["preview_lab"],result["files"]["preview_lab"])
        self.assertTrue(stl.startswith("solid"))
        self.assertIn("拖拽旋转",preview)
        self.assertIn("onwheel",preview)
        self.assertIn("background:#fff",preview)
        self.assertEqual(result["file_opened"],"unverified")

    def test_generates_adjustable_side_wire_exit(self):
        result = generator.generate_project(
            {
                "mode": "chat3d",
                "delivery_mode": "makerlab-code",
                "generation_confirmed": True,
                "board_id": "idmc-0001-starcore-v4-2-2",
                "parameters": {
                    "inner_width": 180,
                    "inner_depth": 130,
                    "inner_height": 45,
                    "side_openings": [
                        {
                            "face": "front",
                            "position": 28,
                            "z": 11,
                            "width": 22,
                            "height": 9,
                            "clearance": 0.4,
                            "label": "USB 与线束出口",
                        }
                    ],
                },
            }
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["side_openings"][0]["face"], "front")
        self.assertIn('wire_exit_1_face = "front"', result["scad_code"])
        self.assertIn("module side_opening_cutout", result["scad_code"])
        self.assertIn("side_opening_cutout(wire_exit_1_face", result["scad_code"])

    def test_rejects_side_wire_exit_outside_face(self):
        result = generator.generate_project(
            {
                "mode": "chat3d",
                "delivery_mode": "makerlab-code",
                "generation_confirmed": True,
                "board_id": "idmc-0001-starcore-v4-2-2",
                "parameters": {
                    "inner_width": 100,
                    "inner_depth": 80,
                    "side_openings": [
                        {"face": "front", "position": 48, "z": 10, "width": 20, "height": 8}
                    ],
                },
            }
        )

        self.assertFalse(result["success"])
        self.assertIn("side_opening_out_of_bounds", result["detail"])

    def test_starcore_sensing_box_example_regenerates_with_controls_and_cutouts(self):
        request = json.loads((EXAMPLE / "request.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            request["output_dir"] = folder
            result = generator.generate_project(request)
            self.assertTrue(result["success"], result)
            preview = Path(result["files"]["preview_lab"]).read_text(encoding="utf-8")
            scad = Path(result["files"]["scad"]).read_text(encoding="utf-8")
            stl = Path(result["files"]["stl"]).read_text(encoding="ascii")

        self.assertIn("wire${n}face", preview)
        self.assertIn("drawWireExit", preview)
        self.assertIn("placementAwareScad", preview)
        self.assertIn("label_glyphs", scad)
        self.assertIn("lid_mount_points", scad)
        self.assertIn("side_opening_cutout(wire_exit_1_face", scad)
        self.assertIn("idms-0009-starcore-ultrasonic", scad)
        self.assertTrue(stl.startswith("solid starcore-smart-sensing-enclosure"))
        self.assertTrue(stl.rstrip().endswith("endsolid starcore-smart-sensing-enclosure"))


if __name__ == "__main__": unittest.main()

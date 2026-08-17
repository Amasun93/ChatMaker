import json
import tempfile
import unittest
from pathlib import Path

from chatmaker.cad import generator


class Chat2DTests(unittest.TestCase):
    def test_generates_laser_box_editor_and_layered_files(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project({"mode":"chat2d","board_id":"arduino-uno-r3","project_name":"uno-box","output_dir":folder,"parameters":{"box_width":140}})
            self.assertTrue(result["success"], result)
            self.assertEqual(set(result["files"]), {"project","svg","dxf","preview_lab"})
            project=json.loads(Path(result["files"]["project"]).read_text(encoding="utf-8"))
            preview=Path(result["files"]["preview_lab"]).read_text(encoding="utf-8")
            dxf=Path(result["files"]["dxf"]).read_text(encoding="utf-8")
        self.assertEqual(project["parameters"]["material_thickness"],3.0)
        self.assertEqual(project["parameters"]["joint_size"],10.0)
        self.assertEqual(project["parameters"]["box_width"],140.0)
        self.assertIn("添加自定义模块",preview)
        self.assertIn("三维组装预览",preview)
        self.assertIn("background:#fff",preview)
        self.assertIn("BLACK_CUT_THROUGH",dxf)
        self.assertIn("RED_LINE_ENGRAVE",dxf)
        self.assertGreater(dxf.count("0\nLINE\n8\nBLACK_CUT_THROUGH"),24)
        self.assertIn("榫槽大小",preview)
        self.assertEqual(result["physical_fit"],"unverified")


if __name__ == "__main__": unittest.main()

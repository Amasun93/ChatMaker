import json
import tempfile
import unittest
from pathlib import Path

from chatmaker.cad import generator


class Chat3DTests(unittest.TestCase):
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
        self.assertTrue(stl.startswith("solid"))
        self.assertIn("拖拽旋转",preview)
        self.assertIn("onwheel",preview)
        self.assertIn("background:#fff",preview)
        self.assertEqual(result["file_opened"],"unverified")


if __name__ == "__main__": unittest.main()

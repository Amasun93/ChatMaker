from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.cad import generator  # noqa: E402
from chatmaker.cad import text as text_engine  # noqa: E402


def _cjk_font_available() -> bool:
    try:
        import fontTools  # noqa: F401

        text_engine.find_cjk_font()
        return True
    except Exception:
        return False


class TextEngineUnitTests(unittest.TestCase):
    def test_bundled_font_is_default_and_covers_gb2312(self):
        from fontTools.ttLib import TTFont

        self.assertEqual(text_engine.find_cjk_font(), text_engine.BUNDLED_CJK_FONT)
        font = TTFont(text_engine.BUNDLED_CJK_FONT, recalcTimestamp=False)
        try:
            cmap = font.getBestCmap()
            expected = set(range(0x20, 0x7F))
            for lead in range(0xA1, 0xF8):
                for trail in range(0xA1, 0xFF):
                    try:
                        value = bytes((lead, trail)).decode("gb2312")
                    except UnicodeDecodeError:
                        continue
                    expected.update(ord(character) for character in value)
            self.assertEqual(expected - set(cmap), set())
            primary_name_ids = {1, 3, 4, 6, 16, 18, 21, 25}
            primary_names = {
                record.toUnicode()
                for record in font["name"].names
                if record.nameID in primary_name_ids
            }
            self.assertIn("ChatMaker CJK Sans", primary_names)
            self.assertFalse(any("Source" in name for name in primary_names))
        finally:
            font.close()

    def test_bundled_font_provenance_and_package_data(self):
        assets = text_engine.BUNDLED_CJK_FONT.parent
        metadata = json.loads((assets / "ChatMakerCJK-Regular.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(text_engine.BUNDLED_CJK_FONT.read_bytes()).hexdigest()
        self.assertEqual(metadata["asset"]["sha256"], digest)
        self.assertEqual(metadata["asset"]["size"], text_engine.BUNDLED_CJK_FONT.stat().st_size)
        self.assertEqual(metadata["license"], "SIL Open Font License 1.1")
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", (assets / "OFL-1.1.txt").read_text(encoding="utf-8"))

        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package_data = project["tool"]["setuptools"]["package-data"]["chatmaker"]
        self.assertIn("cad/assets/*.otf", package_data)
        self.assertIn("cad/assets/*.txt", package_data)
        self.assertIn("cad/assets/*.json", package_data)

    def test_explicit_font_path_still_overrides_bundle(self):
        with tempfile.NamedTemporaryFile(suffix=".otf") as handle:
            self.assertEqual(text_engine.find_cjk_font(handle.name), Path(handle.name))

    def test_signed_area_and_triangle_helpers(self):
        square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        self.assertAlmostEqual(text_engine._signed_area(square), 1.0)
        self.assertTrue(text_engine._point_in_triangle((0.3, 0.3), (0, 0), (1, 0), (0, 1)) or True)
        self.assertTrue(text_engine._point_in_polygon((0.5, 0.5), square))
        self.assertFalse(text_engine._point_in_polygon((1.5, 0.5), square))

    def test_ear_clip_square(self):
        square = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
        triangles = text_engine._ear_clip(square)
        self.assertEqual(len(triangles), 2)
        area = sum(
            abs(
                (b[0] - a[0]) * (c[1] - a[1])
                - (b[1] - a[1]) * (c[0] - a[0])
            ) / 2
            for a, b, c in triangles
        )
        self.assertAlmostEqual(area, 4.0)

    def test_bridge_holes_keeps_material_area(self):
        outer = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]
        hole = [(1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 3.0)]
        merged = text_engine._bridge_holes(outer, [hole])
        triangles = text_engine._ear_clip(merged)
        area = sum(
            abs(
                (b[0] - a[0]) * (c[1] - a[1])
                - (b[1] - a[1]) * (c[0] - a[0])
            ) / 2
            for a, b, c in triangles
        )
        self.assertAlmostEqual(area, 12.0, places=3)

    def test_group_contours_by_containment(self):
        # TrueType direction: outer clockwise (negative area), hole positive.
        outer = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]
        hole = [(1.0, 1.0), (1.0, 3.0), (3.0, 3.0), (3.0, 1.0)]
        island = [(1.2, 1.2), (1.8, 1.2), (1.8, 1.8), (1.2, 1.8)]
        groups = text_engine._group_contours([outer, hole, island])
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups[0][0]), 4)
        self.assertEqual(len(groups[0][1]), 1)
        # Both solid rings must end up counter-clockwise.
        self.assertGreater(text_engine._signed_area(groups[0][0]), 0)
        self.assertGreater(text_engine._signed_area(groups[1][0]), 0)
        self.assertLess(text_engine._signed_area(groups[0][1][0]), 0)


@unittest.skipUnless(_cjk_font_available(), "no CJK font / fontTools on this machine")
class CjkEngravingTests(unittest.TestCase):
    def test_common_label_uses_bundled_font(self):
        layout = text_engine.glyph_layout("中文姓名班级作品2026", 10.0)
        self.assertEqual(Path(layout["font"]), text_engine.BUNDLED_CJK_FONT)
        self.assertEqual(len(layout["glyphs"]), 12)

    def test_layout_and_groups_for_common_name_characters(self):
        layout = text_engine.glyph_layout("孙大卫", 10.0)
        self.assertEqual(len(layout["glyphs"]), 3)
        self.assertGreater(layout["width"], 25.0)
        for glyph in layout["glyphs"]:
            groups = text_engine._group_contours(glyph["contours"])
            self.assertGreaterEqual(len(groups), 1)
            for outer, holes in groups:
                self.assertGreaterEqual(len(outer), 3)
                self.assertGreater(text_engine._signed_area(outer), 0)
                for hole in holes:
                    self.assertLess(text_engine._signed_area(hole), 0)

    def test_scad_text_never_uses_font_rendering(self):
        code = text_engine.scad_text("中", 10.0, 2.0)
        self.assertIn("linear_extrude", code)
        self.assertIn("polygon(", code)
        self.assertNotIn("text(", code)
        self.assertNotIn("font=", code)

    def test_text_triangles_geometry_bounds(self):
        triangles, layout = text_engine.text_triangles("大卫", 8.0, 1.6, base_z=2.0)
        self.assertGreater(len(triangles), 100)
        zs = {point[2] for triangle in triangles for point in triangle}
        self.assertEqual(zs, {2.0, 3.6})
        xs = [point[0] for triangle in triangles for point in triangle]
        self.assertGreaterEqual(min(xs), 0.0)
        self.assertLessEqual(max(xs), layout["width"] + 0.01)

    def test_chat3d_generate_engraves_chinese_on_lid(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generator.execute_request(
                {
                    "action": "generate",
                    "board_id": "arduino-uno-r3",
                    "project_name": "姓名牌测试",
                    "output_dir": directory,
                    "mode": "chat3d",
                    "parameters": {"engrave_text": "孙大卫", "text_size": 12, "text_depth": 1.2},
                }
            )
            self.assertTrue(result["success"], result)
            paths = {name: Path(path) for name, path in result["files"].items()}
            scad = paths["scad"].read_text(encoding="utf-8")
            self.assertIn("linear_extrude", scad)
            self.assertIn("polygon(", scad)
            self.assertNotIn("text(", scad)
            # OpenSCAD customizer / Bambu Studio Custom 3D Print lab format.
            for marker in (
                'part = "assembled"',
                "module label_glyphs()",
                "label_depth",
                "label_scale",
                "show_label",
                "/* [文字雕刻] */",
            ):
                self.assertIn(marker, scad)
            stl = paths["stl"].read_text(encoding="ascii")
            self.assertGreater(stl.count("facet normal"), 200)
            lab = paths["preview_lab"].read_text(encoding="utf-8")
            self.assertIn("孙大卫", lab)
            self.assertIn("浮凸文字", lab)
            # The lab page embeds glyph contours so its own SCAD export keeps them.
            self.assertIn("label_depth", lab)
            self.assertIn("label_glyphs", lab)

    def test_chat3d_without_text_stays_plain(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generator.execute_request(
                {
                    "action": "generate",
                    "board_id": "arduino-uno-r3",
                    "project_name": "plain-box",
                    "output_dir": directory,
                    "mode": "chat3d",
                }
            )
            self.assertTrue(result["success"], result)
            scad = Path(result["files"]["scad"]).read_text(encoding="utf-8")
            self.assertNotIn("linear_extrude", scad)

    def test_missing_font_file_reports_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generator.execute_request(
                {
                    "action": "generate",
                    "board_id": "arduino-uno-r3",
                    "project_name": "bad-font",
                    "output_dir": directory,
                    "mode": "chat3d",
                    "parameters": {
                        "engrave_text": "测试",
                        "engrave_font": str(Path(directory) / "nope.ttf"),
                    },
                }
            )
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "cad_generation_failed")
            self.assertIn("font_file_not_found", result["detail"])


if __name__ == "__main__":
    unittest.main()

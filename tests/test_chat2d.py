import json
import math
import re
import tempfile
import unittest
from pathlib import Path

from chatmaker.cad import box_model, chat2d, generator
from chatmaker.cad.profiles import get_profile


class Chat2DTests(unittest.TestCase):
    def setUp(self):
        self.profile = get_profile("arduino-uno-r3")["profile"]

    def test_parameterized_box_has_six_orthogonal_closed_contours(self):
        geometry = chat2d.geometry(
            self.profile,
            {
                "box_width": 140,
                "box_depth": 95,
                "box_height": 55,
                "joint_size_length": 14,
                "joint_size_width": 11,
                "joint_size_height": 8,
                "laser_compensation": 0.15,
            },
            3,
        )
        panels = box_model.panels(geometry)
        self.assertEqual(len(panels), 6)
        for panel in panels:
            with self.subTest(panel=panel["name"]):
                points = box_model.panel_outline(panel, geometry)
                self.assertGreater(len(points), 12)
                self.assertEqual(box_model.diagonal_segments(points), [])
                self.assertTrue(
                    math.isclose(points[-1][0], points[0][0])
                    or math.isclose(points[-1][1], points[0][1])
                )

    def test_mating_edges_are_complementary_and_compensation_changes_fit(self):
        self.assertTrue(all(edge[1] == "male" for edge in box_model.EDGE_CONTRACT["top"]))
        self.assertEqual(box_model.EDGE_CONTRACT["front"][0][1], "female")
        self.assertEqual(box_model.EDGE_CONTRACT["front"][1][1], "male")
        self.assertTrue(all(edge[1] == "female" for edge in box_model.EDGE_CONTRACT["left"]))

        male = box_model.finger_intervals(100, 12, 3, "male", 0.2)[0]
        female = box_model.finger_intervals(100, 12, 3, "female", 0.2)[0]
        self.assertGreater(male[1] - male[0], female[1] - female[0])

    def test_internal_dimensions_and_optional_lids(self):
        geometry = chat2d.geometry(
            self.profile,
            {
                "dimension_mode": "internal",
                "box_width": 140,
                "box_depth": 90,
                "box_height": 50,
                "material_thickness": 3,
                "include_top": False,
            },
            3,
        )
        self.assertEqual(geometry["inner_width"], 140)
        self.assertEqual(geometry["outer_width"], 146)
        self.assertEqual(geometry["outer_depth"], 96)
        self.assertEqual(geometry["outer_height"], 56)
        self.assertNotIn("top", {panel["name"] for panel in box_model.panels(geometry)})

    def test_generates_direct_manipulation_editor_and_visual_library(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project(
                {
                    "mode": "chat2d",
                    "board_id": "arduino-uno-r3",
                    "project_name": "uno-box",
                    "output_dir": folder,
                    "parameters": {"box_width": 140, "box_depth": 95},
                }
            )
            self.assertTrue(result["success"], result)
            project = json.loads(Path(result["files"]["project"]).read_text(encoding="utf-8"))
            preview = Path(result["files"]["preview_lab"]).read_text(encoding="utf-8")
            svg = Path(result["files"]["svg"]).read_text(encoding="utf-8")
            dxf = Path(result["files"]["dxf"]).read_text(encoding="utf-8")

        library = project["parameters"]["library"]
        self.assertEqual(len(library), 26)
        self.assertEqual(len([item for item in library if item["kind"] == "board"]), 4)
        self.assertEqual(len([item for item in library if item["kind"] == "component"]), 22)
        self.assertTrue(all("visual" in item for item in library))
        oled = next(item for item in library if item["id"] == "idmd-0021-starcore-oled-1-3")
        ultrasonic = next(item for item in library if item["id"] == "idms-0009-starcore-ultrasonic")
        rgb = next(item for item in library if item["id"] == "idmd-0001-starcore-rgb-light")
        self.assertEqual(oled["visual"]["features"][0]["shape"], "rect")
        self.assertEqual(ultrasonic["visual"]["features"][0]["shape"], "dual_round")
        self.assertEqual(len(rgb["visual"]["center_marks"]), 4)
        self.assertEqual(rgb["holes"], [])

        for hook in (
            "function templateSvg",
            "function startLibraryDrag",
            "function updateDrag",
            "function finishDrag",
            "function hitPanel",
            "drag-invalid",
            "拖到任意板面",
            "导出 3D 配置",
            "function canonicalPlacements",
            "function projectRequest",
        ):
            self.assertIn(hook, preview)
        self.assertNotIn("已放置模块", preview)
        self.assertNotIn('data-prop="panel"', preview)
        self.assertNotIn("添加实测孔位", preview)
        self.assertNotIn("<h2>安装孔</h2>", preview)
        self.assertIn("显示板件名称和尺寸", preview)
        self.assertIn("window.chat2d", preview)

        self.assertEqual(svg.count('data-panel="'), 6)
        for point_text in re.findall(r'<polygon data-panel="[^"]+" points="([^"]+)"', svg):
            points = [tuple(map(float, pair.split(","))) for pair in point_text.split()]
            self.assertEqual(box_model.diagonal_segments(points), [])
        self.assertIn("BLACK_CUT_THROUGH", dxf)
        self.assertIn("RED_LINE_ENGRAVE", dxf)
        self.assertEqual(result["model_generated"], "verified")
        self.assertEqual(result["file_opened"], "unverified")
        self.assertEqual(result["physical_fit"], "unverified")
        self.assertEqual(project["parameters"]["placements"][0]["face"], "bottom")

    def test_library_uses_beginner_names_and_series_filters(self):
        library = chat2d._library()
        by_id = {item["id"]: item for item in library}

        self.assertEqual(by_id["arduino-uno-r3"]["name"], "Arduino UNO")
        self.assertEqual(by_id["arduino-nano-classic"]["name"], "Arduino Nano")
        self.assertEqual(by_id["esp32-devkit-v1"]["name"], "ESP32 开发板")
        self.assertEqual(by_id["idmc-0001-starcore-v4-2-2"]["name"], "星核板")
        self.assertEqual(
            by_id["idms-0008-starcore-dht11"]["name"],
            "DHT11 温湿度传感器",
        )
        self.assertIn("open-hardware", by_id["arduino-uno-r3"]["series"])
        self.assertIn("starcore", by_id["idmc-0001-starcore-v4-2-2"]["series"])
        self.assertIn("starcore", by_id["idms-0008-starcore-dht11"]["series"])
        self.assertIn("sensor", by_id["idms-0008-starcore-dht11"]["series"])
        self.assertTrue(
            all(not re.search(r"\bIDM[A-Z]-\d+\b", item["name"]) for item in library)
        )

        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project(
                {
                    "mode": "chat2d",
                    "board_id": "arduino-uno-r3",
                    "project_name": "friendly-library",
                    "output_dir": folder,
                }
            )
            self.assertTrue(result["success"], result)
            preview = Path(result["files"]["preview_lab"]).read_text(encoding="utf-8")

        self.assertIn('id="librarySeries"', preview)
        self.assertIn('<option value="open-hardware"', preview)
        self.assertIn('<option value="starcore"', preview)
        self.assertIn('<option value="sensor"', preview)
        self.assertNotIn('id="libraryKind"', preview)

    def test_label_toggle_removes_text_from_initial_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generator.generate_project(
                {
                    "mode": "chat2d",
                    "board_id": "arduino-uno-r3",
                    "project_name": "clean-cut",
                    "output_dir": folder,
                    "parameters": {"include_panel_labels": False},
                }
            )
            self.assertTrue(result["success"], result)
            svg = Path(result["files"]["svg"]).read_text(encoding="utf-8")
            dxf = Path(result["files"]["dxf"]).read_text(encoding="utf-8")
        self.assertNotIn("顶板", svg)
        self.assertNotIn("底板", svg)
        self.assertNotIn("顶板", dxf)
        self.assertNotIn("底板", dxf)
        self.assertIn('data-panel="top"', svg)


if __name__ == "__main__":
    unittest.main()

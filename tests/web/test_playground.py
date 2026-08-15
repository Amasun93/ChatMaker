from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.web.playground import PlaygroundRequest, generate_playground  # noqa: E402


class AdvancedPlaygroundTests(unittest.TestCase):
    def test_playground_refuses_implicit_beginner_use(self):
        request = PlaygroundRequest(
            kind="classroom-tool",
            title="课堂方向游乐场",
            brief="比较同一个课堂反馈想法的不同体验",
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "explicit advanced opt-in"):
                generate_playground(request, Path(directory) / "playground.html")

    def test_advanced_playground_writes_one_accessible_dependency_free_html_file(self):
        request = PlaygroundRequest(
            kind="classroom-tool",
            title="课堂方向游乐场",
            brief="比较同一个课堂反馈想法的不同体验",
            advanced=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "playground.html"

            project = generate_playground(request, output)
            text = output.read_text(encoding="utf-8")

        self.assertEqual(project.path, output)
        self.assertGreaterEqual(len(project.direction_ids), 5)
        self.assertIn("<style>", text)
        self.assertIn("<script>", text)
        self.assertNotRegex(text, r"(?i)https?://|<(?:script|link)[^>]+(?:src|href)=")
        self.assertRegex(text, r"min-height\s*:\s*(?:4[4-9]|[5-9]\d)px")
        self.assertIn(":focus-visible", text)
        self.assertIn("prefers-reduced-motion", text)
        self.assertFalse(any(line != line.rstrip() for line in text.splitlines()))
        for forbidden_font in ("Inter", "Roboto", "Arial"):
            self.assertNotIn(forbidden_font, text)

    def test_hardware_playground_labels_every_comparison_as_simulation(self):
        request = PlaygroundRequest(
            kind="hardware-interface",
            title="设备界面方向游乐场",
            brief="比较传感器状态与灯光控制方向",
            advanced=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "hardware-playground.html"

            project = generate_playground(request, output)
            text = output.read_text(encoding="utf-8")

        self.assertIn("模拟比较", text)
        self.assertIn("不代表任何硬件已经连接", text)
        self.assertEqual(project.evidence["hardware_connectivity"], "unverified")


if __name__ == "__main__":
    unittest.main()

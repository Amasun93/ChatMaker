from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.web.generator import WebProjectRequest, generate_single_file  # noqa: E402


class SingleFileGeneratorTests(unittest.TestCase):
    def request(self) -> WebProjectRequest:
        return WebProjectRequest(
            kind="classroom-tool",
            title="课堂脉冲",
            prompt="今天哪一步最需要再讲一次？",
            primary_label="我需要再讲一次",
            direction_id="editorial-signal",
        )

    def test_generator_writes_one_self_contained_html_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "classroom-pulse.html"

            project = generate_single_file(self.request(), output)
            text = output.read_text(encoding="utf-8")

        self.assertEqual(project.path, output)
        self.assertIn("<style>", text)
        self.assertIn("<script>", text)
        self.assertNotIn("https://", text)
        self.assertIn('data-state="ready"', text)
        self.assertIn('aria-live="polite"', text)
        self.assertIn('data-template="spatial-glass"', text)
        self.assertIn("prefers-reduced-motion", text)

    def test_generator_escapes_user_text(self):
        request = replace(self.request(), title='<script id="attack">bad()</script>')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "safe.html"

            generate_single_file(request, output)
            text = output.read_text(encoding="utf-8")

        self.assertNotIn('<script id="attack">', text)
        self.assertIn("&lt;script", text)

    def test_hardware_page_starts_disconnected_and_labels_simulation(self):
        request = WebProjectRequest(
            kind="hardware-interface",
            title="灯光控制台",
            prompt="先连接模拟设备，再测试开关。",
            primary_label="连接模拟设备",
            direction_id="device-console",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "hardware-console.html"

            project = generate_single_file(request, output)
            text = output.read_text(encoding="utf-8")

        self.assertIn('data-state="disconnected"', text)
        self.assertIn('data-mode="simulation"', text)
        self.assertIn("模拟设备未连接", text)
        self.assertIn('data-template="mission-console"', text)
        self.assertIn("LIVE SIGNAL", text)
        self.assertEqual(project.evidence["hardware_connectivity"], "unverified")

    def test_omitted_direction_selects_the_flagship_for_each_kind(self):
        cases = (
            ("classroom-tool", "spatial-glass", "editorial-signal"),
            ("hardware-interface", "mission-console", "device-console"),
            ("mini-game", 'data-game="reaction-rush"', "reaction-rush"),
        )
        for kind, marker, direction_id in cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "auto.html"
                project = generate_single_file(
                    WebProjectRequest(
                        kind=kind,
                        title="一句话作品",
                        prompt="自动选择最合适的高级效果。",
                        primary_label="开始体验",
                    ),
                    output,
                )
                text = output.read_text(encoding="utf-8")

            self.assertIn(marker, text)
            self.assertEqual(project.direction_id, direction_id)
            self.assertNotIn("https://", text)

    def test_each_beginner_game_pattern_generates_a_playable_single_file(self):
        for direction_id in ("reaction-rush", "dodge-collect", "drag-puzzle"):
            with self.subTest(direction_id=direction_id), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / f"{direction_id}.html"
                project = generate_single_file(
                    WebProjectRequest(
                        kind="mini-game",
                        title="星星挑战",
                        prompt="收集星星，避开干扰。",
                        primary_label="开始游戏",
                        direction_id=direction_id,
                    ),
                    output,
                )
                text = output.read_text(encoding="utf-8")

            self.assertIn('data-kind="mini-game"', text)
            self.assertIn(f'data-game="{direction_id}"', text)
            self.assertIn("重新开始", text)
            self.assertIn("游戏结束", text)
            self.assertNotIn("https://", text)
            self.assertEqual(project.evidence["browser_interaction"], "unverified")
            self.assertEqual(project.evidence["hardware_connectivity"], "not_applicable")


if __name__ == "__main__":
    unittest.main()

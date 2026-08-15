from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "examples" / "chatweb" / "esp32-ap-control.html"


class Esp32ApControlPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8") if PAGE.exists() else ""

    def test_expected_page_exists(self):
        self.assertTrue(PAGE.is_file(), f"missing page: {PAGE}")

    def test_page_is_a_self_contained_mobile_document(self):
        self.assertRegex(self.html, r"(?i)<!doctype html>")
        self.assertIn('lang="zh-CN"', self.html)
        self.assertIn('name="viewport"', self.html)
        self.assertIn("<style>", self.html)
        self.assertIn("<script>", self.html)
        self.assertNotRegex(self.html, r"(?i)<(?:script|link)[^>]+(?:src|href)=")
        self.assertNotRegex(self.html, r"https?://")

    def test_controls_are_touch_sized_and_keyboard_visible(self):
        self.assertRegex(
            self.html,
            r"(?s)(?:button|\.mode-button)[^{]*\{[^}]*min-height\s*:\s*(?:4[4-9]|[5-9]\d)px",
        )
        self.assertIn(":focus-visible", self.html)
        self.assertIn("prefers-reduced-motion", self.html)
        self.assertIn('aria-live="polite"', self.html)

    def test_mobile_metric_grid_has_no_empty_fourth_cell(self):
        self.assertRegex(
            self.html,
            r"\.metric:last-child\s*\{\s*grid-column\s*:\s*1\s*/\s*-1\s*;\s*\}",
        )
        self.assertRegex(
            self.html,
            r"(?s)@media\s*\(min-width:\s*620px\).*?\.metric:last-child\s*\{\s*grid-column\s*:\s*auto\s*;\s*\}",
        )

    def test_page_starts_disconnected_and_declares_all_visible_states(self):
        self.assertIn('data-state="disconnected"', self.html)
        self.assertRegex(self.html, r'id="connection-status"[^>]*>[^<]*(?:未连接|断开)')
        for state in ("loading", "connected", "error"):
            with self.subTest(state=state):
                self.assertIn(f'"{state}"', self.html)

    def test_simulation_is_explicitly_labeled_as_preview_only(self):
        self.assertIn("模拟预览", self.html)
        self.assertRegex(self.html, r"模拟[^<\n]*(?:仅|只)[^<\n]*页面[^<\n]*(?:预览|演示)")
        self.assertIn('data-mode="real"', self.html)
        self.assertIn('id="mode-simulation"', self.html)

    def test_real_mode_uses_the_fixed_same_origin_api_contract(self):
        self.assertRegex(self.html, r'fetch\(\s*["\']/api/state["\']')
        self.assertRegex(self.html, r'fetch\(\s*["\']/api/led["\']')
        self.assertRegex(self.html, r'method\s*:\s*["\']POST["\']')
        self.assertRegex(self.html, r'Content-Type["\']?\s*:\s*["\']application/json["\']')
        self.assertRegex(self.html, r'JSON\.stringify\(\s*\{\s*on\s*:')
        for field in ("schema_version", "led_on", "sensor_raw", "uptime_ms"):
            with self.subTest(field=field):
                self.assertIn(field, self.html)

    def test_led_control_cannot_claim_success_while_disconnected(self):
        self.assertIn('id="led-control"', self.html)
        self.assertRegex(self.html, r'id="led-control"[^>]*disabled')
        self.assertRegex(self.html, r"ledControl\.disabled\s*=\s*state\s*!==\s*[\"\']connected[\"\']")


if __name__ == "__main__":
    unittest.main()

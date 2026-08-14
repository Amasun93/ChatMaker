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

    def test_generator_escapes_user_text(self):
        request = replace(self.request(), title='<script id="attack">bad()</script>')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "safe.html"

            generate_single_file(request, output)
            text = output.read_text(encoding="utf-8")

        self.assertNotIn('<script id="attack">', text)
        self.assertIn("&lt;script", text)


if __name__ == "__main__":
    unittest.main()

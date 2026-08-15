from __future__ import annotations

import importlib
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))


def load_embed_module():
    spec = importlib.util.find_spec("chatmaker.web.embed")
    if spec is None:
        return None
    return importlib.import_module("chatmaker.web.embed")


def embedded_body(header: str) -> str:
    match = re.search(
        r'R"(?P<delimiter>[A-Z0-9_]+)\((?P<body>.*)\)(?P=delimiter)";',
        header,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError("generated header does not contain one C++ raw string")
    return match.group("body")


class HtmlEmbedTests(unittest.TestCase):
    def test_rendered_header_round_trips_utf8_html_and_avoids_delimiter_collision(self):
        embed = load_embed_module()
        self.assertIsNotNone(embed, "chatmaker.web.embed is missing")
        html = '<!doctype html>\n<p>中文 )CHATMAKER_PAGE" still belongs to HTML</p>\n'

        header = embed.render_cpp_header(html, symbol="DEMO_PAGE")

        self.assertEqual(embedded_body(header), html)
        self.assertIn("#include <Arduino.h>", header)
        self.assertIn("const char DEMO_PAGE[] PROGMEM", header)
        self.assertIn(
            "constexpr size_t DEMO_PAGE_LENGTH = sizeof(DEMO_PAGE) - 1;",
            header,
        )
        self.assertEqual(embed.render_cpp_header(html, symbol="DEMO_PAGE"), header)

    def test_embed_file_cli_writes_the_real_input_without_external_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "phone.html"
            output = Path(directory) / "phone_page.h"
            html = "<!doctype html>\n<title>设备页</title>\n"
            source.write_text(html, encoding="utf-8")
            environment = {**os.environ, "PYTHONPATH": str(ROOT / "runtime")}

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "chatmaker.web.embed",
                    str(source),
                    str(output),
                    "--symbol",
                    "PHONE_PAGE",
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            header = output.read_text(encoding="utf-8")

        self.assertEqual(embedded_body(header), html)
        self.assertNotIn("https://", header)

    def test_embed_file_always_writes_lf_bytes(self):
        embed = load_embed_module()
        self.assertIsNotNone(embed, "chatmaker.web.embed is missing")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "phone.html"
            output = Path(directory) / "phone_page.h"
            source.write_bytes(b"<main>hello</main>\r\n")

            embed.embed_html_file(source, output, symbol="PHONE_PAGE")

            generated = output.read_bytes()
        self.assertIn(b"\n", generated)
        self.assertNotIn(b"\r\n", generated)

    def test_render_rejects_a_symbol_that_would_break_the_cpp_header(self):
        embed = load_embed_module()
        self.assertIsNotNone(embed, "chatmaker.web.embed is missing")

        with self.assertRaisesRegex(ValueError, "invalid_cpp_symbol"):
            embed.render_cpp_header("<p>safe</p>", symbol="PAGE; injected")

    def test_render_rejects_nul_that_would_truncate_the_served_page(self):
        embed = load_embed_module()
        self.assertIsNotNone(embed, "chatmaker.web.embed is missing")

        with self.assertRaisesRegex(ValueError, "html_contains_nul"):
            embed.render_cpp_header("<p>before\0after</p>", symbol="SAFE_PAGE")


if __name__ == "__main__":
    unittest.main()

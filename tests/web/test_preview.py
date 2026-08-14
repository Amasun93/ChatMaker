from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.web.preview import serve_preview  # noqa: E402


class PreviewServerTests(unittest.TestCase):
    def test_preview_defaults_to_loopback_and_serves_only_requested_file(self):
        with tempfile.TemporaryDirectory() as directory:
            html_file = Path(directory) / "preview.html"
            html_file.write_text("<!doctype html><title>Preview</title>", encoding="utf-8")

            server, address = serve_preview(html_file)
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)

            self.assertEqual(address.host, "127.0.0.1")
            with urlopen(address.url, timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b"<title>Preview</title>", response.read())
            try:
                with urlopen(f"{address.url}favicon.ico", timeout=3) as favicon:
                    self.assertEqual(favicon.status, 204)
            except HTTPError as exc:
                self.fail(f"favicon request returned {exc.code}")
            with self.assertRaises(HTTPError) as missing:
                urlopen(f"{address.url}pyproject.toml", timeout=3)
            self.assertEqual(missing.exception.code, 404)

    def test_non_loopback_host_requires_explicit_network_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            html_file = Path(directory) / "preview.html"
            html_file.write_text("<!doctype html>", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "allow_network"):
                serve_preview(html_file, host="0.0.0.0")


if __name__ == "__main__":
    unittest.main()

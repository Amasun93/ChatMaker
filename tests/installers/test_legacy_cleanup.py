from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from cleanup_legacy_mcp import cleanup  # noqa: E402


class LegacyCleanupTests(unittest.TestCase):
    def test_removes_only_owned_entries_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "mcp.json"
            original = {
                "mcpServers": {
                    "chatmaker": {"command": "python", "args": ["-m", "chatmaker.integrations.mcp"]},
                    "arduino-nano-mindplus": {"command": "chatmaker-workbuddy-mcp"},
                    "teacher-tool": {"command": "keep-me"},
                },
                "hostSetting": True,
            }
            config.write_text(json.dumps(original), encoding="utf-8")

            result = cleanup(config)

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "cleaned")
            self.assertEqual(set(result["removed"]), {"chatmaker", "arduino-nano-mindplus"})
            saved = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(saved["mcpServers"], {"teacher-tool": {"command": "keep-me"}})
            self.assertEqual(Path(result["backup"]).read_bytes(), json.dumps(original).encode("utf-8"))

    def test_preserves_an_unrelated_server_that_reuses_the_legacy_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "mcp.json"
            original = {"mcpServers": {"arduino-nano-mindplus": {"command": "teacher-owned"}}}
            config.write_text(json.dumps(original), encoding="utf-8")

            result = cleanup(config)

            self.assertEqual(result["status"], "already_clean")
            self.assertEqual(json.loads(config.read_text(encoding="utf-8")), original)


if __name__ == "__main__":
    unittest.main()

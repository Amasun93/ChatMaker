from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.installers import capabilities  # noqa: E402


class CapabilityProbeTests(unittest.TestCase):
    def test_windows_probe_includes_common_non_system_drive_installs(self):
        v1, v2, _ = capabilities._mindplus_roots(Path("C:/Users/teacher"), {}, "windows")
        self.assertIn(Path(r"E:\Mind+"), v1)
        self.assertIn(Path(r"E:\Mind+2"), v2)

    def test_probe_reports_only_local_capabilities(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            environment = {
                "PATH": "",
                "SHELL": "/bin/sh",
                "CODEX_HOME": str(home / "codex"),
                "WORKBUDDY_HOME": str(home / "workbuddy"),
                "WORKBUDDY_CONFIG": str(home / "workbuddy" / "mcp.json"),
            }
            with (
                mock.patch.object(capabilities.platform, "system", return_value="Linux"),
                mock.patch.object(capabilities.platform, "machine", return_value="x86_64"),
                mock.patch.object(capabilities.nano_mindplus, "scan_ports", return_value=[]),
                mock.patch.object(capabilities.nano_mindplus, "discover_installations", return_value=[]),
                mock.patch.object(capabilities.shutil, "which", return_value=None),
            ):
                report = capabilities.probe_environment(home=home, environ=environment).to_dict()

            self.assertTrue(report["success"])
            self.assertEqual(report["os"]["family"], "linux")
            self.assertNotIn("skill_roots", report)
            self.assertNotIn("candidate_skill_roots", report)
            self.assertNotIn("mcp_configs", report)
            self.assertFalse((home / "codex").exists())
            self.assertFalse((home / "workbuddy").exists())

    def test_missing_optional_tools_remain_a_successful_report(self):
        with (
            mock.patch.object(capabilities.nano_mindplus, "scan_ports", return_value=[]),
            mock.patch.object(capabilities.nano_mindplus, "discover_installations", return_value=[]),
            mock.patch.object(capabilities.shutil, "which", return_value=None),
        ):
            report = capabilities.probe_environment(environ={"PATH": ""}).to_dict()

        self.assertTrue(report["success"])
        self.assertFalse(report["serial"]["available"])
        self.assertFalse(report["mindplus"]["available"])
        self.assertFalse(report["arduino_cli"]["available"])


if __name__ == "__main__":
    unittest.main()

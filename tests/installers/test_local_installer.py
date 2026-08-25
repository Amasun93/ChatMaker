from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.installers import capabilities, local  # noqa: E402


class LocalInstallerTests(unittest.TestCase):
    def test_local_check_ignores_host_environment_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            environment = {
                "PATH": "",
                "SHELL": "/bin/sh",
                "CODEX_HOME": str(home / "codex"),
                "WORKBUDDY_HOME": str(home / "workbuddy"),
                "WORKBUDDY_CONFIG": str(home / "workbuddy" / "mcp.json"),
            }
            before = list(home.rglob("*"))
            with (
                mock.patch.object(capabilities.nano_mindplus, "scan_ports", return_value=[]),
                mock.patch.object(capabilities.nano_mindplus, "discover_installations", return_value=[]),
                mock.patch.object(capabilities.shutil, "which", return_value=None),
            ):
                result = local.run(["local"], home=home, environ=environment)

            self.assertTrue(result["success"])
            self.assertFalse(result["host_scan_performed"])
            self.assertNotIn("hosts", result)
            self.assertNotIn("skill_roots", result["environment"])
            self.assertNotIn("mcp_configs", result["environment"])
            self.assertEqual(before, list(home.rglob("*")))

    def test_doctor_is_a_read_only_alias_for_the_local_check(self):
        output = io.StringIO()
        with (
            mock.patch.object(capabilities.nano_mindplus, "scan_ports", return_value=[]),
            mock.patch.object(capabilities.nano_mindplus, "discover_installations", return_value=[]),
            mock.patch.object(capabilities.shutil, "which", return_value=None),
            contextlib.redirect_stdout(output),
        ):
            exit_code = local.main(["doctor"], environ={"PATH": "", "SHELL": "/bin/sh"})

        value = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(value["mode"], "local")
        self.assertFalse(value["host_scan_performed"])

    def test_removed_auto_action_is_rejected_as_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = local.main(["auto"], environ={"PATH": ""})

        value = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(value["success"])
        self.assertEqual(value["status"], "failed")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from chatmaker.cad import generator, openscad_runtime


class OpenScadRuntimeTests(unittest.TestCase):
    def test_chatmaker_cad_cli_routes_status_and_guarded_prepare(self):
        with (
            mock.patch.object(openscad_runtime, "status", return_value={"success": True, "installed": False}) as status,
            mock.patch.object(openscad_runtime, "prepare", return_value={"success": True, "installed": True}) as prepare,
        ):
            self.assertTrue(generator.execute_request({"action": "openscad-status"})["success"])
            self.assertTrue(
                generator.execute_request(
                    {"action": "openscad-prepare", "allow_install": True}
                )["success"]
            )

        status.assert_called_once_with()
        prepare.assert_called_once_with(allow_install=True)

    def test_status_reports_real_executable_and_version(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "openscad.com"
            executable.write_bytes(b"test")

            def runner(command, **_kwargs):
                self.assertEqual(command, [str(executable), "--version"])
                return subprocess.CompletedProcess(command, 0, "", "OpenSCAD version 2021.01\n")

            result = openscad_runtime.status(
                platform_name="win32",
                environ={"OPENSCAD_BINARY": str(executable)},
                which=lambda _name: None,
                runner=runner,
            )

        self.assertTrue(result["success"])
        self.assertTrue(result["installed"])
        self.assertEqual(result["version"], "2021.01")
        self.assertEqual(result["state"], "ready")

    def test_prepare_requires_explicit_install_permission(self):
        result = openscad_runtime.prepare(
            allow_install=False,
            platform_name="win32",
            environ={},
            which=lambda _name: None,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["installed"])
        self.assertTrue(result["confirmation_required"])
        self.assertEqual(result["state"], "awaiting-install-confirmation")

    def test_prepare_uses_only_official_winget_package_after_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "openscad.com"
            calls = []

            def which(name):
                if name == "winget":
                    return r"C:\Windows\winget.exe"
                return None

            def runner(command, **_kwargs):
                calls.append(command)
                if command[0].lower().endswith("winget.exe"):
                    executable.write_bytes(b"installed")
                    return subprocess.CompletedProcess(command, 0, "installed", "")
                return subprocess.CompletedProcess(command, 0, "OpenSCAD version 2021.01", "")

            result = openscad_runtime.prepare(
                allow_install=True,
                platform_name="win32",
                environ={"OPENSCAD_BINARY": str(executable)},
                which=which,
                runner=runner,
            )

        self.assertTrue(result["success"], result)
        self.assertTrue(result["installed"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["package_id"], "OpenSCAD.OpenSCAD")
        install = calls[0]
        self.assertEqual(
            install,
            [
                r"C:\Windows\winget.exe",
                "install",
                "--id",
                "OpenSCAD.OpenSCAD",
                "-e",
                "--source",
                "winget",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ],
        )


if __name__ == "__main__":
    unittest.main()

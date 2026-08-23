from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.installers.capabilities import probe_environment  # noqa: E402
from chatmaker.installers import capabilities  # noqa: E402


class CapabilityProbeTests(unittest.TestCase):
    def test_windows_probe_includes_common_non_system_drive_installs(self):
        v1, v2, _ = capabilities._mindplus_roots(Path("C:/Users/teacher"), {}, "windows")
        self.assertIn(Path(r"E:\Mind+"), v1)
        self.assertIn(Path(r"E:\Mind+2"), v2)

    def test_probe_environment_reports_platform_capabilities_from_a_table(self):
        """Catches regressions that turn an absent optional prerequisite into a failure."""
        cases = (
            {
                "name": "windows_explicit_paths_and_available_tools",
                "system": "Windows",
                "machine": "AMD64",
                "environ": {
                    "CODEX_HOME": "explicit codex",
                    "WORKBUDDY_CONFIG": "explicit workbuddy/mcp.json",
                    "MINDPLUS1_ROOT": "Mind Plus",
                    "COMSPEC": "C:/Windows/System32/cmd.exe",
                },
                "which": {
                    "arduino-cli.exe": "C:/Tools/arduino-cli.exe",
                    "chrome.exe": "C:/Program Files/Chrome/chrome.exe",
                },
                "ports": [{"address": "COM7", "eligible_for_upload": True}],
                "installations": [{"backend": "mindplus-1-builder", "toolchain_present": True}],
                "want": {
                    "os": "windows",
                    "cpu": "x86_64",
                    "terminal": True,
                    "browser": True,
                    "serial": True,
                    "mindplus": True,
                    "arduino_cli": True,
                    "first_skill_root": "explicit codex/skills",
                    "first_mcp_config": "explicit workbuddy/mcp.json",
                },
            },
            {
                "name": "macos_missing_optional_tools_and_devices",
                "system": "Darwin",
                "machine": "arm64",
                "environ": {"SHELL": "/bin/zsh"},
                "which": {},
                "ports": [],
                "installations": [],
                "want": {
                    "os": "macos",
                    "cpu": "arm64",
                    "terminal": True,
                    "browser": False,
                    "serial": False,
                    "mindplus": False,
                    "arduino_cli": False,
                },
            },
        )

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for case in cases:
                with self.subTest(case=case["name"]):
                    home = base / case["name"]
                    home.mkdir()
                    environ = {
                        key: str(home / value) if key.endswith(("HOME", "CONFIG", "ROOT")) else value
                        for key, value in case["environ"].items()
                    }
                    with (
                        mock.patch.object(capabilities.platform, "system", return_value=case["system"]),
                        mock.patch.object(capabilities.platform, "machine", return_value=case["machine"]),
                        mock.patch.object(
                            capabilities.shutil,
                            "which",
                            side_effect=lambda command, path=None: case["which"].get(command),
                        ),
                        mock.patch.object(capabilities.nano_mindplus, "scan_ports", return_value=case["ports"]),
                        mock.patch("serial.tools.list_ports.comports", return_value=case["ports"]),
                        mock.patch.object(
                            capabilities.nano_mindplus,
                            "discover_installations",
                            return_value=case["installations"],
                        ),
                    ):
                        report = probe_environment(home=home, environ=environ).to_dict()

                    want = case["want"]
                    self.assertTrue(report["success"])
                    self.assertEqual(report["os"]["family"], want["os"])
                    self.assertEqual(report["cpu"]["architecture"], want["cpu"])
                    self.assertEqual(report["terminal"]["available"], want["terminal"])
                    self.assertEqual(report["browser"]["available"], want["browser"])
                    self.assertEqual(report["serial"]["available"], want["serial"])
                    self.assertEqual(report["mindplus"]["available"], want["mindplus"])
                    self.assertEqual(report["arduino_cli"]["available"], want["arduino_cli"])
                    if "first_skill_root" in want:
                        self.assertEqual(report["skill_roots"][0]["path"], str(home / want["first_skill_root"]))
                        self.assertEqual(report["mcp_configs"][0]["path"], str(home / want["first_mcp_config"]))

    def test_probe_environment_keeps_unicode_home_and_explicit_paths(self):
        """Catches path normalization that drops valid Unicode or space-containing homes."""
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "李老师 的 Home"
            codex_home = home / "Codex 空间"
            codex_home.joinpath("skills").mkdir(parents=True)

            with (
                mock.patch.object(capabilities.nano_mindplus, "scan_ports", return_value=[]),
                mock.patch.object(capabilities.nano_mindplus, "discover_installations", return_value=[]),
                mock.patch.object(capabilities.shutil, "which", return_value=None),
            ):
                report = probe_environment(
                    home=home,
                    environ={"CODEX_HOME": str(codex_home), "SHELL": "/bin/zsh"},
                ).to_dict()

            codex = next(item for item in report["skill_roots"] if item["host"] == "codex")
            self.assertEqual(codex["path"], str(codex_home / "skills"))
            self.assertTrue(codex["available"])
            self.assertIn("李老师 的 Home", report["home"])

    def test_probe_environment_treats_unreadable_candidates_as_unavailable(self):
        """Catches permission errors escaping from a merely optional host configuration."""
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            blocked = home / ".workbuddy" / ".mcp.json"
            original_is_file = Path.is_file

            def unreadable(path: Path) -> bool:
                if path == blocked:
                    raise PermissionError("simulated unreadable MCP config")
                return original_is_file(path)

            with (
                mock.patch.object(capabilities.nano_mindplus, "scan_ports", return_value=[]),
                mock.patch.object(capabilities.nano_mindplus, "discover_installations", return_value=[]),
                mock.patch.object(capabilities.shutil, "which", return_value=None),
                mock.patch.object(Path, "is_file", unreadable),
            ):
                report = probe_environment(home=home, environ={"SHELL": "/bin/zsh"}).to_dict()

            workbuddy = next(item for item in report["mcp_configs"] if item["host"] == "workbuddy")
            self.assertTrue(report["success"])
            self.assertFalse(workbuddy["available"])
            self.assertEqual(workbuddy["path"], str(blocked))

    def test_probe_prefers_current_workbuddy_dot_mcp_config_and_keeps_legacy_compatible(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            workbuddy_home = home / ".workbuddy"
            workbuddy_home.mkdir()
            current = workbuddy_home / ".mcp.json"
            legacy = workbuddy_home / "mcp.json"
            current.write_text('{"mcpServers": {}}\n', encoding="utf-8")

            current_report = capabilities._mcp_configs(home, {})
            current_value = next(item for item in current_report if item["host"] == "workbuddy")
            self.assertEqual(current_value["path"], str(current))
            self.assertTrue(current_value["available"])

            current.unlink()
            legacy.write_text('{"mcpServers": {}}\n', encoding="utf-8")
            legacy_report = capabilities._mcp_configs(home, {})
            legacy_value = next(item for item in legacy_report if item["host"] == "workbuddy")
            self.assertEqual(legacy_value["path"], str(legacy))
            self.assertTrue(legacy_value["available"])

    def test_macos_probe_enumerates_serial_and_mindplus_app_without_windows_helpers(self):
        """Catches macOS capability detection silently delegating to Windows-only helpers."""
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            app = home / "Mind+2.app"
            cli = app / "Contents" / "Resources" / "app" / "applications" / "deps" / "mind-link" / "tool" / "arduino-cli"
            config = home / "mindplus-arduino-cli.yaml"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\n", encoding="utf-8")
            config.write_text("directories: {}\n", encoding="utf-8")
            usb_port = SimpleNamespace(
                device="/dev/cu.usbserial-1410",
                description="USB Serial",
                hwid="USB VID:PID=2341:0043",
                manufacturer="Arduino",
            )
            bluetooth_port = SimpleNamespace(
                device="/dev/cu.Bluetooth-Incoming-Port",
                description="Bluetooth-Incoming-Port",
                hwid="",
                manufacturer="",
            )

            with (
                mock.patch.object(capabilities.platform, "system", return_value="Darwin"),
                mock.patch("serial.tools.list_ports.comports", return_value=[usb_port, bluetooth_port]),
            ):
                report = probe_environment(
                    home=home,
                    environ={
                        "PATH": "",
                        "MINDPLUS2_ROOT": str(app),
                        "MINDPLUS2_CONFIG": str(config),
                    },
                ).to_dict()

            self.assertTrue(report["success"])
            self.assertTrue(report["serial"]["available"])
            ports = {item["address"]: item for item in report["serial"]["ports"]}
            self.assertIn("/dev/cu.usbserial-1410", ports)
            self.assertFalse(ports["/dev/cu.Bluetooth-Incoming-Port"]["eligible_for_upload"])
            self.assertTrue(report["mindplus"]["available"])
            self.assertEqual(report["mindplus"]["installations"][0]["backend"], "mindplus-2-cli")
            self.assertEqual(report["mindplus"]["installations"][0]["cli"], str(cli))

    def test_macos_probe_reports_missing_devices_and_app_without_failure(self):
        """Catches absent macOS hardware being treated as an installer error."""
        with tempfile.TemporaryDirectory() as temporary:
            with (
                mock.patch.object(capabilities.platform, "system", return_value="Darwin"),
                mock.patch("serial.tools.list_ports.comports", return_value=[]),
            ):
                report = probe_environment(
                    home=Path(temporary),
                    environ={"PATH": ""},
                ).to_dict()

            self.assertTrue(report["success"])
            self.assertFalse(report["serial"]["available"])
            self.assertFalse(report["mindplus"]["available"])

    def test_supplied_path_controls_windows_command_discovery(self):
        """Catches a supplied PATH being ignored in favor of the process-global PATH."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            supplied = root / "supplied bin"
            process_global = root / "process global bin"
            supplied.mkdir()
            process_global.mkdir()
            for directory in (supplied, process_global):
                for executable in ("cmd.exe", "chrome.exe", "arduino-cli.exe"):
                    (directory / executable).write_text("", encoding="utf-8")

            with (
                mock.patch.object(capabilities.platform, "system", return_value="Windows"),
                mock.patch.dict("os.environ", {"PATH": str(process_global)}, clear=False),
                mock.patch.object(capabilities.nano_mindplus, "scan_ports", return_value=[]),
                mock.patch.object(capabilities.nano_mindplus, "discover_installations", return_value=[]),
            ):
                report = probe_environment(
                    home=root,
                    environ={"PATH": str(supplied)},
                ).to_dict()

            self.assertEqual(report["terminal"]["path"], str(supplied / "cmd.exe"))
            self.assertEqual(report["browser"]["path"], str(supplied / "chrome.exe"))
            self.assertEqual(report["arduino_cli"]["path"], str(supplied / "arduino-cli.exe"))


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
import hashlib
import json
import os
from pathlib import Path
from unittest import mock
import zipfile

from chatmaker.hardware import starcore
from chatmaker.hardware import starcore_toolchain as managed


def flash_assets():
    return {
        "esptool": "esptool.exe",
        "boot_app0": "boot_app0.bin",
        "bootloader": "bootloader.bin",
        "font": "font.xbf",
        "missing": [],
        "font_sha256": starcore.mpython_flash.FONT_SHA256,
        "font_hash_verified": True,
    }


class StarcoreTests(unittest.TestCase):
    def test_current_and_historical_targets_stay_separate(self):
        self.assertTrue(starcore.CURRENT_FQBN.startswith("mindplus:esp32:mpython:"))
        self.assertTrue(starcore.FALLBACK_FQBN.startswith("dfrobot:mpython:mpython:"))
        self.assertNotEqual(starcore.CURRENT_FQBN, starcore.FALLBACK_FQBN)

    def test_mindplus_2_compile_command_uses_preferred_target(self):
        context = {
            "backend": "mindplus-2-cli",
            "cli": "arduino-cli.exe",
            "config": "arduino-cli.yaml",
        }
        command = starcore.build_compile_command(context, Path("blink.ino"), Path("build"))
        self.assertIn(starcore.CURRENT_FQBN, command)
        self.assertNotIn(starcore.FALLBACK_FQBN, command)

    def test_mindplus_1_compile_command_is_only_the_fallback(self):
        context = {
            "backend": "mindplus-1-builder",
            "builder": "builder.exe",
            "arduino": r"C:\Mind+\Arduino",
        }
        command = starcore.build_compile_command(context, Path("blink.ino"), Path("build"))
        self.assertIn(f"-fqbn={starcore.FALLBACK_FQBN}", command)
        self.assertNotIn(f"-fqbn={starcore.CURRENT_FQBN}", command)

    def test_managed_compile_command_uses_isolated_config_and_current_target(self):
        context = {
            "backend": managed.BACKEND,
            "cli": r"C:\ChatMaker\arduino-cli.exe",
            "config": r"C:\ChatMaker\arduino-cli.yaml",
        }
        command = starcore.build_compile_command(context, Path("blink.ino"), Path("build"))
        self.assertIn(starcore.CURRENT_FQBN, command)
        self.assertIn(r"C:\ChatMaker\arduino-cli.yaml", command)

    def test_discovery_prefers_usable_mindplus_2_over_mindplus_1(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cli = root / "Mind+2" / "arduino-cli.exe"
            config = root / "arduino-cli.yaml"
            builder = root / "Mind+1" / "Arduino" / "arduino-builder.exe"
            boards = root / "Mind+1" / "Arduino" / "hardware" / "dfrobot" / "mpython" / "boards.txt"
            for path in (cli, config, builder, boards):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder", encoding="utf-8")
            installations = [
                {"backend": "mindplus-1-builder", "root": str(root / "Mind+1"), "builder": str(builder)},
                {"backend": "mindplus-2-cli", "root": str(root / "Mind+2"), "cli": str(cli), "config": str(config)},
            ]
            with (
                mock.patch.object(managed, "managed_context", return_value=None),
                mock.patch.object(starcore.shared, "discover_installations", return_value=installations),
            ):
                context = starcore._current_context()
        self.assertEqual(context["backend"], "mindplus-2-cli")
        self.assertEqual(context["fqbn"], starcore.CURRENT_FQBN)

    def test_upload_requires_confirmed_board_identity(self):
        original = starcore.scan_ports
        starcore.scan_ports = lambda: [{"address": "COM7", "eligible_for_upload": True}]
        try:
            port, error, _ = starcore._select_port({})
        finally:
            starcore.scan_ports = original
        self.assertIsNone(port)
        self.assertEqual(error, "starcore_identity_confirmation_required")

    def test_identity_block_explains_the_beginner_next_step(self):
        with mock.patch.object(
            starcore,
            "scan_ports",
            return_value=[{"address": "COM7", "eligible_for_upload": True}],
        ):
            result = starcore.upload_result(
                {"backend": managed.BACKEND, "fqbn": starcore.CURRENT_FQBN},
                {},
                {},
            )
        self.assertFalse(result["success"])
        self.assertEqual(result["next_action"], "confirm_starcore_identity_then_retry")
        self.assertIn("V4.2.2", result["teacher_message"])

    def test_upload_retries_at_115200_after_permission_error(self):
        calls = []

        def runner(command, timeout):
            calls.append(command)
            if "read_flash" in command and "1500000" in command:
                return {"returncode": 1, "stdout": "", "stderr": "PermissionError: access denied"}
            if "read_flash" in command:
                Path(command[-1]).write_bytes(b"GUIX")
            return {"returncode": 0, "stdout": "Hash of data verified", "stderr": ""}

        context = {
            "backend": managed.BACKEND,
            "cli": "arduino-cli.exe",
            "config": "arduino-cli.yaml",
            "fqbn": starcore.CURRENT_FQBN,
        }
        compiled = {"application_bin": "app.bin", "partitions_bin": "partitions.bin"}
        with (
            mock.patch.object(starcore, "scan_ports", return_value=[{"address": "COM7", "eligible_for_upload": True}]),
            mock.patch.object(starcore.mpython_flash, "resolve_flash_assets", return_value=flash_assets()),
        ):
            result = starcore.upload_result(
                context,
                {"board_confirmed": True},
                compiled,
                runner=runner,
            )

        self.assertTrue(result["success"])
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["upload_baud"], 115200)
        self.assertTrue(result["safe_baud_fallback_used"])
        self.assertTrue(result["font_checked"])
        self.assertFalse(result["font_asset_written"])

    def test_invalid_packet_head_returns_manual_download_mode_guidance(self):
        def runner(command, timeout):
            return {"returncode": 1, "stdout": "", "stderr": "Invalid head of packet (0xE3)"}

        context = {
            "backend": managed.BACKEND,
            "cli": "arduino-cli.exe",
            "config": "arduino-cli.yaml",
            "fqbn": starcore.CURRENT_FQBN,
        }
        compiled = {"application_bin": "app.bin", "partitions_bin": "partitions.bin"}
        with (
            mock.patch.object(starcore, "scan_ports", return_value=[{"address": "COM7", "eligible_for_upload": True}]),
            mock.patch.object(starcore.mpython_flash, "resolve_flash_assets", return_value=flash_assets()),
        ):
            result = starcore.upload_result(
                context,
                {"board_confirmed": True},
                compiled,
                runner=runner,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["diagnostics"]["error_type"], "manual_download_mode_required")
        self.assertIn("A 键", result["diagnostics"]["teacher_message"])
        self.assertIn("RST", result["diagnostics"]["teacher_message"])

    def test_missing_font_marker_writes_verified_font_in_same_flash_command(self):
        calls = []

        def runner(command, timeout):
            calls.append(command)
            if "read_flash" in command:
                Path(command[-1]).write_bytes(b"NONE")
            return {"returncode": 0, "stdout": "Hash of data verified", "stderr": ""}

        with (
            mock.patch.object(starcore, "scan_ports", return_value=[{"address": "COM7", "eligible_for_upload": True}]),
            mock.patch.object(starcore.mpython_flash, "resolve_flash_assets", return_value=flash_assets()),
        ):
            result = starcore.upload_result(
                {"backend": managed.BACKEND, "fqbn": starcore.CURRENT_FQBN},
                {"board_confirmed": True, "manual_download_mode": True},
                {"application_bin": "app.bin", "partitions_bin": "partitions.bin"},
                runner=runner,
            )

        self.assertTrue(result["success"])
        self.assertTrue(result["font_checked"])
        self.assertTrue(result["font_asset_written"])
        upload = next(command for command in calls if "write_flash" in command)
        self.assertIn("0x400000", upload)
        self.assertIn("font.xbf", upload)
        self.assertIn("no_reset", upload)

    def test_missing_toolchain_is_reported(self):
        original = starcore._current_context
        starcore._current_context = lambda: None
        try:
            result = starcore.execute_request({"action": "compile", "code": "x"})
        finally:
            starcore._current_context = original
        self.assertEqual(result["error"], "starcore_toolchain_missing")
        self.assertEqual(result["next_action"], "prepare-environment")

    def test_compile_requires_source(self):
        with tempfile.TemporaryDirectory() as folder:
            context = {"builder": "builder.exe", "arduino": folder}
            result = starcore.compile_result(context, {})
        self.assertEqual(result["error"], "sketch_or_code_required")

    def test_toolchain_lock_pins_official_cli_core_and_chinese_libraries(self):
        lock = managed.toolchain_lock()
        self.assertEqual(lock["arduino_cli"]["version"], "0.33.1")
        self.assertEqual(
            lock["arduino_cli"]["sha256"],
            "58e7474a5873dbd7cad811ed4193223497d90445a6312397a65c08156b6c96d3",
        )
        self.assertEqual(lock["core"]["id"], "mindplus:esp32")
        self.assertEqual(lock["core"]["version"], "0.0.1")
        self.assertEqual(lock["font_device_package"]["source_kind"], "domestic_official")
        self.assertEqual(lock["font_device_package"]["font_sha256"], starcore.mpython_flash.FONT_SHA256)
        self.assertEqual(
            {item["name"] for item in lock["libraries"]},
            {
                "DFRobot_Mindplus_ASCIIfont",
                "DFRobot_Mindplus_CHfont",
                "DFRobot_MPython_Font",
                "DFRobot_Mindplus_NeoPixel",
                "DFRobot_Mindplus_SSD1306",
                "DFRobot_Mindplus_MPython",
            },
        )
        self.assertTrue(all(item["version"] == "1.0.0" for item in lock["libraries"]))
        self.assertTrue(all(len(item["sha256"]) == 64 for item in lock["libraries"]))

    def test_managed_environment_is_preferred_over_mindplus(self):
        context = {
            "backend": managed.BACKEND,
            "cli": "managed-cli.exe",
            "config": "managed.yaml",
        }
        with (
            mock.patch.object(managed, "managed_context", return_value=context),
            mock.patch.object(starcore.shared, "discover_installations") as discover,
        ):
            selected = starcore._current_context()
        discover.assert_not_called()
        self.assertEqual(selected["backend"], managed.BACKEND)
        self.assertEqual(selected["fqbn"], starcore.CURRENT_FQBN)

    def test_prepare_environment_builds_isolated_managed_toolchain(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "managed"

            def downloader(item, destination):
                destination.parent.mkdir(parents=True, exist_ok=True)
                if item["filename"].startswith("arduino-cli_"):
                    with zipfile.ZipFile(destination, "w") as archive:
                        archive.writestr("arduino-cli.exe", b"managed-cli")
                elif item["filename"] == managed.FONT_DEVICE_ARTIFACT["filename"]:
                    with zipfile.ZipFile(destination, "w") as archive:
                        archive.writestr(
                            f"firmware/{managed.FONT_DEVICE_ARTIFACT['font_filename']}",
                            b"font-bytes",
                        )
                else:
                    with zipfile.ZipFile(destination, "w") as archive:
                        archive.writestr(
                            f"{item['archive_root']}/{item['required_file']}",
                            b"// managed",
                        )

            def runner(command, timeout):
                if command[1:3] == ["core", "install"]:
                    board = root / "data" / "packages" / "mindplus" / "hardware" / "esp32" / "0.0.1" / "boards.txt"
                    board.parent.mkdir(parents=True, exist_ok=True)
                    board.write_text("mpython.name=mPython", encoding="utf-8")
                return {"command": command, "returncode": 0, "stdout": "", "stderr": ""}

            def install_font(_archive, destination):
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b"0" * managed.FONT_DEVICE_ARTIFACT["font_size"])

            with (
                mock.patch.object(managed.os, "name", "nt"),
                mock.patch.object(managed.platform, "machine", return_value="AMD64"),
                mock.patch.object(managed, "_install_font_device_archive", side_effect=install_font),
                mock.patch.object(managed, "_sha256", side_effect=lambda path: (
                    managed.FONT_DEVICE_ARTIFACT["font_sha256"]
                    if Path(path).name == managed.FONT_DEVICE_ARTIFACT["font_filename"]
                    else hashlib.sha256(Path(path).read_bytes()).hexdigest()
                )),
            ):
                result = managed.prepare_environment_result(
                    root=root,
                    runner=runner,
                    downloader=downloader,
                )

            self.assertTrue(result["success"])
            self.assertTrue(result["installation_performed"])
            self.assertEqual(result["environment"]["backend"], managed.BACKEND)
            config = json.loads((root / "arduino-cli.yaml").read_text(encoding="ascii"))
            self.assertTrue(
                os.path.samefile(
                    Path(config["directories"]["data"]),
                    root / "data",
                )
            )
            self.assertEqual(
                config["board_manager"]["additional_urls"],
                [managed.MINDPLUS_PACKAGE_INDEX_URL],
            )
            manifest = json.loads((root / "manifest.json").read_text(encoding="ascii"))
            self.assertEqual(manifest["backend"], managed.BACKEND)
            self.assertEqual(
                manifest["arduino_cli_executable_sha256"],
                hashlib.sha256(b"managed-cli").hexdigest(),
            )
            self.assertEqual(manifest["font_sha256"], managed.FONT_DEVICE_ARTIFACT["font_sha256"])
            self.assertTrue((root / "firmware" / managed.FONT_DEVICE_ARTIFACT["font_filename"]).is_file())


if __name__ == "__main__":
    unittest.main()

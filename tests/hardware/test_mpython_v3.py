from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock
import zipfile

import yaml

from chatmaker.hardware import mpython_v3


ROOT = Path(__file__).resolve().parents[2]


class MpythonV3Tests(unittest.TestCase):
    def test_identity_and_official_target_are_not_classic_or_starcore(self):
        self.assertEqual(mpython_v3.BOARD_ID, "mpython-v3")
        self.assertEqual(mpython_v3.CORE_ID, "mpython:esp32")
        self.assertEqual(mpython_v3.CORE_VERSION, "3.0.0")
        self.assertEqual(mpython_v3.FQBN, "mpython:esp32:labplus_mpython_v3")

    def test_toolchain_lock_pins_official_windows_assets(self):
        lock = mpython_v3.toolchain_lock()
        self.assertEqual(lock["arduino_cli"]["size"], 14311609)
        self.assertEqual(lock["core"]["size"], 44968645)
        self.assertEqual(len(lock["arduino_cli"]["sha256"]), 64)
        self.assertEqual(len(lock["core"]["sha256"]), 64)
        self.assertEqual(
            lock["package_index"],
            "https://labplus-cn.github.io/arduino-esp32/package_esp32_mpython_index_cn.json",
        )
        dependencies = {item["name"]: item for item in lock["windows_x64_dependencies"]}
        self.assertEqual(
            set(dependencies),
            {
                "esp32-arduino-libs",
                "xtensa-esp32s3-elf-gcc",
                "esptool_py",
                "mkspiffs",
                "mklittlefs",
            },
        )
        self.assertEqual(dependencies["esp32-arduino-libs"]["size"], 79063774)
        self.assertEqual(dependencies["xtensa-esp32s3-elf-gcc"]["size"], 135381926)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in dependencies.values()))

    def test_prepare_adds_windows_cpp_prefix_compatibility_override(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "managed"

            def downloader(item, destination):
                destination.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(destination, "w") as archive:
                    archive.writestr("arduino-cli.exe", b"managed-cli")

            def runner(command, timeout):
                if command[1:3] == ["core", "install"]:
                    platform = (
                        root
                        / "data"
                        / "packages"
                        / "mpython"
                        / "hardware"
                        / "esp32"
                        / mpython_v3.CORE_VERSION
                    )
                    platform.mkdir(parents=True, exist_ok=True)
                    (platform / "boards.txt").write_text(
                        "labplus_mpython_v3.name=mPython V3\n", encoding="utf-8"
                    )
                return {"command": command, "returncode": 0, "stdout": "", "stderr": ""}

            with (
                mock.patch.object(mpython_v3.os, "name", "nt"),
                mock.patch.object(mpython_v3.platform, "machine", return_value="AMD64"),
            ):
                result = mpython_v3.prepare_environment_result(
                    root=root, runner=runner, downloader=downloader
                )

            override = (
                root
                / "data"
                / "packages"
                / "mpython"
                / "hardware"
                / "esp32"
                / mpython_v3.CORE_VERSION
                / "platform.local.txt"
            )
            self.assertTrue(result["success"], result)
            self.assertTrue(override.is_file())
            self.assertIn("-isystem", override.read_text(encoding="ascii"))
            self.assertIn("xtensa-esp32s3-elf", override.read_text(encoding="ascii"))

    def test_prepare_download_failure_returns_a_safe_offline_next_step(self):
        with tempfile.TemporaryDirectory() as folder:
            with (
                mock.patch.object(mpython_v3.os, "name", "nt"),
                mock.patch.object(mpython_v3.platform, "machine", return_value="AMD64"),
            ):
                result = mpython_v3.prepare_environment_result(
                    root=Path(folder) / "managed",
                    downloader=mock.Mock(
                        side_effect=mpython_v3.downloads.DownloadError(
                            "all_pinned_sources_failed"
                        )
                    ),
                )

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "arduino-cli")
        self.assertEqual(
            result["next_action"],
            "place_verified_archive_in_managed_downloads_or_configure_mirror",
        )
        self.assertIn("CHATMAKER_DOWNLOAD_MIRROR_BASE", result["teacher_message"])
        self.assertTrue(result["required_archive"].endswith(mpython_v3.ARDUINO_CLI["filename"]))

    def test_upload_requires_exact_board_confirmation(self):
        ports = [{"address": "COM7", "eligible_for_upload": True}]
        with mock.patch.object(mpython_v3.shared, "scan_ports", return_value=ports):
            port, error, _ = mpython_v3._select_port({})
        self.assertIsNone(port)
        self.assertEqual(error, "mpython_v3_identity_confirmation_required")

    def test_recipe_keeps_unobserved_hardware_gates_open(self):
        recipe = yaml.safe_load(
            (ROOT / "packs/recipes/mpython-v3-chinese-status.yaml").read_text(
                encoding="utf-8"
            )
        )
        source = (ROOT / recipe["source_file"]).read_text(encoding="utf-8")
        self.assertEqual(recipe["boards"], [mpython_v3.BOARD_ID])
        self.assertIn("掌控板3.0", source)
        self.assertNotIn("fillScreen", source.split("void loop()", 1)[1])
        self.assertEqual(recipe["verification"]["firmware_uploaded"]["status"], "unverified")
        self.assertEqual(recipe["verification"]["physical_effect_verified"]["status"], "unverified")


if __name__ == "__main__":
    unittest.main()

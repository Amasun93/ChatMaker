from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_VERSION = "0.1.0-rc5"


def load_builder():
    path = ROOT / "scripts" / "build_release.py"
    spec = importlib.util.spec_from_file_location("chatmaker_build_release", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleasePackageTests(unittest.TestCase):
    def test_rc5_verification_records_timeout_before_corrected_final_success(self):
        verification = (
            ROOT / "docs" / "verification" / "2026-08-15-rc5-release-candidate.md"
        ).read_text(encoding="utf-8")

        timeout_position = verification.find("900 秒默认预算下超时")
        correction_position = verification.find("编译默认预算修正为 1200 秒")
        success_position = verification.find("1056.41 秒")

        self.assertGreaterEqual(timeout_position, 0)
        self.assertGreaterEqual(correction_position, 0)
        self.assertGreaterEqual(success_position, 0)
        self.assertLess(timeout_position, correction_position)
        self.assertLess(correction_position, success_position)
        self.assertIn("946528 B", verification)
        self.assertIn("47168 B", verification)
        self.assertNotIn("Fix round 1 修正文档后重新生成最终归档", verification)
        self.assertNotIn("chatmaker-rc5-fix1-final-", verification)

    def test_rc5_verification_records_latest_final_extraction_metrics(self):
        verification = (
            ROOT / "docs" / "verification" / "2026-08-15-rc5-release-candidate.md"
        ).read_text(encoding="utf-8")

        final_position = verification.find("最新最终归档的全新解压复验")

        self.assertGreaterEqual(final_position, 0)
        final_evidence = verification[final_position:]
        self.assertIn("220.876 秒", final_evidence)
        self.assertIn("904.292 秒", final_evidence)
        self.assertIn("946528 B", final_evidence)
        self.assertIn("47168 B", final_evidence)

    def test_installation_verifies_archive_before_entering_extracted_directory(self):
        installation = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")
        checksum_position = installation.find("Get-FileHash .\\ChatMaker-0.1.0-rc5.zip")
        extract_position = installation.find("Expand-Archive")
        enter_position = installation.find("Set-Location .\\ChatMaker-0.1.0-rc5")

        self.assertGreaterEqual(checksum_position, 0)
        self.assertGreaterEqual(extract_position, 0)
        self.assertGreaterEqual(enter_position, 0)
        self.assertLess(checksum_position, extract_position)
        self.assertLess(extract_position, enter_position)

    def test_workbuddy_stdio_is_excluded_from_help_claim(self):
        installation = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")

        self.assertNotIn("所有已安装命令均支持 `--help`", installation)
        self.assertNotIn("All installed commands support `--help`", installation)
        self.assertNotRegex(installation, r"chatmaker-workbuddy-mcp\s+--help")
        self.assertIn('"method":"tools/list"', installation)

    def test_release_cli_defaults_to_rc5(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_release.py"),
                    "--root",
                    str(ROOT),
                    "--output",
                    directory,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            result = json.loads(completed.stdout)

        self.assertEqual(result["version"], RELEASE_VERSION)
        self.assertEqual(Path(result["archive"]).name, f"ChatMaker-{RELEASE_VERSION}.zip")

    def test_release_zip_is_deterministic_and_contains_installable_project(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            first = builder.build_release(ROOT, Path(directory) / "first", RELEASE_VERSION)
            second = builder.build_release(ROOT, Path(directory) / "second", RELEASE_VERSION)

            first_zip = Path(first["archive"])
            second_zip = Path(second["archive"])
            first_hash = hashlib.sha256(first_zip.read_bytes()).hexdigest()
            second_hash = hashlib.sha256(second_zip.read_bytes()).hexdigest()
            with zipfile.ZipFile(first_zip) as archive:
                names = set(archive.namelist())

        prefix = f"ChatMaker-{RELEASE_VERSION}/"
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(metadata["project"]["version"], "0.1.0rc5")
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_hash, first["sha256"])
        self.assertIn(prefix + "README.md", names)
        self.assertIn(prefix + "CONTRIBUTING.md", names)
        self.assertIn(prefix + "RELEASE_NOTES.md", names)
        self.assertIn(prefix + "pyproject.toml", names)
        self.assertIn(prefix + "docs/installation.md", names)
        self.assertIn(prefix + "docs/demo/one-minute-demo.md", names)
        self.assertIn(prefix + ".github/pull_request_template.md", names)
        self.assertIn(prefix + "skills/chatmaker/SKILL.md", names)
        self.assertIn(prefix + "runtime/chatmaker/installers/codex.py", names)
        self.assertIn(prefix + "runtime/chatmaker/installers/workbuddy.py", names)
        self.assertIn(prefix + "runtime/chatmaker/installers/skill_bundle.py", names)
        self.assertIn(prefix + "runtime/chatmaker/hardware/esp32_devkit_v1.py", names)
        self.assertIn(prefix + "runtime/chatmaker/route.py", names)
        self.assertIn(prefix + "runtime/chatmaker/web/embed.py", names)
        self.assertIn(prefix + "runtime/chatmaker/web/planner.py", names)
        self.assertIn(prefix + "runtime/chatmaker/web/playground.py", names)
        self.assertIn(prefix + "examples/chatduino/esp32/ap-led-sensor/ap-led-sensor.ino", names)
        self.assertIn(prefix + "examples/chatduino/esp32/ap-led-sensor/page_html.h", names)
        self.assertIn(prefix + "examples/chatweb/esp32-ap-control.html", names)
        self.assertIn(prefix + "examples/chatweb/advanced-playground.html", names)
        self.assertIn(prefix + "tests/browser/chatweb.spec.mjs", names)
        self.assertIn(prefix + "package.json", names)
        self.assertIn(prefix + "package-lock.json", names)
        self.assertIn(prefix + "playwright.config.mjs", names)
        self.assertFalse(any("__pycache__" in name or ".git/" in name for name in names))


if __name__ == "__main__":
    unittest.main()
